"""Small, test-driven sanitizer for text spoken by Vietnamese TTS."""

from __future__ import annotations

import re

_FENCED_CODE = re.compile(r"```.*?```", re.DOTALL)
_MARKDOWN_LINK = re.compile(r"\[([^\]]+)\]\((?:https?://|www\.)[^)]+\)")
_URL = re.compile(r"(?:https?://|www\.)\S+", re.IGNORECASE)
_INLINE_CODE = re.compile(r"`([^`]+)`")
_MARKERS = re.compile(r"(?m)^\s{0,3}(?:#{1,6}\s+|[-*+]\s+|>\s*)")
# "1. Bước..." list numbering: the sentence aggregator would split "1." into
# its own sentence and TTS babbles on letter-less input — drop the marker.
_LIST_NUMBER = re.compile(r"(?m)(?:^|(?<=[.!?…:]\s))\d{1,2}[.)]\s+")
_WHITESPACE = re.compile(r"\s+")
# VieNeu v3 Turbo non-verbal cues, rendered as real sounds by that engine.
# Other engines (Piper) would read them aloud, so they get stripped there.
_EMOTION_TAGS = re.compile(r"\[(?:cười|thở dài|hắng giọng|chuckle|sigh|clear throat)\]", re.IGNORECASE)


def strip_emotion_tags(text: str) -> str:
    """Remove VieNeu emotion tags for engines that would vocalize them."""
    return _WHITESPACE.sub(" ", _EMOTION_TAGS.sub(" ", text)).strip()


def sanitize_spoken_vietnamese(text: str) -> str:
    """Remove content that should not be vocalized while preserving numbers/diacritics."""

    value = _FENCED_CODE.sub(" ", text)
    value = _MARKDOWN_LINK.sub(r"\1", value)
    value = _URL.sub(" liên kết ", value)
    value = _INLINE_CODE.sub(r"\1", value)
    value = _MARKERS.sub("", value)
    value = _LIST_NUMBER.sub("", value)
    value = value.replace("**", "").replace("__", "").replace("~~", "")
    return _WHITESPACE.sub(" ", value).strip()
