"""Deterministic project-internal providers used only for offline tests.

These classes are *not* speech recognition or natural speech synthesis. They
exercise Pipecat frame flow, sentence aggregation and interruption semantics
without external API keys. Real microphone acceptance uses the ``google_vi``
profile instead.
"""

from __future__ import annotations

import asyncio
import math
import struct
import time
from collections import deque
from collections.abc import AsyncGenerator, Sequence
from typing import Any

from pydantic import BaseModel, Field

from pipecat.frames.frames import (
    CancelFrame,
    Frame,
    InterimTranscriptionFrame,
    InterruptionFrame,
    LLMFullResponseEndFrame,
    LLMFullResponseStartFrame,
    TextFrame,
    TranscriptionFrame,
    TTSAudioRawFrame,
)
from pipecat.processors.frame_processor import FrameDirection
from pipecat.services.ai_service import AIService
from pipecat.services.settings import TTSSettings
from pipecat.services.tts_service import TTSService, TextAggregationMode

from app.logging_utils import get_logger

logger = get_logger(__name__)


DEFAULT_SCRIPTED_TRANSCRIPTS = [
    "Xin chào, tôi là người dùng thử nghiệm",
    "Tên tôi là Minh Hiếu",
    "Tôi vừa nói tên gì",
]


class MockSTTService(AIService):
    """Scripted transcription source for deterministic pipeline tests.

    It reacts to VAD stop frames and emits the next configured transcript. It
    does not inspect or understand microphone content and must never be used as
    evidence that ASR works.
    """

    class Settings(BaseModel):
        delay_ms: int = 50
        language: str = "vi-VN"
        transcripts: list[str] = Field(default_factory=lambda: list(DEFAULT_SCRIPTED_TRANSCRIPTS))

    def __init__(self, *, settings: Settings | None = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._mock_settings = settings or self.Settings()
        self._transcripts: deque[str] = deque(self._mock_settings.transcripts)
        self._cancelled = False

    def queue_transcript(self, text: str) -> None:
        """Append a deterministic transcript for a later test turn."""
        self._transcripts.append(text)

    async def process_frame(self, frame: Frame, direction: FrameDirection) -> None:
        await super().process_frame(frame, direction)

        if isinstance(frame, (CancelFrame, InterruptionFrame)):
            self._cancelled = True
            await self.push_frame(frame, direction)
            return

        frame_name = type(frame).__name__
        if frame_name == "VADUserStartedSpeakingFrame":
            self._cancelled = False
            await self.push_frame(frame, direction)
            return

        if frame_name == "VADUserStoppedSpeakingFrame":
            await self.push_frame(frame, direction)
            if not self._cancelled:
                await asyncio.sleep(self._mock_settings.delay_ms / 1000.0)
                await self._emit_transcription()
            return

        await self.push_frame(frame, direction)

    async def _emit_transcription(self) -> None:
        text = self._transcripts.popleft() if self._transcripts else "Kiểm thử không có transcript mới"
        await self.push_frame(
            InterimTranscriptionFrame(
                text=text[: max(1, len(text) // 2)],
                user_id="mock-user",
                timestamp=str(time.time()),
            )
        )
        await self.push_frame(
            TranscriptionFrame(text=text, user_id="mock-user", timestamp=str(time.time()))
        )
        logger.info("mock_scripted_transcription", text=text)


DEFAULT_MOCK_RESPONSES = [
    "Xin chào bạn. Đây là phản hồi kiểm thử thứ hai.",
    "Tôi đã ghi nhận tên Minh Hiếu. Phiên này đang được cô lập.",
    "Bạn vừa nói tên Minh Hiếu. Đây là câu thứ hai để kiểm tra tổng hợp.",
]


class MockLLMService(AIService):
    """Deterministic token-streaming LLM test double."""

    class Settings(BaseModel):
        token_delay_ms: int = 10
        responses: list[str] = Field(default_factory=lambda: list(DEFAULT_MOCK_RESPONSES))

    def __init__(self, *, settings: Settings | None = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._mock_settings = settings or self.Settings()
        self._responses: deque[str] = deque(self._mock_settings.responses)
        self._interrupted = False

    async def process_frame(self, frame: Frame, direction: FrameDirection) -> None:
        await super().process_frame(frame, direction)

        if isinstance(frame, (CancelFrame, InterruptionFrame)):
            self._interrupted = True
            await self.push_frame(frame, direction)
            return

        if type(frame).__name__ == "LLMContextFrame":
            self._interrupted = False
            await self._stream_response()
            return

        await self.push_frame(frame, direction)

    async def _stream_response(self) -> None:
        response = self._responses.popleft() if self._responses else DEFAULT_MOCK_RESPONSES[-1]
        await self.push_frame(LLMFullResponseStartFrame())
        await self.start_ttfb_metrics()
        await self.start_processing_metrics()

        for index, token in enumerate(response.split(" ")):
            if self._interrupted:
                break
            if index == 0:
                await self.stop_ttfb_metrics()
            text = token if index == 0 else f" {token}"
            await self.push_frame(TextFrame(text=text))
            await asyncio.sleep(self._mock_settings.token_delay_ms / 1000.0)

        await self.stop_processing_metrics()
        await self.push_frame(LLMFullResponseEndFrame())
        logger.info("mock_llm_response", interrupted=self._interrupted, response=response)


def _generate_sine_wave(
    *,
    frequency: float,
    duration_ms: int,
    sample_rate: int,
    amplitude: float = 0.18,
) -> bytes:
    num_samples = int(sample_rate * duration_ms / 1000)
    samples = [
        int(amplitude * math.sin(2 * math.pi * frequency * (i / sample_rate)) * 32767)
        for i in range(num_samples)
    ]
    return struct.pack(f"<{len(samples)}h", *samples)


class MockTTSService(TTSService):
    """Sentence-aggregating tone generator for transport tests.

    ``TTSService`` performs the actual sentence aggregation. ``run_tts`` is
    invoked once per aggregated sentence and records the received text so tests
    can prove that synthesis is not invoked token-by-token.
    """

    class Settings(BaseModel):
        sample_rate: int = 24000
        milliseconds_per_sentence: int = 180
        frequency: float = 440.0

    def __init__(
        self,
        *,
        settings: Settings | None = None,
        request_recorder: list[str] | None = None,
        **kwargs: Any,
    ) -> None:
        self._mock_settings = settings or self.Settings()
        self.requests = request_recorder if request_recorder is not None else []
        super().__init__(
            text_aggregation_mode=TextAggregationMode.SENTENCE,
            push_start_frame=True,
            push_stop_frames=True,
            sample_rate=self._mock_settings.sample_rate,
            settings=TTSSettings(model=None, voice="test-tone", language="vi-VN"),
            **kwargs,
        )

    async def run_tts(self, text: str, context_id: str) -> AsyncGenerator[Frame | None, None]:
        normalized = text.strip()
        if not normalized:
            return
        self.requests.append(normalized)
        logger.info("mock_tts_sentence_request", context_id=context_id, text=normalized)
        audio = _generate_sine_wave(
            frequency=self._mock_settings.frequency,
            duration_ms=self._mock_settings.milliseconds_per_sentence,
            sample_rate=self._mock_settings.sample_rate,
        )
        yield TTSAudioRawFrame(
            audio=audio,
            sample_rate=self._mock_settings.sample_rate,
            num_channels=1,
            context_id=context_id,
        )


def make_mock_stt(transcripts: Sequence[str] | None = None) -> MockSTTService:
    settings = MockSTTService.Settings(
        transcripts=list(transcripts or DEFAULT_SCRIPTED_TRANSCRIPTS)
    )
    return MockSTTService(settings=settings, name="MockScriptedSTT")
