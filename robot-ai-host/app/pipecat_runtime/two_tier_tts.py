"""Two-tier TTS (spec 16.2a): Piper opener + expressive tier, latency-masked.

Tier roles (NOT the error-fallback chain, which is 16.2):
- First sentence of a turn → opener engine (Piper, low TTFA) — plays immediately.
- Later sentences → expressive engine (VieNeu), rendered WHILE the opener audio
  is playing. If the expressive render would exceed the playback mask window
  plus the allowed gap (≤700 ms), that sentence falls back to the opener engine.

Both engines are injected as callables so unit tests use deterministic fakes
and the real wiring picks Piper HTTP + VieNeu.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncGenerator, Awaitable, Callable
from dataclasses import dataclass

import numpy as np

from pipecat.frames.frames import Frame, TTSAudioRawFrame
from pipecat.services.settings import TTSSettings
from pipecat.services.tts_service import TTSService, TextAggregationMode

from app.logging_utils import get_logger
from app.pipecat_runtime.text_sanitizer import strip_emotion_tags

logger = get_logger(__name__)

CHUNK_BYTES = 9600  # 200 ms at 24 kHz s16le — stream like the stock services do


def resample_s16(audio: bytes, from_rate: int, to_rate: int) -> bytes:
    """Linear-resample s16le mono PCM. One resample per sentence (spec 16.5)."""
    if from_rate == to_rate or not audio:
        return audio
    samples = np.frombuffer(audio, dtype=np.int16).astype(np.float32)
    target_len = max(1, int(len(samples) * to_rate / from_rate))
    positions = np.linspace(0, len(samples) - 1, target_len)
    resampled = np.interp(positions, np.arange(len(samples)), samples)
    return np.clip(resampled, -32768, 32767).astype(np.int16).tobytes()

# Synthesize(text) → (pcm_s16le_bytes, sample_rate). Raise on failure.
SynthesizeFn = Callable[[str], Awaitable[tuple[bytes, int]]]
# Streaming variant: async generator of (pcm_chunk, sample_rate).
SynthesizeStreamFn = Callable[[str], AsyncGenerator[tuple[bytes, int], None]]

# A streaming sentence whose next chunk stalls this long is abandoned.
STREAM_CHUNK_TIMEOUT_S = 10.0

MAX_INTER_TIER_GAP_S = 0.7  # spec 16.6: opener→expressive silence P95 ≤700 ms


@dataclass
class _TurnState:
    context_id: str
    started_at: float
    queued_audio_s: float = 0.0
    sentences: int = 0

    def playback_remaining_s(self) -> float:
        return max(0.0, self.queued_audio_s - (time.monotonic() - self.started_at))


class TwoTierTTSService(TTSService):
    def __init__(
        self,
        *,
        opener: SynthesizeFn,
        expressive: SynthesizeFn | None,
        expressive_stream: SynthesizeStreamFn | None = None,
        opener_first: bool = True,
        first_sentence_timeout_s: float = 8.0,
        expressive_min_render_estimate_s: float = 1.0,
        sample_rate: int = 24000,
        **kwargs,
    ) -> None:
        self._opener = opener
        self._expressive = expressive
        self._expressive_stream = expressive_stream
        # opener_first=False → one voice for the whole reply (expressive tier
        # owns every sentence, Piper is error-fallback only).
        self._opener_first = opener_first
        self._first_timeout_s = first_sentence_timeout_s
        self._estimate_s = expressive_min_render_estimate_s
        self._configured_rate = sample_rate
        self._turn: _TurnState | None = None
        self.tier_log: list[tuple[str, str]] = []  # (tier, sentence) evidence
        super().__init__(
            text_aggregation_mode=TextAggregationMode.SENTENCE,
            push_start_frame=True,
            push_stop_frames=True,
            sample_rate=sample_rate,
            settings=TTSSettings(model=None, voice="two-tier-vi", language="vi-VN"),
            **kwargs,
        )

    def _budget_for_expressive(self, turn: _TurnState) -> float:
        # Render may take as long as the already-queued playback plus the
        # allowed inter-tier gap; single-sentence turns get the flat estimate.
        return turn.playback_remaining_s() + MAX_INTER_TIER_GAP_S

    async def run_tts(self, text: str, context_id: str) -> AsyncGenerator[Frame | None, None]:
        sentence = text.strip()
        # Fragments without a real word ("3.", ".", "…", a bare "[cười]") make
        # TTS models babble — require at least one letter outside emotion tags.
        if not sentence or not any(ch.isalpha() for ch in strip_emotion_tags(sentence)):
            return

        if self._turn is None or self._turn.context_id != context_id:
            self._turn = _TurnState(context_id=context_id, started_at=time.monotonic())
        turn = self._turn
        turn.sentences += 1

        has_expressive = self._expressive is not None or self._expressive_stream is not None
        use_expressive = has_expressive and (
            turn.sentences > 1  # opener tier owns the first sentence...
            or not self._opener_first  # ...unless single-voice mode is on
        )
        out_rate = self.sample_rate or self._configured_rate

        stream_failed = False
        if use_expressive and self._expressive_stream is not None:
            budget = self._budget_for_expressive(turn)
            if turn.sentences == 1:
                budget = self._first_timeout_s
            gen = self._expressive_stream(sentence)
            # The finally MUST close the engine generator on every exit path —
            # including the CancelledError a barge-in raises at any await/yield
            # here. An abandoned generator keeps the render thread going and
            # holds the engine lock forever (bug: "không cắt ngang được").
            try:
                try:
                    first_chunk, in_rate = await asyncio.wait_for(
                        gen.__anext__(), timeout=max(budget, self._estimate_s)
                    )
                except (asyncio.TimeoutError, StopAsyncIteration, Exception) as exc:  # noqa: BLE001
                    logger.warning(
                        "expressive_stream_fallback",
                        reason=type(exc).__name__,
                        budget_s=round(budget, 2),
                        sentence=sentence[:60],
                    )
                    stream_failed = True
                else:
                    self.tier_log.append(("expressive", sentence))
                    logger.info(
                        "two_tier_tts_sentence",
                        tier="expressive",
                        streaming=True,
                        sentence_index=turn.sentences,
                        context_id=context_id,
                    )
                    chunk = resample_s16(first_chunk, in_rate, out_rate)
                    turn.queued_audio_s += len(chunk) / 2 / out_rate
                    yield TTSAudioRawFrame(
                        audio=chunk, sample_rate=out_rate, num_channels=1, context_id=context_id
                    )
                    while True:
                        try:
                            nxt, in_rate = await asyncio.wait_for(
                                gen.__anext__(), timeout=STREAM_CHUNK_TIMEOUT_S
                            )
                        except StopAsyncIteration:
                            break
                        except Exception as exc:  # noqa: BLE001
                            # Part of the sentence already played — abandon the
                            # rest rather than re-speaking it in another voice.
                            logger.error(
                                "expressive_stream_aborted",
                                error=str(exc),
                                sentence=sentence[:60],
                            )
                            break
                        chunk = resample_s16(nxt, in_rate, out_rate)
                        turn.queued_audio_s += len(chunk) / 2 / out_rate
                        yield TTSAudioRawFrame(
                            audio=chunk, sample_rate=out_rate, num_channels=1, context_id=context_id
                        )
            finally:
                await gen.aclose()
            if not stream_failed:
                return

        audio: bytes | None = None
        rate = 0
        tier = "opener"
        if use_expressive and self._expressive is not None and not stream_failed:
            budget = self._budget_for_expressive(turn)
            if turn.sentences == 1:
                # No opener audio masks the wait — allow the flat first-sentence
                # timeout so the whole reply keeps one voice.
                budget = self._first_timeout_s
            try:
                audio, rate = await asyncio.wait_for(
                    self._expressive(sentence), timeout=max(budget, self._estimate_s)
                )
                tier = "expressive"
            except (asyncio.TimeoutError, Exception) as exc:  # noqa: BLE001
                logger.warning(
                    "expressive_tier_fallback",
                    reason=type(exc).__name__,
                    budget_s=round(budget, 2),
                    sentence=sentence[:60],
                )
        if audio is None:
            try:
                audio, rate = await self._opener(sentence)
            except Exception as exc:
                # A sentence must never be silently dropped (user-facing bug):
                # log loudly; the turn continues with the next sentence.
                logger.error("two_tier_opener_failed", error=str(exc), sentence=sentence[:60])
                return
            tier = "opener"

        # Normalize to the service sample rate — mixed-rate frames are dropped
        # or mis-played by the transport (root cause of "câu 2 không đọc").
        out_rate = self.sample_rate or self._configured_rate
        audio = resample_s16(audio, rate, out_rate)

        self.tier_log.append((tier, sentence))
        turn.queued_audio_s += len(audio) / 2 / out_rate  # s16le mono
        logger.info(
            "two_tier_tts_sentence",
            tier=tier,
            sentence_index=turn.sentences,
            context_id=context_id,
        )
        for start in range(0, len(audio), CHUNK_BYTES):
            yield TTSAudioRawFrame(
                audio=audio[start : start + CHUNK_BYTES],
                sample_rate=out_rate,
                num_channels=1,
                context_id=context_id,
            )


async def piper_synthesize(session, base_url: str, voice: str, text: str) -> tuple[bytes, int]:
    """Minimal Piper HTTP client returning raw PCM (strips the WAV header)."""
    import io
    import wave

    async with session.post(base_url, json={"text": text, "voice": voice}) as resp:
        resp.raise_for_status()
        payload = await resp.read()
    with wave.open(io.BytesIO(payload)) as wav:
        return wav.readframes(wav.getnframes()), wav.getframerate()
