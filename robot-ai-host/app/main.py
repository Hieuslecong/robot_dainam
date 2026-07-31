"""FastAPI bootstrap/session host for Pipecat SmallWebRTC voice workers."""

from __future__ import annotations

import argparse
import asyncio

try:
    import uvloop  # type: ignore[import-untyped]
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
except ImportError:
    pass
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any
from urllib.parse import quote

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field

from app.auth import (
    create_access_token,
    get_current_device,
    verify_connection_token,
)
from app.security.rate_limit import RateLimitMiddleware
from app.security.tickets import TicketStore
from app.security.audit import audit_log, set_request_id
from app.config import (
    RuntimeProfile,
    Settings,
    get_settings,
    load_profile,
    load_profiles,
    validate_profile_runtime,
)
from app.logging_utils import get_logger
from app.pipecat_runtime.metrics import LatencyTracker
from app.sessions import SessionManager, SessionState

logger = get_logger(__name__)
ROOT_DIR = Path(__file__).resolve().parent.parent
BROWSER_DIST_DIR = ROOT_DIR / "clients" / "browser" / "dist"
BROWSER_SRC_DIR = ROOT_DIR / "clients" / "browser"
ROBOT_DIST_DIR = ROOT_DIR / "clients" / "desktop_robot_emulator" / "dist"


class DeviceRegisterRequest(BaseModel):
    device_id: str = Field(min_length=1, max_length=128)
    device_type: str = "desktop_emulator"
    firmware_version: str = "0.1.0"
    provisioning_secret: str
    capabilities: dict[str, bool] = Field(default_factory=dict)


class DeviceRegisterResponse(BaseModel):
    device_id: str
    access_token: str
    expires_in: int
    heartbeat_interval_seconds: int = 15


class CreateSessionRequest(BaseModel):
    device_id: str
    profile: str | None = None
    language: str = "vi-VN"
    transport: str = "webrtc"
    metadata: dict[str, Any] = Field(default_factory=dict)


class CreateSessionResponse(BaseModel):
    session_id: str
    status: str
    expires_in: int
    webrtcUrl: str
    webrtc: dict[str, Any]
    turnExpiresAt: float | None = None
    iceTransportPolicy: str = "all"
    # Pipecat client-js reads iceConfig at top level of connect params.
    iceConfig: dict[str, Any] | None = None


class OfferRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    sdp: str
    type: str = "offer"
    pc_id: str | None = None
    restart_pc: bool | None = None
    request_data: Any | None = Field(default=None, alias="requestData")


class IceCandidateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    candidate: str
    sdp_mid: str = Field(alias="sdpMid")
    sdp_mline_index: int = Field(alias="sdpMLineIndex")


class PatchOfferRequest(BaseModel):
    pc_id: str
    candidates: list[IceCandidateRequest]


from app.pipecat_runtime.ice_utils import parse_ice_servers as _parse_ice_servers


class HeartbeatResponse(BaseModel):
    status: str
    timestamp: float


class HealthResponse(BaseModel):
    status: str
    version: str
    active_sessions: int
    max_sessions: int
    default_profile: str
    webrtc_available: bool
    browser_built: bool


