"""VieNeu-TTS expressive engine adapter for the two-tier TTS (spec 16.1/16.2a).

Wraps the synchronous ``vieneu`` SDK (v3 Turbo, CPU→ONNX) behind an async
callable returning PCM s16le + sample rate, run in a worker thread so the
event loop never blocks. Expression styles map to VieNeu's built-in styles.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator

import numpy as np

from app.logging_utils import get_logger

logger = get_logger(__name__)

VIENEU_SAMPLE_RATE = 48000


def speed_shift(wave: np.ndarray, factor: float) -> np.ndarray:
    """Speed up playback by ``factor`` — raises pitch AND tempo together.

    ponytail: plain resample, no formant preservation; good enough for ≤~1.12.
    """
    if factor == 1.0 or wave.size == 0:
        return wave
    target_len = max(1, int(wave.size / factor))
    positions = np.linspace(0, wave.size - 1, target_len)
    return np.interp(positions, np.arange(wave.size), wave).astype(np.float32)

# Expression Composer style (spec 15.2) → VieNeu v3 Turbo style token.
# The model knows exactly three styles (config style_labels): tu_nhien,
# tin_tuc, doc_truyen — anything else silently falls back to tu_nhien.
STYLE_MAP = {
    "neutral": "tu_nhien",
    "friendly": "tu_nhien",
    "cheerful": "doc_truyen",
    "calm": "tu_nhien",
    "empathetic": "doc_truyen",
    "encouraging": "doc_truyen",
    "serious": "tin_tuc",
}


class VieNeuEngine:
    """VieNeu synthesizer with explicit warm-up.

    Model load takes tens of seconds on M1; loading lazily inside the two-tier
    render budget would time out every early sentence. ``start_warm_up()`` loads
    in the background at pipeline build; until ready, ``synthesize`` raises and
    the two-tier service cleanly falls back to Piper for that sentence.
    """

    def __init__(
        self,
        voice: str | None = None,
        *,
        speed: float = 1.0,
        temperature: float = 0.8,
    ) -> None:
        self._tts = None
        self._voice = voice or None  # empty string → SDK default preset
        self._speed = speed
        self._temperature = temperature
        self._lock = asyncio.Lock()
        self._warm_task: asyncio.Task | None = None

    @property
    def ready(self) -> bool:
        return self._tts is not None

    def start_warm_up(self) -> None:
        if self._warm_task is None and not self.ready:
            self._warm_task = asyncio.get_running_loop().create_task(self._warm_up())

    async def _warm_up(self) -> None:
        try:
            logger.info("vieneu_loading")
            self._tts = await asyncio.to_thread(self._build)
            logger.info("vieneu_loaded")
        except Exception as exc:
            logger.warning("vieneu_load_failed", error=str(exc))

    @staticmethod
    def _build():
        from vieneu import Vieneu

        return Vieneu()  # v3turbo default; CPU runs ONNX int8

    async def synthesize(self, text: str, *, style: str = "friendly") -> tuple[bytes, int]:
        if not self.ready:
            self.start_warm_up()
            raise RuntimeError("vieneu_warming_up")
        async with self._lock:  # one render at a time on CPU
            audio = await asyncio.to_thread(self._render, text, style)
        return audio, VIENEU_SAMPLE_RATE

    async def synthesize_stream(
        self, text: str, *, style: str = "friendly"
    ) -> AsyncGenerator[tuple[bytes, int], None]:
        """Yield PCM chunks as VieNeu produces them (native codec streaming).

        First audio arrives after ~0.5s instead of after the full sentence
        render. The blocking SDK generator runs in a worker thread and hands
        chunks over via an asyncio queue.
        """
        if not self.ready:
            self.start_warm_up()
            raise RuntimeError("vieneu_warming_up")
        import threading

        loop = asyncio.get_running_loop()
        queue: asyncio.Queue = asyncio.Queue(maxsize=4)
        done = object()
        cancelled = threading.Event()  # consumer gone (barge-in) → stop rendering

        def _put(item) -> bool:
            while not cancelled.is_set():
                try:
                    asyncio.run_coroutine_threadsafe(queue.put(item), loop).result(timeout=1.0)
                    return True
                except TimeoutError:
                    continue  # queue full and consumer still alive — retry
                except Exception:
                    return False  # loop closed
            return False

        def producer() -> None:
            try:
                kwargs = {
                    "style": STYLE_MAP.get(style, "tu_nhien"),
                    "temperature": self._temperature,
                }
                if self._voice:
                    kwargs["voice"] = self._voice
                for chunk in self._tts.infer_stream(text, **kwargs):
                    arr = speed_shift(np.asarray(chunk, dtype=np.float32), self._speed)
                    pcm = (np.clip(arr, -1.0, 1.0) * 32767).astype(np.int16).tobytes()
                    if pcm and not _put(pcm):
                        return  # cancelled mid-render: drop the rest, free the lock
            except Exception as exc:  # surfaced to the async consumer
                _put(exc)
                return
            _put(done)

        async with self._lock:  # one render at a time on CPU
            worker = loop.run_in_executor(None, producer)
            try:
                while True:
                    item = await queue.get()
                    if item is done:
                        break
                    if isinstance(item, Exception):
                        raise item
                    yield item, VIENEU_SAMPLE_RATE
            finally:
                cancelled.set()
                # Drain so a producer blocked on a full queue can finish.
                while not queue.empty():
                    queue.get_nowait()
                await worker

    def _render(self, text: str, style: str) -> bytes:
        kwargs = {
            "style": STYLE_MAP.get(style, "tu_nhien"),
            "temperature": self._temperature,
        }
        if self._voice:
            kwargs["voice"] = self._voice
        try:
            wave = self._tts.infer(text, **kwargs)
        except ValueError as exc:
            # Unknown voice name — fall back to the SDK default preset so a
            # config typo degrades the voice, never the whole reply.
            logger.warning("vieneu_voice_fallback", voice=self._voice, error=str(exc))
            self._voice = None
            kwargs.pop("voice", None)
            wave = self._tts.infer(text, **kwargs)
        wave = speed_shift(np.asarray(wave, dtype=np.float32), self._speed)
        wave = np.clip(np.asarray(wave, dtype=np.float32), -1.0, 1.0)
        return (wave * 32767).astype(np.int16).tobytes()
