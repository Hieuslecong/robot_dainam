"""STT Guard — prevents noise, echo, and background audio from reaching the LLM."""

from __future__ import annotations

import hashlib
import time
from typing import Literal

from pipecat.frames.frames import (
    Frame,
    InterimTranscriptionFrame,
    TranscriptionFrame,
)
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor


class STTGuard(FrameProcessor):
    """Filter STT output: block partials, duplicates, echo, short speech."""

    def __init__(
        self,
        *,
        min_speech_ms: float = 300,
        final_only: bool = True,
        duplicate_window_seconds: float = 8.0,
        min_characters: int = 2,
        glossary=None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self._min_speech_ms = min_speech_ms
        self._final_only = final_only
        self._dup_window = duplicate_window_seconds
        self._min_chars = min_characters
        self._glossary = glossary
        self._recent_hashes: dict[str, float] = {}
        self._bot_speaking = False
        self._speech_start: float | None = None

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)

        from pipecat.frames.frames import (
            BotStartedSpeakingFrame,
            BotStoppedSpeakingFrame,
            UserStartedSpeakingFrame,
            UserStoppedSpeakingFrame,
        )

        if isinstance(frame, BotStartedSpeakingFrame):
            self._bot_speaking = True
        elif isinstance(frame, BotStoppedSpeakingFrame):
            self._bot_speaking = False
        elif isinstance(frame, UserStartedSpeakingFrame):
            self._speech_start = time.monotonic()
        elif isinstance(frame, UserStoppedSpeakingFrame):
            self._speech_start = None

        if isinstance(frame, InterimTranscriptionFrame):
            if self._final_only:
                return  # Drop partial transcripts
            if not self._should_pass(frame.text, is_final=False):
                return

        if isinstance(frame, TranscriptionFrame):
            if not self._should_pass(frame.text, is_final=True):
                return
            if self._glossary is not None:
                # Spec 8.3: glossary correction on final transcripts only;
                # originals + confidence are logged by the corrector.
                frame.text = self._glossary.correct(frame.text).text

        await self.push_frame(frame, direction)

    def _should_pass(self, text: str, *, is_final: bool) -> bool:
        text = text.strip()
        if len(text) < self._min_chars:
            self._logger.debug(f"STT dropped (too short): {text!r}")
            return False

        # PR-3.6: Don't blanket-drop transcripts just because bot is speaking.
        # User interjections during bot speech are valid barge-in.
        # Echo prevention uses hash-based dedup (below), not the bot_speaking flag.
        # Only drop if it's an interim, not a final, during bot speech (echo risk).
        if self._bot_speaking and not is_final:
            self._logger.debug(f"STT dropped (interim during bot speech): {text!r}")
            return False

        # Check speech duration minimum (for final transcripts)
        if self._speech_start is not None:
            duration_ms = (time.monotonic() - self._speech_start) * 1000
            if is_final and duration_ms < self._min_speech_ms:
                self._logger.debug(
                    f"STT dropped (too short speech {duration_ms:.0f}ms < {self._min_speech_ms}ms): {text!r}"
                )
                return False

        # Duplicate detection
        norm = " ".join(text.lower().split())
        h = hashlib.sha256(norm.encode()).hexdigest()[:12]
        now = time.monotonic()
        self._recent_hashes = {
            k: v for k, v in self._recent_hashes.items() if v > now
        }
        if h in self._recent_hashes:
            self._logger.debug(f"STT dropped (duplicate): {text!r}")
            return False
        self._recent_hashes[h] = now + self._dup_window

        return True
