"""Sherpa-onnx Zipformer Vietnamese STT service (spec 8.1 `stt_streaming_vi`).

Round-1 VIVOS result that justifies this runtime integration (report 02):
WER 9.39% (vs 14.71% current default), decode P50 0.088 s (vs 1.696 s) —
the only candidate under the ≤900 ms speech-end→final gate on M1.

Decodes the VAD-segmented buffer with the sherpa-onnx offline (non-streaming
API) recognizer — decode is ~0.1 s, so segment-level decoding already meets the
gate without true streaming decode. sherpa-onnx resamples internally via its
feature extractor, so the pipeline sample rate is passed straight through.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from pathlib import Path

import numpy as np

from pipecat.frames.frames import ErrorFrame, Frame, TranscriptionFrame
from pipecat.services.settings import STTSettings
from pipecat.services.stt_service import SegmentedSTTService
from pipecat.transcriptions.language import Language
from pipecat.utils.time import time_now_iso8601

from app.logging_utils import get_logger

logger = get_logger(__name__)

DEFAULT_MODEL_REPO = "csukuangfj/sherpa-onnx-zipformer-vi-int8-2025-04-20"


def _build_recognizer(model_repo: str):
    import sherpa_onnx
    from huggingface_hub import snapshot_download

    snap = Path(snapshot_download(model_repo))
    return sherpa_onnx.OfflineRecognizer.from_transducer(
        tokens=str(next(snap.rglob("tokens.txt"))),
        encoder=str(next(snap.rglob("encoder*.onnx"))),
        decoder=str(next(snap.rglob("decoder*.onnx"))),
        joiner=str(next(snap.rglob("joiner*.onnx"))),
        num_threads=2,
    )


class SherpaSTTService(SegmentedSTTService):
    """Segment-level Vietnamese STT on sherpa-onnx Zipformer."""

    @property
    def wants_wav_segments(self) -> bool:
        return False  # raw s16le PCM

    def __init__(self, *, model_repo: str = DEFAULT_MODEL_REPO, **kwargs) -> None:
        super().__init__(
            settings=STTSettings(model=model_repo, language=Language.VI),
            **kwargs,
        )
        self._recognizer = _build_recognizer(model_repo)
        logger.info("sherpa_stt_loaded", model=model_repo)

    def can_generate_metrics(self) -> bool:
        return True

    # Below this RMS the segment is treated as silence and never decoded —
    # transducer models can hallucinate tokens on non-speech input (gate 8.6).
    SILENCE_RMS = 0.005

    def _decode(self, audio: bytes, sample_rate: int) -> str:
        samples = np.frombuffer(audio, dtype=np.int16).astype(np.float32) / 32768.0
        if samples.size == 0 or float(np.sqrt(np.mean(samples**2))) < self.SILENCE_RMS:
            return ""
        stream = self._recognizer.create_stream()
        stream.accept_waveform(sample_rate, samples)
        self._recognizer.decode_stream(stream)
        return stream.result.text.strip()

    async def run_stt(self, audio: bytes) -> AsyncGenerator[Frame | None, None]:
        if self._recognizer is None:
            yield ErrorFrame("Sherpa recognizer not available")
            return

        await self.start_processing_metrics()
        try:
            text = await asyncio.to_thread(self._decode, audio, self.sample_rate)
        except Exception as exc:
            await self.stop_processing_metrics()
            logger.warning("sherpa_stt_failed", error=str(exc))
            yield ErrorFrame(f"Sherpa STT failed: {exc}")
            return
        await self.stop_processing_metrics()

        if text:
            logger.debug(f"Transcription: [{text}]")
            yield TranscriptionFrame(text, self._user_id, time_now_iso8601(), Language.VI)
