"""Pipecat observers that bridge framework metrics into project evidence."""

from __future__ import annotations

import time

from pipecat.frames.frames import (
    BotStartedSpeakingFrame,
    BotStoppedSpeakingFrame,
    MetricsFrame,
    TextFrame,
    TranscriptionFrame,
    TTSAudioRawFrame,
    UserStartedSpeakingFrame,
    UserStoppedSpeakingFrame,
)
from pipecat.metrics.metrics import TextAggregationMetricsData, TTFAMetricsData, TTFBMetricsData
from pipecat.observers.base_observer import BaseObserver, FramePushed
from pipecat.processors.frame_processor import FrameDirection

from app.pipecat_runtime.metrics import LatencyTracker


class TurnTimeline:
    """Absolute (monotonic) event times for one user→bot turn — spec 17.1."""

    def __init__(self) -> None:
        self.events: dict[str, float] = {}

    def mark(self, event: str, at: float) -> None:
        # First occurrence wins: e.g. only the first TTS audio frame of the
        # turn is ``tts_first_audio``.
        self.events.setdefault(event, at)

    def offset_ms(self, event: str, anchor: str = "vad_speech_start") -> float | None:
        if event in self.events and anchor in self.events:
            return (self.events[event] - self.events[anchor]) * 1000
        return None

    def segment_ms(self, start: str, end: str) -> float | None:
        if start in self.events and end in self.events:
            return (self.events[end] - self.events[start]) * 1000
        return None


class RuntimeMetricsObserver(BaseObserver):
    """Collect framework metrics and the unified turn timeline per session."""

    def __init__(
        self,
        *,
        tracker: LatencyTracker,
        session_id: str,
        device_id: str,
        profile: str,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._tracker = tracker
        self._context = {
            "session_id": session_id,
            "device_id": device_id,
            "profile": profile,
        }
        self._barge_started_at: float | None = None
        self._user_stopped_at: float | None = None
        self._bot_speaking = False
        self._turn = TurnTimeline()

    async def _record(self, name: str, value_ms: float, **metadata) -> None:
        await self._tracker.record(name, value_ms, metadata=metadata, **self._context)

    def mark_client_event(self, event: str) -> None:
        """Timeline events reported by the client over RTVI messages."""
        self._turn.mark(event, time.monotonic())

    async def _flush_turn(self) -> None:
        turn = self._turn
        self._turn = TurnTimeline()
        if "vad_speech_start" not in turn.events:
            return
        offsets = {
            name: round(offset, 1)
            for name in LatencyTracker.TIMELINE_EVENTS
            if (offset := turn.offset_ms(name)) is not None
        }
        total = turn.segment_ms("vad_speech_end", "server_audio_sent")
        await self._record(
            LatencyTracker.METRIC_TURN_TIMELINE,
            total if total is not None else 0.0,
            timeline_offsets_ms=offsets,
        )
        for metric, start, end in (
            (LatencyTracker.METRIC_SEG_STT_TO_FIRST_TOKEN, "stt_final", "llm_first_token"),
            (
                LatencyTracker.METRIC_SEG_TOKEN_TO_SPEAKABLE,
                "llm_first_token",
                "first_speakable_chunk",
            ),
            (
                LatencyTracker.METRIC_SEG_SPEAKABLE_TO_AUDIO,
                "first_speakable_chunk",
                "tts_first_audio",
            ),
            (
                LatencyTracker.METRIC_SEG_SPEECH_END_TO_AUDIO_SENT,
                "vad_speech_end",
                "server_audio_sent",
            ),
        ):
            value = turn.segment_ms(start, end)
            if value is not None and value >= 0:
                await self._record(metric, value, measurement="turn_timeline")

    async def on_push_frame(self, data: FramePushed) -> None:
        if data.direction != FrameDirection.DOWNSTREAM:
            return
        frame = data.frame
        now = time.monotonic()
        frame_type = type(frame).__name__

        if isinstance(frame, BotStartedSpeakingFrame):
            self._bot_speaking = True
            self._turn.mark("server_audio_sent", now)
        elif isinstance(frame, UserStartedSpeakingFrame):
            self._user_stopped_at = None
            if self._bot_speaking:
                self._barge_started_at = now
                self._turn.mark("interruption_detected", now)
            else:
                # New turn begins; flush whatever the previous turn collected.
                await self._flush_turn()
                self._turn.mark("vad_speech_start", now)
        elif isinstance(frame, UserStoppedSpeakingFrame):
            self._user_stopped_at = now
            self._turn.mark("vad_speech_end", now)
            # No Smart Turn yet: VAD stop finalizes the turn.
            self._turn.mark("turn_finalized", now)
        elif isinstance(frame, TranscriptionFrame):
            self._turn.mark("stt_final", now)
            if self._user_stopped_at is not None:
                await self._record(
                    LatencyTracker.METRIC_STT_FINAL,
                    (now - self._user_stopped_at) * 1000,
                    measurement="user_stopped_to_final_transcription_frame",
                )
                self._user_stopped_at = None
        elif frame_type == "LLMContextFrame":
            self._turn.mark("llm_request_start", now)
        elif isinstance(frame, TextFrame) and not isinstance(frame, TranscriptionFrame):
            self._turn.mark("llm_first_token", now)
        elif isinstance(frame, TTSAudioRawFrame):
            self._turn.mark("tts_first_audio", now)
        elif frame_type in ("TTSStartedFrame", "TTSTextFrame"):
            self._turn.mark("tts_request_start", now)
        elif isinstance(frame, BotStoppedSpeakingFrame):
            self._bot_speaking = False
            if self._barge_started_at is not None:
                await self._record(
                    LatencyTracker.METRIC_BARGE_IN_STOP,
                    (now - self._barge_started_at) * 1000,
                    measurement="server_frame",
                )
                self._barge_started_at = None
        elif isinstance(frame, MetricsFrame):
            for metric in frame.data:
                processor = metric.processor.lower()
                if isinstance(metric, TTFAMetricsData):
                    await self._record(
                        LatencyTracker.METRIC_TTS_FIRST_AUDIO,
                        metric.ttfa * 1000,
                        processor=metric.processor,
                        model=metric.model,
                        leading_silence_ms=metric.leading_silence * 1000,
                    )
                elif isinstance(metric, TextAggregationMetricsData):
                    self._turn.mark("first_speakable_chunk", now)
                    await self._record(
                        LatencyTracker.METRIC_FIRST_SENTENCE,
                        metric.value * 1000,
                        processor=metric.processor,
                    )
                elif isinstance(metric, TTFBMetricsData):
                    if "stt" in processor:
                        name = LatencyTracker.METRIC_STT_TTFB
                    elif "llm" in processor:
                        name = LatencyTracker.METRIC_LLM_FIRST_TOKEN
                    elif "tts" in processor:
                        name = LatencyTracker.METRIC_TTS_TTFB
                    else:
                        continue
                    await self._record(
                        name,
                        metric.value * 1000,
                        processor=metric.processor,
                        model=metric.model,
                    )
