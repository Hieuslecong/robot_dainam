"""Session management: in-memory session registry and lifecycle."""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
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


@dataclass
class SessionRuntimeRecord:
    """Typed runtime record for a single session (PR-2.1).

    Replaces the untyped dict[str, Any] _workers dict.
    """

    worker: Any = None  # PipelineWorker | None
    runner: Any = None  # WorkerRunner | None
    task: asyncio.Task | None = None
    bundle: Any = None  # PipelineBundle | None
    connection: Any = None
    webrtc_handler: Any = None
    pc_id: str | None = None
    claimed: bool = False
    closing: bool = False
    created_at: float = field(default_factory=time.monotonic)


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
    ice_servers: list[dict[str, Any]] = Field(default_factory=list)


class SessionManager:
    """In-memory session registry.

    Thread-safe via asyncio.Lock. Manages session lifecycle, heartbeats,
    ownership validation, cleanup of expired sessions.

    PR-2 changes:
    - Typed SessionRuntimeRecord replaces dict[str, Any]
    - Atomic worker claim (claim_worker_slot / complete_worker_registration)
    - Retention policy (CLOSED_RETENTION / ERROR_RETENTION / MAX_RETAINED)
    - Idempotent cleanup
    """

    # PR-2.6: retention policy
    CLOSED_RETENTION_SECONDS: float = 300.0   # 5 min
    ERROR_RETENTION_SECONDS: float = 600.0    # 10 min
    MAX_RETAINED_SESSION_RECORDS: int = 100

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._sessions: dict[str, SessionInfo] = {}
        self._lock = asyncio.Lock()
        # PR-2.1: typed runtime records
        self._runtimes: dict[str, SessionRuntimeRecord] = {}

    async def create_session(
        self,
        device_id: str,
        profile: str,
        language: str = "vi-VN",
        transport: str = "webrtc",
        ice_servers: list[dict[str, Any]] | None = None,
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
                ice_servers=ice_servers or [],
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

        # PR-2.5: idempotent cleanup using SessionRuntimeRecord
        record = self._runtimes.get(session_id)
        if record and not record.closing:
            record.closing = True
            try:
                runner = record.runner
                worker = record.worker
                bundle = record.bundle
                if runner and hasattr(runner, "cancel"):
                    await runner.cancel(reason="session_closed")
                elif worker and hasattr(worker, "cancel"):
                    await worker.cancel()
                if bundle and hasattr(bundle, "aclose"):
                    await bundle.aclose()
                logger.info("worker_cancelled", session_id=session_id)
            except Exception as exc:
                logger.error("worker_cancel_error", session_id=session_id, error=str(exc))
            finally:
                # Release resources
                if record.bundle and hasattr(record.bundle, "aclose"):
                    try:
                        await record.bundle.aclose()
                    except Exception as cleanup_exc:
                        logger.error("pipeline_resource_cleanup_error", session_id=session_id, error=str(cleanup_exc))
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
        """Clean sessions whose heartbeat timed out, and prune retained closed records.

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

        # PR-2.6: prune retained closed/error sessions
        await self._prune_retained()

        return closed

    async def _prune_retained(self) -> None:
        """PR-2.6: Remove old closed/error sessions and their runtime records."""
        now = time.time()
        async with self._lock:
            to_remove: list[str] = []
            for sid, sess in self._sessions.items():
                if sess.state == SessionState.CLOSED:
                    if now - sess.created_at > self.CLOSED_RETENTION_SECONDS:
                        to_remove.append(sid)
                elif sess.state == SessionState.ERROR:
                    if now - sess.created_at > self.ERROR_RETENTION_SECONDS:
                        to_remove.append(sid)

            # Enforce max retained records
            closed_records = [
                sid for sid, sess in self._sessions.items()
                if sess.state in (SessionState.CLOSED, SessionState.ERROR)
            ]
            if len(closed_records) > self.MAX_RETAINED_SESSION_RECORDS:
                # Remove oldest first
                closed_records.sort(key=lambda sid: self._sessions[sid].created_at)
                overflow = closed_records[:len(closed_records) - self.MAX_RETAINED_SESSION_RECORDS]
                to_remove.extend(overflow)

            for sid in set(to_remove):
                self._sessions.pop(sid, None)
                self._runtimes.pop(sid, None)
                logger.info("session_pruned", session_id=sid)

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
        """Register a PipelineWorker for a session (PR-2.2: atomic via claim_worker_slot).

        A second worker for the same session would create duplicate audio/context
        pipelines and leak resources, so this is rejected explicitly.
        """
        if session_id in self._runtimes and self._runtimes[session_id].claimed:
            raise ValueError(f"Worker already registered for session {session_id}")
        record = self._runtimes.setdefault(session_id, SessionRuntimeRecord())
        record.worker = worker
        record.runner = runner
        record.bundle = bundle
        record.claimed = True

    async def claim_worker_slot(self, session_id: str) -> SessionRuntimeRecord:
        """PR-2.2: Atomically claim a worker slot (must hold lock)."""
        if session_id in self._runtimes and self._runtimes[session_id].claimed:
            raise ValueError(f"Worker slot already claimed for session {session_id}")
        record = self._runtimes.setdefault(session_id, SessionRuntimeRecord())
        record.claimed = True
        record.created_at = time.monotonic()
        return record

    async def complete_worker_registration(
        self,
        session_id: str,
        record: SessionRuntimeRecord,
    ) -> None:
        """PR-2.2: Complete registration after worker is created."""
        if not record.claimed:
            raise ValueError(f"Worker slot not claimed for session {session_id}")
        # record is already in _runtimes; nothing extra needed

    def has_worker(self, session_id: str) -> bool:
        """Return whether a voice worker is registered for the session."""
        record = self._runtimes.get(session_id)
        return record is not None and record.claimed

    @property
    def active_count(self) -> int:
        """Count of active/created sessions."""
        return sum(
            1
            for s in self._sessions.values()
            if s.state in (SessionState.CREATED, SessionState.ACTIVE)
        )
