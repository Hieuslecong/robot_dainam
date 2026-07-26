"""Session management: in-memory session registry with lifecycle."""

from __future__ import annotations

import asyncio
import time
import uuid
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from app.config import Settings
from app.logging_utils import get_logger

logger = get_logger(__name__)


class SessionState(str, Enum):
    """Session lifecycle states."""

    CREATED = "created"
    ACTIVE = "active"
    CLOSING = "closing"
    CLOSED = "closed"
    ERROR = "error"


class SessionInfo(BaseModel):
    """Information about an active session."""

    session_id: str
    device_id: str
    profile: str
    state: SessionState = SessionState.CREATED
    created_at: float = Field(default_factory=time.time)
    last_heartbeat: float = Field(default_factory=time.time)
    transport: str = "webrtc"
    language: str = "vi-VN"
    cleanup_status: str = "none"
    metrics_summary: dict[str, Any] | None = None


class SessionManager:
    """In-memory session registry.

    Thread-safe via asyncio.Lock. Manages session lifecycle, heartbeats,
    ownership validation, and cleanup of expired sessions.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._sessions: dict[str, SessionInfo] = {}
        self._lock = asyncio.Lock()
        # Store workers/runners by session_id for cleanup
        self._workers: dict[str, Any] = {}

    async def create_session(
        self,
        device_id: str,
        profile: str,
        language: str = "vi-VN",
        transport: str = "webrtc",
    ) -> SessionInfo:
        """Create a new session.

        Args:
            device_id: The device requesting the session.
            profile: Provider profile name.
            language: Language code.
            transport: Transport type.

        Returns:
            Created SessionInfo.

        Raises:
            ValueError: If max sessions limit is reached.
        """
        async with self._lock:
            active_count = sum(
                1
                for s in self._sessions.values()
                if s.state in (SessionState.CREATED, SessionState.ACTIVE)
            )
            if active_count >= self._settings.max_sessions:
                logger.warning(
                    "max_sessions_reached",
                    active=active_count,
                    max=self._settings.max_sessions,
                )
                raise ValueError(
                    f"Max sessions ({self._settings.max_sessions}) reached"
                )

            if profile == "hybrid_local_vi":
                hybrid_count = sum(
                    1
                    for item in self._sessions.values()
                    if item.profile == "hybrid_local_vi"
                    and item.state in (SessionState.CREATED, SessionState.ACTIVE)
                )
                if hybrid_count >= self._settings.local_stt_max_sessions:
                    raise ValueError(
                        "Local Whisper session limit reached "
                        f"({self._settings.local_stt_max_sessions}); increase "
                        "LOCAL_STT_MAX_SESSIONS only after memory/latency benchmarking"
                    )

            session_id = f"sess_{uuid.uuid4().hex[:16]}"
            session = SessionInfo(
                session_id=session_id,
                device_id=device_id,
                profile=profile,
                language=language,
                transport=transport,
            )
            self._sessions[session_id] = session
            logger.info(
                "session_created",
                session_id=session_id,
                device_id=device_id,
                profile=profile,
            )
            return session

    async def get_session(self, session_id: str) -> SessionInfo | None:
        """Get session by ID."""
        return self._sessions.get(session_id)

    async def update_heartbeat(self, session_id: str) -> bool:
        """Update session heartbeat timestamp.

        Returns:
            True if session exists and was updated.
        """
        async with self._lock:
            session = self._sessions.get(session_id)
            if session and session.state in (
                SessionState.CREATED,
                SessionState.ACTIVE,
            ):
                session.last_heartbeat = time.time()
                return True
            return False

    async def activate_session(self, session_id: str) -> bool:
        """Mark session as active (after WebRTC connected)."""
        async with self._lock:
            session = self._sessions.get(session_id)
            if session and session.state == SessionState.CREATED:
                session.state = SessionState.ACTIVE
                return True
            return False


    async def mark_error(self, session_id: str, message: str) -> bool:
        """Mark a session as failed while preserving evidence for inspection."""
        async with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return False
            session.state = SessionState.ERROR
            session.cleanup_status = f"error: {message[:200]}"
            return True

    async def close_session(self, session_id: str) -> bool:
        """Close a session (idempotent).

        Returns:
            True if session was found and closed/already closed.
        """
        async with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return False
            if session.state in (SessionState.CLOSED, SessionState.CLOSING):
                return True
            session.state = SessionState.CLOSING
            session.cleanup_status = "pending"

        # Cleanup worker outside of lock
        worker_info = self._workers.pop(session_id, None)
        if worker_info:
            try:
                runner = worker_info.get("runner")
                worker = worker_info.get("worker")
                if runner and hasattr(runner, "cancel"):
                    await runner.cancel(reason="session_closed")
                elif worker and hasattr(worker, "cancel"):
                    await worker.cancel()
                bundle = worker_info.get("bundle")
                if bundle and hasattr(bundle, "aclose"):
                    await bundle.aclose()
                logger.info("worker_cancelled", session_id=session_id)
            except Exception as exc:
                logger.error("worker_cancel_error", session_id=session_id, error=str(exc))
                bundle = worker_info.get("bundle")
                if bundle and hasattr(bundle, "aclose"):
                    try:
                        await bundle.aclose()
                    except Exception as cleanup_exc:
                        logger.error(
                            "pipeline_resource_cleanup_error",
                            session_id=session_id,
                            error=str(cleanup_exc),
                        )

        async with self._lock:
            session = self._sessions.get(session_id)
            if session:
                session.state = SessionState.CLOSED
                session.cleanup_status = "completed"
            logger.info("session_closed", session_id=session_id)
            return True

    async def list_sessions(self) -> list[SessionInfo]:
        """List all sessions."""
        return list(self._sessions.values())

    async def cleanup_expired(self) -> list[str]:
        """Clean up sessions whose heartbeat has timed out.

        Returns:
            List of closed session IDs.
        """
        now = time.time()
        timeout = self._settings.heartbeat_timeout_seconds
        expired_ids: list[str] = []

        async with self._lock:
            for sid, session in self._sessions.items():
                if session.state in (SessionState.CREATED, SessionState.ACTIVE):
                    if now - session.last_heartbeat > timeout:
                        expired_ids.append(sid)

        closed: list[str] = []
        for sid in expired_ids:
            logger.warning("session_heartbeat_expired", session_id=sid)
            await self.close_session(sid)
            closed.append(sid)
        return closed

    def validate_ownership(self, session_id: str, device_id: str) -> bool:
        """Check if device_id owns the session."""
        session = self._sessions.get(session_id)
        if not session:
            return False
        return session.device_id == device_id

    def register_worker(
        self,
        session_id: str,
        worker: Any,
        runner: Any = None,
        bundle: Any = None,
    ) -> None:
        """Register one PipelineWorker for a session.

        A second worker for the same session would create duplicate audio/context
        pipelines and leak resources, so it is rejected explicitly.
        """
        if session_id in self._workers:
            raise ValueError(f"Worker already registered for session {session_id}")
        self._workers[session_id] = {
            "worker": worker,
            "runner": runner,
            "bundle": bundle,
        }

    def has_worker(self, session_id: str) -> bool:
        """Return whether a voice worker is already registered for a session."""
        return session_id in self._workers

    @property
    def active_count(self) -> int:
        """Count of active/created sessions."""
        return sum(
            1
            for s in self._sessions.values()
            if s.state in (SessionState.CREATED, SessionState.ACTIVE)
        )
