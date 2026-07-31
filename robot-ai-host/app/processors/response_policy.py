"""Response policy — hard ceiling on sentences/words per LLM response.

The LLM streams TextFrames as small deltas, so per-frame counting can never
trigger (the original bug: 200-word replies sailed through a 3-sentence cap).
This processor counts CUMULATIVELY across one response: reset on
LLMFullResponseStartFrame, then swallow every TextFrame after the budget is
spent until LLMFullResponseEndFrame. The cap is an overflow guard — everyday
brevity is steered by the system prompt.
"""

from __future__ import annotations

import re

from pipecat.frames.frames import (
    Frame,
    LLMFullResponseEndFrame,
    LLMFullResponseStartFrame,
    TextFrame,
)
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor

from app.logging_utils import get_logger

logger = get_logger(__name__)

_SENTENCE_END = re.compile(r"[.!?…](?=\s|$)")


class ResponsePolicyProcessor(FrameProcessor):
    """Cumulative per-response limiter for streamed LLM text."""

    def __init__(
        self,
        *,
        max_sentences: int = 8,
        max_words: int = 150,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self._max_sentences = max_sentences
        self._max_words = max_words
        self._sentences = 0
        self._words = 0
        self._truncating = False

    def _reset(self) -> None:
        self._sentences = 0
        self._words = 0
        self._truncating = False

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)

        if isinstance(frame, LLMFullResponseStartFrame):
            self._reset()
        elif isinstance(frame, LLMFullResponseEndFrame):
            if self._truncating:
                logger.warning(
                    "response_truncated",
                    sentences=self._sentences,
                    words=self._words,
                )
            self._reset()
        elif isinstance(frame, TextFrame):
            if self._truncating:
                return  # budget spent, swallow rest of response

            # PR-3.7: count BEFORE pushing, stop at sentence boundary.
            # Do NOT push the frame that exceeds the limit.
            new_sentences = self._sentences + len(_SENTENCE_END.findall(frame.text))
            new_words = self._words + len(frame.text.split())

            if new_sentences > self._max_sentences or new_words > self._max_words:
                self._truncating = True
                logger.info(
                    "response_truncated_at_boundary",
                    sentences=self._sentences,
                    words=self._words,
                    max_sentences=self._max_sentences,
                    max_words=self._max_words,
                )
                return  # don't push the overflowing frame

            self._sentences = new_sentences
            self._words = new_words

        await self.push_frame(frame, direction)
