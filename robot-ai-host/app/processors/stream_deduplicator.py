"""Stream deduplicator — prevents sentences from being sent to TTS/UI twice."""

from __future__ import annotations

import hashlib
import time
from collections.abc import AsyncGenerator

from pipecat.frames.frames import Frame, TTSStoppedFrame
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor


class StreamDeduplicator(FrameProcessor):
    """Drop duplicate sentences within the same turn using normalized hashes."""

    def __init__(self, *, ttl_seconds: float = 30.0, **kwargs):
        super().__init__(**kwargs)
        self._ttl = ttl_seconds
        self._seen: dict[str, float] = {}  # sentence_hash → expiry_time

    def _normalize(self, text: str) -> str:
        return " ".join(text.strip().lower().split())

    def _hash(self, text: str) -> str:
        return hashlib.sha256(text.encode()).hexdigest()[:16]

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)

        from pipecat.frames.frames import TextFrame

        if isinstance(frame, TextFrame):
            text = frame.text.strip()
            if not text:
                await self.push_frame(frame, direction)
                return

            norm = self._normalize(text)
            h = self._hash(norm)
            now = time.monotonic()

            # Clean expired entries
            self._seen = {k: v for k, v in self._seen.items() if v > now}

            if h in self._seen:
                self._logger.debug(f"Dropped duplicate sentence hash={h} text={text[:60]}")
                return

            self._seen[h] = now + self._ttl

        await self.push_frame(frame, direction)
