"""Create one PipelineWorker and RTVI message scope per device session."""

from __future__ import annotations

import time
from typing import Any

from pipecat.frames.frames import TTSSpeakFrame
from pipecat.observers.user_bot_latency_observer import UserBotLatencyObserver
from pipecat.pipeline.worker import PipelineParams, PipelineWorker
from pipecat.transports.base_transport import BaseTransport
from pipecat.workers.runner import WorkerRunner

from app.config import RuntimeProfile, Settings
from app.logging_utils import get_logger
from app.pipecat_runtime.metrics import LatencyTracker
from app.pipecat_runtime.observers import RuntimeMetricsObserver
from app.pipecat_runtime.pipeline_factory import PipelineBundle, create_pipeline
from app.pipecat_runtime.rtvi import client_message_parts, send_robot_behavior
from app.robot.messages import BehaviorAck, BehaviorCommand

logger = get_logger(__name__)


async def create_worker_for_session(
    session_id: str,
    device_id: str,
    profile: RuntimeProfile,
    transport: BaseTransport,
    *,
    settings: Settings,
    tracker: LatencyTracker,
    auto_intro: bool = False,
) -> tuple[PipelineWorker, WorkerRunner, PipelineBundle]:
    """Create an isolated worker, runner, providers and context for one session."""

    bundle = await create_pipeline(profile, transport, settings=settings)
    runtime_observer = RuntimeMetricsObserver(
        tracker=tracker,
        session_id=session_id,
        device_id=device_id,
        profile=profile.name,
    )
    latency_observer = UserBotLatencyObserver()

    worker = PipelineWorker(
        bundle.pipeline,
        params=PipelineParams(enable_metrics=True, enable_usage_metrics=True),
        enable_rtvi=True,
        observers=[runtime_observer, latency_observer],
        name=f"worker-{session_id}",
    )

    @latency_observer.event_handler("on_latency_measured")
    async def on_latency_measured(observer: Any, latency_seconds: float) -> None:
        await tracker.record(
            LatencyTracker.METRIC_SERVER_USER_TO_BOT,
            latency_seconds * 1000,
            session_id=session_id,
            device_id=device_id,
            profile=profile.name,
            source="pipecat_user_bot_latency_observer",
        )

    behavior_sent_at: dict[str, float] = {}

    @worker.rtvi.event_handler("on_client_ready")
    async def on_rtvi_client_ready(rtvi) -> None:
        behavior = BehaviorCommand(
            name="greet", emotion="friendly", intensity=0.5, duration_ms=700
        )
        sent = await send_robot_behavior(rtvi, behavior, session_id=session_id)
        if sent:
            behavior_sent_at[behavior.behavior_id] = time.monotonic()

    @worker.rtvi.event_handler("on_client_message")
    async def on_client_message(rtvi, message) -> None:
        message_type, data = client_message_parts(message)
        if message_type == "robot.behavior.ack":
            try:
                ack = BehaviorAck.model_validate(data)
            except Exception as exc:
                await rtvi.send_error_response(message, f"Invalid behavior ACK: {exc}")
                return
            started = behavior_sent_at.pop(ack.behavior_id, None)
            if started is not None:
                await tracker.record(
                    LatencyTracker.METRIC_BEHAVIOR_ACK,
                    (time.monotonic() - started) * 1000,
                    session_id=session_id,
                    device_id=device_id,
                    profile=profile.name,
                    source="client_ack",
                )
            logger.info("robot_behavior_ack", session_id=session_id, data=data)
        elif message_type == "client.playback.started":
            runtime_observer.mark_client_event("client_audible_start")
            elapsed = data.get("elapsed_ms")
            if isinstance(elapsed, (int, float)):
                await tracker.record(
                    LatencyTracker.METRIC_CLIENT_AUDIBLE_START,
                    float(elapsed),
                    session_id=session_id,
                    device_id=device_id,
                    profile=profile.name,
                    source="browser",
                )
        elif message_type == "client.audio.received":
            runtime_observer.mark_client_event("client_audio_received")
        elif message_type == "client.playback.stopped":
            runtime_observer.mark_client_event("client_audio_stopped")
        elif message_type == "client.barge_in.stopped":
            runtime_observer.mark_client_event("client_audio_stopped")
            elapsed = data.get("elapsed_ms")
            if isinstance(elapsed, (int, float)):
                await tracker.record(
                    LatencyTracker.METRIC_BARGE_IN_STOP,
                    float(elapsed),
                    session_id=session_id,
                    device_id=device_id,
                    profile=profile.name,
                    source="browser",
                )
        elif message_type == "client.webrtc.connected":
            elapsed = data.get("elapsed_ms")
            if isinstance(elapsed, (int, float)):
                await tracker.record(
                    LatencyTracker.METRIC_WEBRTC_CONNECT,
                    float(elapsed),
                    session_id=session_id,
                    device_id=device_id,
                    profile=profile.name,
                    source="browser",
                )
        elif message_type == "client.capture.settings":
            # AEC/NS/AGC evidence from the live browser track (spec 8.5).
            logger.info("client_capture_settings", session_id=session_id, data=data)
        elif message_type == "conversation.reset":
            bundle.reset_conversation()
            logger.info("conversation_reset", session_id=session_id)
        elif message_type == "robot.wake":
            # Spec 8.7: explicit activation (button/screen touch).
            if bundle.wake_gate is not None:
                bundle.wake_gate.wake()
        elif message_type == "robot.sleep":
            if bundle.wake_gate is not None:
                bundle.wake_gate.sleep()
        elif message_type in {"robot.capabilities", "robot.mute", "robot.unmute"}:
            logger.info("robot_client_message", session_id=session_id, type=message_type, data=data)
        elif message_type == "robot.error":
            logger.warning("robot_error", session_id=session_id, data=data)
        else:
            await rtvi.send_error_response(message, f"Unknown client message type: {message_type}")

    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport: Any, client: Any) -> None:
        logger.info("client_connected", session_id=session_id, device_id=device_id)
        if auto_intro:
            name = settings.persona_name or "Mây Mây"
            intro = f"Mình là {name}, mình có thể giúp gì cho bạn nè?"
            bundle.context.add_message({"role": "assistant", "content": intro})
            # VieNeu warm‑up runs in a background task — wait for it.
            # Non‑VieNeu profiles (Piper, mock) have no engine → skip.
            import asyncio as _asyncio
            engine = getattr(bundle, "vieneu_engine", None)
            if engine is not None:
                for _ in range(16):
                    if engine.ready:
                        break
                    await _asyncio.sleep(0.5)
            await worker.queue_frames([TTSSpeakFrame(intro)])

    runner = WorkerRunner(handle_sigint=False)

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport: Any, client: Any) -> None:
        logger.info("client_disconnected", session_id=session_id, device_id=device_id)
        await runner.cancel(reason="client_disconnected")

    await runner.add_workers(worker)
    logger.info("worker_created", session_id=session_id, profile=profile.name)
    return worker, runner, bundle
