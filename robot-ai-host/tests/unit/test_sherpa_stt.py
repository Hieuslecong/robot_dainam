"""Sherpa STT service tests — real decode on the cached round-1 winner model."""

import asyncio
import math
import struct

import pytest

pytest.importorskip("sherpa_onnx")


def _model_cached() -> bool:
    from pathlib import Path

    cache = Path.home() / ".cache/huggingface/hub"
    return any(cache.glob("models--csukuangfj--sherpa-onnx-zipformer-vi-int8*"))


pytestmark = pytest.mark.skipif(not _model_cached(), reason="zipformer model not in HF cache")


@pytest.fixture(scope="module")
def service():
    from app.pipecat_runtime.sherpa_stt import SherpaSTTService

    svc = SherpaSTTService(name="TestSherpa")
    svc._sample_rate = 16000  # normally set by StartFrame
    return svc


def _tone(seconds: float = 0.5, rate: int = 16000) -> bytes:
    n = int(seconds * rate)
    samples = [int(0.1 * math.sin(2 * math.pi * 440 * i / rate) * 32767) for i in range(n)]
    return struct.pack(f"<{n}h", *samples)


def test_silence_yields_no_hallucination(service):
    """Silence must never produce a transcription (spec 8.6 hallucination gate).

    Known limitation (documented in report 02): the zipformer transducer CAN
    hallucinate tokens on loud non-speech audio (e.g. pure tones). In the real
    pipeline Silero VAD only forwards speech-like segments, and the service's
    RMS gate drops silence; tonal-noise robustness must be measured in the
    round-2 corpus (noise/echo/silence categories).
    """

    async def collect(audio):
        frames = []
        async for frame in service.run_stt(audio):
            if frame is not None:
                frames.append(frame)
        return frames

    silence = b"\x00\x00" * 8000
    assert asyncio.run(collect(silence)) == []
    quiet_noise = b"\x02\x00\xfe\xff" * 4000  # ±2 amplitude dither — far below speech RMS
    assert asyncio.run(collect(quiet_noise)) == []


def test_decode_is_fast(service):
    import time

    start = time.monotonic()
    asyncio.run(_drain(service, _tone(1.0)))
    assert time.monotonic() - start < 2.0  # decode of 1s audio well under gate


async def _drain(service, audio):
    async for _ in service.run_stt(audio):
        pass
