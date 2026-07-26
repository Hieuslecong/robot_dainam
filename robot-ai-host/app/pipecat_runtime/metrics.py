"""Runtime latency collection, JSONL evidence and percentile summaries."""

from __future__ import annotations

import asyncio
import json
import math
import time
from pathlib import Path
from typing import Any

from app.logging_utils import get_logger

logger = get_logger(__name__)


def _percentile(data: list[float], p: float) -> float:
    if not data:
        return 0.0
    k = (len(data) - 1) * p / 100.0
    low = math.floor(k)
    high = math.ceil(k)
    if low == high:
        return data[low]
    return data[low] * (high - k) + data[high] * (k - low)


class LatencyTracker:
    """Session-aware latency tracker with append-only JSONL evidence."""

    METRIC_STT_FINAL = "turn_end_to_stt_final"
    METRIC_STT_TTFB = "stt_ttfb"
    METRIC_LLM_FIRST_TOKEN = "llm_first_token"
    METRIC_FIRST_SENTENCE = "first_sentence"
    METRIC_TTS_TTFB = "tts_ttfb"
    METRIC_TTS_FIRST_AUDIO = "tts_first_audio"
    METRIC_SERVER_USER_TO_BOT = "server_user_to_bot"
    METRIC_CLIENT_AUDIBLE_START = "client_audible_start"
    METRIC_BARGE_IN_STOP = "barge_in_audible_stop"
    METRIC_WEBRTC_CONNECT = "webrtc_connect"
    METRIC_WORKER_STARTUP = "worker_startup"
    METRIC_RECONNECT = "reconnect"
    METRIC_BEHAVIOR_ACK = "behavior_ack"
    METRIC_SESSION_CREATION = "session_creation"

    # Spec 17 unified turn timeline. One record per completed turn, metadata
    # carries every observed event as an offset (ms) from vad_speech_start.
    METRIC_TURN_TIMELINE = "turn_timeline"
    # Critical-path segments derived from the timeline (spec 17.3).
    METRIC_SEG_STT_TO_FIRST_TOKEN = "stt_final_to_llm_first_token"
    METRIC_SEG_TOKEN_TO_SPEAKABLE = "llm_first_token_to_first_speakable_chunk"
    METRIC_SEG_SPEAKABLE_TO_AUDIO = "first_speakable_chunk_to_tts_first_audio"
    METRIC_SEG_SPEECH_END_TO_AUDIO_SENT = "speech_end_to_server_audio_sent"
    # Reserved for Phase 3 adaptive routing (spec 9.8).
    METRIC_ROUTER_LATENCY = "router_latency"
    METRIC_ROUTER_BYPASS_RATE = "router_bypass_rate"

    # Spec 17.1 canonical event names. physical_* and client_* events cannot be
    # produced server-side: physical_* need a reference microphone (human task),
    # client_* arrive via RTVI client messages.
    TIMELINE_EVENTS = (
        "physical_speech_start",
        "vad_speech_start",
        "physical_speech_end",
        "vad_speech_end",
        "turn_finalized",
        "stt_final",
        "llm_request_start",
        "llm_first_token",
        "first_speakable_chunk",
        "tts_request_start",
        "tts_first_audio",
        "server_audio_sent",
        "client_audio_received",
        "client_audible_start",
        "interruption_detected",
        "client_audio_stopped",
    )

    def __init__(self, jsonl_path: str | Path | None = None) -> None:
        self._records: list[dict[str, Any]] = []
        self._lock = asyncio.Lock()
        self._jsonl_path = Path(jsonl_path) if jsonl_path else None
        if self._jsonl_path:
            self._jsonl_path.parent.mkdir(parents=True, exist_ok=True)

    async def record(
        self,
        metric_name: str,
        value_ms: float,
        *,
        session_id: str = "",
        device_id: str = "",
        profile: str = "",
        source: str = "server",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        if value_ms < 0 or not math.isfinite(value_ms):
            logger.warning("invalid_latency_rejected", metric=metric_name, value_ms=value_ms)
            return
        record = {
            "timestamp": time.time(),
            "metric": metric_name,
            "value_ms": round(float(value_ms), 3),
            "session_id": session_id,
            "device_id": device_id,
            "profile": profile,
            "source": source,
            "metadata": metadata or {},
        }
        async with self._lock:
            self._records.append(record)
            if self._jsonl_path:
                line = json.dumps(record, ensure_ascii=False, default=str) + "\n"
                await asyncio.to_thread(self._append_line, line)

    def _append_line(self, line: str) -> None:
        assert self._jsonl_path is not None
        with self._jsonl_path.open("a", encoding="utf-8") as handle:
            handle.write(line)

    async def get_summary(
        self,
        metric_name: str,
        *,
        session_id: str | None = None,
        profile: str | None = None,
    ) -> dict[str, Any]:
        async with self._lock:
            values = [
                row["value_ms"]
                for row in self._records
                if row["metric"] == metric_name
                and (session_id is None or row["session_id"] == session_id)
                and (profile is None or row["profile"] == profile)
            ]
        if not values:
            return {}
        ordered = sorted(values)
        return {
            "count": len(ordered),
            "p50": round(_percentile(ordered, 50), 1),
            "p90": round(_percentile(ordered, 90), 1),
            "p95": round(_percentile(ordered, 95), 1),
            "max": round(max(ordered), 1),
        }

    async def get_all_summaries(
        self,
        *,
        session_id: str | None = None,
        profile: str | None = None,
    ) -> dict[str, dict[str, Any]]:
        async with self._lock:
            names = sorted({row["metric"] for row in self._records})
        result: dict[str, dict[str, Any]] = {}
        for name in names:
            summary = await self.get_summary(name, session_id=session_id, profile=profile)
            if summary:
                result[name] = summary
        return result

    async def records(self, *, session_id: str | None = None) -> list[dict[str, Any]]:
        async with self._lock:
            return [
                dict(row)
                for row in self._records
                if session_id is None or row["session_id"] == session_id
            ]

    async def reset(self) -> None:
        async with self._lock:
            self._records.clear()
        if self._jsonl_path and self._jsonl_path.exists():
            await asyncio.to_thread(self._jsonl_path.unlink)
