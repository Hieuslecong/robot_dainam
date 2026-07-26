"""Official Pipecat BaseTextFilter adapter for Vietnamese speech sanitization."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from pipecat.utils.text.base_text_filter import BaseTextFilter

from app.pipecat_runtime.text_sanitizer import sanitize_spoken_vietnamese, strip_emotion_tags


class VietnameseSpeechTextFilter(BaseTextFilter):
    def __init__(self, *, strip_tags: bool = False) -> None:
        # strip_tags=True for engines that would read "[cười]" aloud (Piper).
        # VieNeu renders the tags as real non-verbal sounds — keep them there.
        self._strip_tags = strip_tags

    async def filter(self, text: str) -> str:
        value = sanitize_spoken_vietnamese(text)
        return strip_emotion_tags(value) if self._strip_tags else value

    async def update_settings(self, settings: Mapping[str, Any]):
        return None
