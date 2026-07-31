"""WebSocket RTVI transport (PR-4).

Uses official Pipecat FastAPIWebsocketTransport with the same:
  - Pipeline factory (create_pipeline)
  - Session runtime (SessionManager)
  - Security model (one-time connection ticket)

Feature-flagged behind WEBSOCKET_RTVI_ENABLED (default false).
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

from fastapi import FastAPI, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

from pipecat.transports.websocket.fastapi import (
    FastAPIWebsocketParams,
    FastAPIWebsocketTransport,
)

from app.config import RuntimeProfile, Settings
from app.logging_utils import get_logger
from app.pipecat_runtime.pipeline_factory import create_pipeline
from app.pipecat_runtime.worker_factory import create_worker_for_session
from app.pipecat_runtime.metrics import LatencyTracker
from app.security.tickets import TicketStore
from app.security.audit import audit_log
from app.sessions import SessionManager

logger = get_logger(__name__)

# Slow-reader deadline: if client can't keep up, mark unhealthy and close
SLOW_READER_DEADLINE_SECONDS = 10.0


def register_websocket_routes(app: FastAPI) -> None:
    """Register WebSocket RTVI route if feature flag is enabled.

    Safe to call during app creation — settings may not be available yet.
    Route registration only activates when the lifespan sets app.state.settings.
    """

    # Deferred: settings are set during lifespan, not during create_app()
    def _get_settings() -> Settings | None:
        try:
            return app.state.settings
        except (AttributeError, KeyError):
            return None

    settings = _get_settings()
    if settings is None or not settings.websocket_rtvi_enabled:
        if settings is None:
            logger.info("websocket_rtvi_deferred", reason="settings not yet available")
        else:
            logger.info("websocket_rtvi_disabled")
        return

    @app.websocket("/v1/ws/{session_id}")
    async def websocket_rtvi_endpoint(
        websocket: WebSocket,
        session_id: str,
        ticket: str = Query(...),
    ):
        """WebSocket RTVI endpoint with one-time ticket auth.

        Flow:
        1. Client POSTs /v1/sessions/{id}/connection-ticket (device token)
        2. Client connects WebSocket with ticket query param
        3. Server validates ticket (single-use, bound to session+transport)
        4. Server creates pipeline and worker
        5. Server runs worker through WS transport

        Ticket is single-use and consumed immediately on validation.
        """
        store: TicketStore = app.state.ticket_store
        manager: SessionManager = app.state.session_manager
        tracker: LatencyTracker = app.state.latency_tracker

        # Validate and consume the ticket (single-use)
        ws_ticket = store.validate_and_consume(
            ticket,
            session_id=session_id,
            transport="websocket",
            origin=websocket.headers.get("origin"),
        )
        if ws_ticket is None:
            await websocket.close(code=4001, reason="Invalid or expired ticket")
            audit_log.log(
                "ws_ticket_rejected",
                principal="anonymous",
                target=f"session:{session_id}",
                source_ip=websocket.client.host if websocket.client else "-",
                result="failure",
            )
            return

        audit_log.log(
            "ws_connected",
            principal=ws_ticket.device_id,
            target=f"session:{session_id}",
            source_ip=websocket.client.host if websocket.client else "-",
        )

        # Accept the WebSocket
        await websocket.accept()
        session = await manager.get_session(session_id)
        if session is None:
            await websocket.close(code=4004, reason="Session not found")
            return

        profile_name = session.profile
        from app.config import load_profile

        profile = load_profile(profile_name)

        # Create transport from the accepted websocket
        from pipecat.serializers.protobuf import ProtobufFrameSerializer

        ws_params = FastAPIWebsocketParams(
            serializer=ProtobufFrameSerializer(),
            session_timeout=300,
            ws_close_timeout=5,
        )
        transport = FastAPIWebsocketTransport(websocket=websocket, params=ws_params)

        try:
            # Create pipeline using same factory
            bundle = await create_pipeline(profile, transport, settings=settings)

            # Create worker
            worker, runner, bundle = await create_worker_for_session(
                session_id=session_id,
                device_id=ws_ticket.device_id,
                profile=profile,
                transport=transport,
                settings=settings,
                tracker=tracker,
                auto_intro=False,
            )

            # Register worker
            manager.register_worker(session_id, worker, runner, bundle)

            # Run with slow-reader deadline
            try:
                await asyncio.wait_for(runner.run(), timeout=SLOW_READER_DEADLINE_SECONDS * 10)
            except asyncio.TimeoutError:
                logger.warning("ws_slow_reader", session_id=session_id)
            except WebSocketDisconnect:
                logger.info("ws_client_disconnected", session_id=session_id)

        except Exception as exc:
            logger.error("ws_session_error", session_id=session_id, error=str(exc))
            audit_log.log(
                "ws_error",
                principal=ws_ticket.device_id,
                target=f"session:{session_id}",
                result="failure",
            )
        finally:
            # Idempotent cleanup
            await manager.close_session(session_id)

            if websocket.client_state != WebSocketState.DISCONNECTED:
                try:
                    await websocket.close()
                except Exception:
                    pass

            audit_log.log(
                "ws_disconnected",
                principal=ws_ticket.device_id,
                target=f"session:{session_id}",
            )

    logger.info("websocket_rtvi_registered", path="/v1/ws/{session_id}")