def create_app(settings_override: Settings | None = None) -> FastAPI:
    """Create an app instance with deterministic settings overrides for CLI/tests."""

    settings = settings_override or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.settings = settings
        app.state.session_manager = SessionManager(settings)
        app.state.latency_tracker = LatencyTracker(settings.metrics_jsonl_path)
        app.state.ticket_store = TicketStore()

        try:
            default_profile = load_profile(settings.default_profile)
            validate_profile_runtime(
                default_profile,
                settings,
                require_credentials=settings.default_profile != "mock",
            )
        except ValueError as exc:
            logger.error("default_profile_invalid", profile=settings.default_profile, error=str(exc))
            raise RuntimeError(f"Invalid DEFAULT_PROFILE: {exc}") from exc

        try:
            from pipecat.transports.smallwebrtc.request_handler import (
                SmallWebRTCRequestHandler,
            )

            app.state.webrtc_handler = SmallWebRTCRequestHandler()
            app.state.webrtc_import_error = None
        except ImportError as exc:
            app.state.webrtc_handler = None
            app.state.webrtc_import_error = str(exc)
            logger.warning("smallwebrtc_unavailable", error=str(exc))

        cleanup_task = asyncio.create_task(_cleanup_loop(app), name="session-cleanup")
        logger.info(
            "server_started",
            host=settings.host,
            port=settings.port,
            profile=settings.default_profile,
            max_sessions=settings.max_sessions,
        )
        try:
            yield
        finally:
            cleanup_task.cancel()
            try:
                await cleanup_task
            except asyncio.CancelledError:
                pass
            manager: SessionManager = app.state.session_manager
            for session in await manager.list_sessions():
                await manager.close_session(session.session_id)
            if app.state.webrtc_handler:
                await app.state.webrtc_handler.close()
            logger.info("server_stopped")

    app = FastAPI(
        title="Robot AI Host Server",
        version="0.1.0",
        description="Pipecat v1.6.0 SmallWebRTC host for Vietnamese robot voice sessions",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )
    app.add_middleware(RateLimitMiddleware)

    # Audit request ID middleware
    @app.middleware("http")
    async def audit_request_id_middleware(request: Request, call_next):
        rid = request.headers.get("X-Request-ID", "")
        set_request_id(rid)
        response = await call_next(request)
        return response

    register_routes(app)

    # Admin API (settings, knowledge, voices, restart)
    from app.admin import router as admin_router

    app.include_router(admin_router)

    # WebSocket RTVI transport (PR-4: feature-flagged)
    from app.transports.websocket_rtvi import register_websocket_routes

    register_websocket_routes(app)
    # Voice chat client at /client/chat (original Pipecat web client)
    if BROWSER_DIST_DIR.is_dir():
        app.mount("/client/chat", StaticFiles(directory=BROWSER_DIST_DIR, html=True), name="chat")
    if ROBOT_DIST_DIR.is_dir():
        app.mount("/robot", StaticFiles(directory=ROBOT_DIST_DIR, html=True), name="robot")
    return app


async def _cleanup_loop(app: FastAPI) -> None:
    while True:
        try:
            await asyncio.sleep(10)
            manager: SessionManager = app.state.session_manager
            closed = await manager.cleanup_expired()
            if closed:
                logger.info("expired_sessions_cleaned", count=len(closed))
        except asyncio.CancelledError:
            return
        except Exception as exc:
            logger.error("cleanup_error", error=str(exc))


def register_routes(app: FastAPI) -> None:
    @app.get("/health", response_model=HealthResponse)
    async def health(request: Request) -> HealthResponse:
        manager: SessionManager = request.app.state.session_manager
        settings: Settings = request.app.state.settings
        return HealthResponse(
            status="ok",
            version="0.1.0",
            active_sessions=manager.active_count,
            max_sessions=settings.max_sessions,
            default_profile=settings.default_profile,
            webrtc_available=request.app.state.webrtc_handler is not None,
            browser_built=BROWSER_DIST_DIR.is_dir(),
        )

    @app.get("/v1/profiles")
    async def profiles() -> dict[str, Any]:
        return {
            name: {
                "language": profile.language,
                "transport": profile.transport,
                "stt": profile.stt.provider,
                "llm": profile.llm.provider,
                "tts": profile.tts.provider,
                "real_audio": name != "mock",
            }
            for name, profile in load_profiles().items()
        }

    @app.post("/v1/devices/register", response_model=DeviceRegisterResponse)
    async def register_device(
        payload: DeviceRegisterRequest, request: Request
    ) -> DeviceRegisterResponse:
        settings: Settings = request.app.state.settings
        if payload.provisioning_secret != settings.provisioning_secret:
            logger.warning("invalid_provisioning_secret", device_id=payload.device_id)
            raise HTTPException(status_code=403, detail="Invalid provisioning secret")
        token = create_access_token(payload.device_id, settings)
        logger.info("device_registered", device_id=payload.device_id, type=payload.device_type)
        return DeviceRegisterResponse(
            device_id=payload.device_id,
            access_token=token,
            expires_in=settings.jwt_expiry_seconds,
        )

    @app.post("/v1/sessions", response_model=CreateSessionResponse)
    async def create_session(
        payload: CreateSessionRequest,
        request: Request,
        device: dict[str, Any] = Depends(get_current_device),
    ) -> CreateSessionResponse:
        started = time.monotonic()
        if payload.device_id != device["device_id"]:
            raise HTTPException(status_code=403, detail="Device ID mismatch")

        settings: Settings = request.app.state.settings
        profile_name = payload.profile or settings.default_profile
        try:
            profile = load_profile(profile_name)
            validate_profile_runtime(
                profile,
                settings,
                require_credentials=profile_name != "mock",
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        if payload.language != profile.language:
            raise HTTPException(status_code=422, detail="Language/profile mismatch")
        if payload.transport != profile.transport:
            raise HTTPException(status_code=422, detail="Transport/profile mismatch")

        manager: SessionManager = request.app.state.session_manager
        # ── Build ICE servers first (needed by both session + response) ──
        ice_servers: list[dict[str, Any]] = []
        turn_expires_at: float | None = None
        try:
            from app.pipecat_runtime.turn_credentials import get_turn_service

            turn_service = get_turn_service(settings)
            if turn_service.use_cloudflare:
                cf_cred = await turn_service.generate_credentials()
                if cf_cred:
                    ice_servers = turn_service.build_ice_servers(cf_cred)
                    turn_expires_at = time.time() + cf_cred.ttl
                    logger.info(
                        "turn_credential_generated",
                        session_id=None,  # not yet created
                        expires_at=turn_expires_at,
                        urls_count=sum(
                            1 + (len(s.get("urls", [])) if isinstance(s.get("urls"), list) else 0)
                            for s in ice_servers
                        ),
                    )
                else:
                    ice_servers = turn_service.build_ice_servers()
            else:
                ice_servers = turn_service.build_ice_servers()
        except Exception as exc:
            logger.warning("turn_service_error", error=str(exc))
            ice_servers = _parse_ice_servers(settings.webrtc_ice_servers)

        try:
            session = await manager.create_session(
                device_id=payload.device_id,
                profile=profile.name,
                language=profile.language,
                transport=profile.transport,
                ice_servers=ice_servers,
            )
        except ValueError as exc:
            raise HTTPException(status_code=429, detail=str(exc)) from exc

        connection_token = create_access_token(
            payload.device_id,
            settings,
            session_id=session.session_id,
            expiry_seconds=min(600, settings.jwt_expiry_seconds),
        )
        base = str(request.base_url).rstrip("/")
        offer_path = f"/v1/sessions/{session.session_id}/api/offer"
        webrtc_url = f"{base}{offer_path}?access_token={quote(connection_token)}"
        tracker: LatencyTracker = request.app.state.latency_tracker
        await tracker.record(
            LatencyTracker.METRIC_SESSION_CREATION,
            (time.monotonic() - started) * 1000,
            session_id=session.session_id,
            device_id=session.device_id,
            profile=session.profile,
        )
        response = CreateSessionResponse(
            session_id=session.session_id,
            status=session.state.value,
            expires_in=settings.jwt_expiry_seconds,
            webrtcUrl=webrtc_url,
            webrtc={
                "url": webrtc_url,
                "ice_servers": ice_servers,
            },
            turnExpiresAt=turn_expires_at,
            iceTransportPolicy=settings.webrtc_ice_policy,
            iceConfig={"iceServers": ice_servers},
        )
        return response

    @app.get("/v1/sessions/{session_id}")
    async def get_session(
        session_id: str,
        request: Request,
        device: dict[str, Any] = Depends(get_current_device),
    ) -> dict[str, Any]:
        manager: SessionManager = request.app.state.session_manager
        session = await manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        if not manager.validate_ownership(session_id, device["device_id"]):
            raise HTTPException(status_code=403, detail="Session ownership mismatch")
        return session.model_dump()

    @app.post("/v1/sessions/{session_id}/heartbeat", response_model=HeartbeatResponse)
    async def heartbeat(
        session_id: str,
        request: Request,
        device: dict[str, Any] = Depends(get_current_device),
    ) -> HeartbeatResponse:
        manager: SessionManager = request.app.state.session_manager
        if not manager.validate_ownership(session_id, device["device_id"]):
            raise HTTPException(status_code=403, detail="Session ownership mismatch")
        if not await manager.update_heartbeat(session_id):
            raise HTTPException(status_code=404, detail="Session not found or inactive")
        return HeartbeatResponse(status="ok", timestamp=time.time())

    @app.delete("/v1/sessions/{session_id}")
    async def close_session(
        session_id: str,
        request: Request,
        device: dict[str, Any] = Depends(get_current_device),
    ) -> dict[str, str]:
        manager: SessionManager = request.app.state.session_manager
        if not manager.validate_ownership(session_id, device["device_id"]):
            raise HTTPException(status_code=403, detail="Session ownership mismatch")
        if not await manager.close_session(session_id):
            raise HTTPException(status_code=404, detail="Session not found")
        return {"status": "closed", "session_id": session_id}

    async def _authorize_offer(
        session_id: str, request: Request, access_token: str
    ) -> tuple[Any, RuntimeProfile]:
        payload = verify_connection_token(request, access_token, session_id=session_id)
        manager: SessionManager = request.app.state.session_manager
        session = await manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        if not manager.validate_ownership(session_id, payload["device_id"]):
            raise HTTPException(status_code=403, detail="Session ownership mismatch")
        return session, load_profile(session.profile)

    async def _handle_offer(
        session_id: str,
        payload: OfferRequest,
        request: Request,
        access_token: str,
    ) -> dict[str, Any]:
        session, profile = await _authorize_offer(session_id, request, access_token)
        if session.state not in {SessionState.CREATED, SessionState.ACTIVE}:
            raise HTTPException(status_code=409, detail="Session is not connectable")
        handler = request.app.state.webrtc_handler
        if not handler:
            detail = request.app.state.webrtc_import_error or "WebRTC extra unavailable"
            raise HTTPException(status_code=503, detail=detail)

        from pipecat.transports.base_transport import TransportParams
        from pipecat.transports.smallwebrtc.request_handler import SmallWebRTCRequest
        from pipecat.transports.smallwebrtc.transport import SmallWebRTCTransport

        manager: SessionManager = request.app.state.session_manager
        settings: Settings = request.app.state.settings
        tracker: LatencyTracker = request.app.state.latency_tracker
        callback_error: list[Exception] = []
        callback_connection: list[Any] = []
        callback_started = time.monotonic()

        async def connection_callback(connection) -> None:
            callback_connection.append(connection)
            try:
                if manager.has_worker(session_id):
                    raise RuntimeError("A voice worker is already active for this session")
                from app.pipecat_runtime.worker_factory import create_worker_for_session

                transport = SmallWebRTCTransport(
                    webrtc_connection=connection,
                    params=TransportParams(
                        audio_in_enabled=True,
                        audio_out_enabled=True,
                        audio_in_stream_on_start=False,
                    ),
                )
                worker, runner, bundle = await create_worker_for_session(
                    session_id=session_id,
                    device_id=session.device_id,
                    profile=profile,
                    transport=transport,
                    settings=settings,
                    tracker=tracker,
                    auto_intro=True,
                )
                manager.register_worker(session_id, worker, runner, bundle)
                await manager.activate_session(session_id)
                await tracker.record(
                    LatencyTracker.METRIC_WORKER_STARTUP,
                    (time.monotonic() - callback_started) * 1000,
                    session_id=session_id,
                    device_id=session.device_id,
                    profile=profile.name,
                )
                asyncio.create_task(
                    _run_worker_runner(runner, session_id, manager),
                    name=f"runner-{session_id}",
                )
            except Exception as exc:
                callback_error.append(exc)
                await manager.mark_error(session_id, str(exc))
                raise

        small_request = SmallWebRTCRequest(
            sdp=payload.sdp,
            type=payload.type,
            pc_id=payload.pc_id,
            restart_pc=payload.restart_pc,
            request_data=payload.request_data,
        )
        # Pass ICE servers from session to handler so server-side also
        # uses TURN (not just the client). Without this, the server only
        # advertises host candidates and ICE can't complete over NAT.
        if session.ice_servers:
            from pipecat.transports.smallwebrtc.connection import IceServer

            ice_servers_typed: list[IceServer] = []
            for s in session.ice_servers:
                ice_servers_typed.append(IceServer(**s))
            handler.update_ice_servers(ice_servers_typed)
        try:
            answer = await handler.handle_web_request(small_request, connection_callback)
        except Exception as exc:
            await manager.mark_error(session_id, str(exc))
            raise HTTPException(status_code=500, detail=f"WebRTC negotiation failed: {exc}") from exc
        if callback_error:
            # The upstream request handler logs callback failures and still
            # stores the peer connection. Disconnect only after it returns so
            # its public ``closed`` handler can remove the stored connection.
            if callback_connection:
                try:
                    await callback_connection[0].disconnect()
                except Exception as cleanup_exc:
                    logger.warning(
                        "failed_webrtc_connection_cleanup",
                        session_id=session_id,
                        error=str(cleanup_exc),
                    )
            raise HTTPException(
                status_code=500,
                detail=f"Voice worker startup failed: {callback_error[0]}",
            )
        if not answer:
            raise HTTPException(status_code=500, detail="No SDP answer generated")
        return answer

    @app.post("/v1/sessions/{session_id}/api/offer")
    @app.post("/v1/sessions/{session_id}/offer", include_in_schema=False)
    async def webrtc_offer(
        session_id: str,
        payload: OfferRequest,
        request: Request,
        access_token: str = Query(...),
    ) -> dict[str, Any]:
        return await _handle_offer(session_id, payload, request, access_token)

    @app.patch("/v1/sessions/{session_id}/api/offer")
    @app.patch("/v1/sessions/{session_id}/offer", include_in_schema=False)
    async def webrtc_ice_candidate(
        session_id: str,
        payload: PatchOfferRequest,
        request: Request,
        access_token: str = Query(...),
    ) -> dict[str, str]:
        await _authorize_offer(session_id, request, access_token)
        handler = request.app.state.webrtc_handler
        if not handler:
            raise HTTPException(status_code=503, detail="WebRTC not available")
        from pipecat.transports.smallwebrtc.request_handler import (
            IceCandidate,
            SmallWebRTCPatchRequest,
        )

        patch = SmallWebRTCPatchRequest(
            pc_id=payload.pc_id,
            candidates=[
                IceCandidate(
                    candidate=item.candidate,
                    sdp_mid=item.sdp_mid,
                    sdp_mline_index=item.sdp_mline_index,
                )
                for item in payload.candidates
            ],
        )
        await handler.handle_patch_request(patch)
        return {"status": "success"}

    # ── Memory control API (PR-1: disabled by default, consent required) ──
    from app.core.memory import MemoryRefused, MemoryStore

    memory_store = MemoryStore()

    def _check_memory_enabled(request: Request) -> None:
        """Raise 403 if persistent memory is disabled."""
        settings: Settings = request.app.state.settings
        if not settings.persistent_user_memory:
            raise HTTPException(status_code=403, detail="Persistent memory is disabled")

    @app.get("/v1/memory/{user_id}")
    async def memory_view(
        user_id: str, request: Request, device: dict[str, Any] = Depends(get_current_device)
    ) -> dict[str, Any]:
        _check_memory_enabled(request)
        audit_log.log("memory_view", principal=device["device_id"], target=f"user:{user_id}")
        return memory_store.view(user_id)

    @app.post("/v1/memory/{user_id}")
    async def memory_remember(
        user_id: str,
        request: Request,
        device: dict[str, Any] = Depends(get_current_device),
    ) -> dict[str, Any]:
        _check_memory_enabled(request)
        body = await request.json()
        try:
            item = memory_store.remember(
                user_id,
                str(body.get("kind", "")),
                str(body.get("value", "")),
                consent=bool(body.get("consent", False)),
            )
        except MemoryRefused as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        audit_log.log("memory_remember", principal=device["device_id"], target=f"user:{user_id}")
        return {"stored": item}

    @app.delete("/v1/memory/{user_id}/{kind}")
    async def memory_delete_one(
        user_id: str, kind: str, request: Request, device: dict[str, Any] = Depends(get_current_device)
    ) -> dict[str, Any]:
        _check_memory_enabled(request)
        audit_log.log("memory_delete_one", principal=device["device_id"], target=f"user:{user_id}/{kind}")
        return {"deleted": memory_store.delete_one(user_id, kind)}

    @app.delete("/v1/memory/{user_id}")
    async def memory_delete_all(
        user_id: str, request: Request, device: dict[str, Any] = Depends(get_current_device)
    ) -> dict[str, Any]:
        _check_memory_enabled(request)
        audit_log.log("memory_delete_all", principal=device["device_id"], target=f"user:{user_id}")
        memory_store.delete_all(user_id)
        return {"deleted": True}

    @app.post("/v1/memory/{user_id}/disable")
    async def memory_disable(
        user_id: str,
        request: Request,
        device: dict[str, Any] = Depends(get_current_device),
    ) -> dict[str, Any]:
        _check_memory_enabled(request)
        audit_log.log("memory_disable", principal=device["device_id"], target=f"user:{user_id}")
        memory_store.disable(user_id)
        return {"disabled": True}
        return {"disabled": bool(body.get("disabled", True))}

    @app.get("/v1/metrics")
    async def get_metrics(
        request: Request,
        session_id: str | None = None,
        profile: str | None = None,
    ) -> dict[str, Any]:
        tracker: LatencyTracker = request.app.state.latency_tracker
        return await tracker.get_all_summaries(session_id=session_id, profile=profile)

    @app.get("/api/system/devices")
    async def system_devices(request: Request) -> dict[str, Any]:
        """Return device diagnostics: GPU backend, STT engine, LLM info."""
        from app.core.device_manager import detect_device

        settings: Settings = request.app.state.settings
        info = detect_device(
            allow_cpu_fallback=settings.allow_cpu_fallback,
            log_diagnostics=settings.log_device_diagnostics,
        )
        info.llm_endpoint = settings.resolved_llm_base_url or ""
        info.llm_model = settings.resolved_llm_model
        info.llm_runtime = settings.llm_runtime_hint or "unknown"  # type: ignore[assignment]
        return {
            "platform": info.platform,
            "pytorch_device": info.pytorch_device,
            "stt_backend": info.stt_backend,
            "llm_endpoint": info.llm_endpoint,
            "llm_model": info.llm_model,
            "llm_runtime": info.llm_runtime,
            "tts_backend": info.tts_backend,
            "fallbacks": info.fallbacks,
        }

    # ── Connection ticket (PR-1: one-time, single-use, TTL 30s) ──────
    @app.post("/v1/sessions/{session_id}/connection-ticket")
    async def connection_ticket(
        session_id: str,
        request: Request,
        device: dict[str, Any] = Depends(get_current_device),
        transport: str = Query("webrtc", pattern="^(webrtc|websocket)$"),
    ) -> dict[str, Any]:
        """Issue a one-time connection ticket for WebRTC/WebSocket.

        Ticket is opaque, single-use, TTL 30s, bound to device+session+transport.
        Replaces the old pattern of embedding JWT in query strings.
        """
        from app.security.tickets import TicketStore

        settings: Settings = request.app.state.settings
        store: TicketStore = request.app.state.ticket_store
        ticket = store.issue(
            device_id=device["device_id"],
            session_id=session_id,
            transport=transport,
            origin=request.headers.get("origin"),
        )
        audit_log.log(
            "connection_ticket_issued",
            principal=device["device_id"],
            target=f"session:{session_id}",
            source_ip=request.client.host if request.client else "-",
            extra={"transport": transport, "ticket_prefix": ticket.ticket[:8] + "..."},
        )
        return {
            "ticket": ticket.ticket,
            "expires_in": ticket.ttl_seconds,
            "transport": transport,
        }

    # ── Legacy endpoints removed (PR-1) ───────────────────────────────
    # POST /api/settings — REMOVED (no auth, now admin-only via /v1/admin)
    # GET /settings — REMOVED (HTML page leaked masked API key)

    # Dashboard (always served, no build required) ────────────────────
    _dashboard_html: str | None = None

    def _load_dashboard() -> str:
        nonlocal _dashboard_html
        if _dashboard_html is None:
            path = BROWSER_SRC_DIR / "dashboard.html"
            if path.is_file():
                _dashboard_html = path.read_text(encoding="utf-8")
            else:
                _dashboard_html = "<h1>Dashboard not found</h1>"
        return _dashboard_html

    @app.get("/client", response_class=HTMLResponse)
    async def dashboard(request: Request) -> HTMLResponse:
        return HTMLResponse(_load_dashboard())

    if not BROWSER_DIST_DIR.is_dir():
        @app.get("/client/chat", response_class=HTMLResponse)
        async def browser_not_built() -> HTMLResponse:
            return HTMLResponse(
                "<h1>Browser client is not built</h1>"
                "<p>Run <code>npm ci --prefix clients/browser && "
                "npm run build --prefix clients/browser</code>, then restart the server.</p>",
                status_code=503,
            )


async def _run_worker_runner(runner: Any, session_id: str, manager: SessionManager) -> None:
    try:
        await runner.run()
    except asyncio.CancelledError:
        logger.info("runner_cancelled", session_id=session_id)
    except Exception as exc:
        logger.error("runner_error", session_id=session_id, error=str(exc))
        await manager.mark_error(session_id, str(exc))
    finally:
        await manager.close_session(session_id)
        logger.info("runner_finished", session_id=session_id)


app = create_app()


def main() -> None:
    parser = argparse.ArgumentParser(description="Robot AI Host Server")
    parser.add_argument("--host", default=None)
    parser.add_argument("--port", type=int, default=None)
    parser.add_argument("--profile", default=None)
    args = parser.parse_args()

    base = get_settings()
    values = base.model_dump()
    if args.host:
        values["host"] = args.host
    if args.port:
        values["port"] = args.port
    if args.profile:
        values["default_profile"] = args.profile
    runtime_settings = Settings(**values)
    runtime_app = create_app(runtime_settings)
    ssl_kwargs = {}
    cert, key = runtime_settings.ssl_certfile, runtime_settings.ssl_keyfile
    if cert and key and Path(cert).exists() and Path(key).exists():
        ssl_kwargs = {"ssl_certfile": cert, "ssl_keyfile": key}
    elif cert or key:
        logger.warning("ssl_files_missing_falling_back_to_http", certfile=cert, keyfile=key)
    uvicorn.run(
        runtime_app, host=runtime_settings.host, port=runtime_settings.port, **ssl_kwargs
    )


if __name__ == "__main__":
    main()
