"""Heuristic small-talk bypass (spec 9.8 router, heuristic tier).

Sits right before the LLM. When the last user message is an unambiguous
greeting/thanks/goodbye/name/how-are-you one-liner, the canned reply is pushed
straight to TTS and the LLMContextFrame is swallowed — 0ms LLM latency.

Conservative on purpose: only short utterances (≤ 6 words) that fully match a
pattern bypass; anything with a school topic or safety signal always goes to
the LLM (which has grounding + safety notes injected upstream).
"""

from __future__ import annotations

import random
import re

from pipecat.frames.frames import (
    Frame,
    LLMFullResponseEndFrame,
    LLMFullResponseStartFrame,
    TextFrame,
)
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor

from app.logging_utils import get_logger
from app.processors.turn_grounding import _SAFETY_PATTERNS, _SCHOOL_TOPIC

logger = get_logger(__name__)

_MAX_WORDS = 6

# (intent, full-ish match pattern, reply templates). {name} = persona name.
_RULES: list[tuple[str, re.Pattern, list[str]]] = [
    ("greeting", re.compile(
        r"^(xin chào|chào( bạn| em| cậu)?|hello|hi|alo)[\s!.,~]*$", re.IGNORECASE),
     ["Chào bạn nè! Hôm nay bạn cần mình giúp gì không?",
      "Hí lô! Mình nghe nè.",
      "Chào bạn! Gặp bạn vui ghê."]),
    ("name", re.compile(
        r"^(cho\s+(mình|tôi)\s+hỏi\s+)?(vậy\s+)?(bạn|em|cậu|cô)?\s*(là|tên|tên là)\s*(ai|gì|chi)(\s+vậy|\s+đó|\s+đấy|\s+nè|\s+ạ)?[\s!.,~?]*$|^tên\s+(bạn|em|cậu)\s+là\s+gì[\s!.,~?]*$",
        re.IGNORECASE),
     ["Dạ, mình là {name}, trợ lý AI của Trường Đại Nam nè! Rất vui được gặp bạn.",
      "Mình là {name} nè! Mình luôn ở đây để hỗ trợ bạn học tập và tìm kiếm thông tin nha."]),


    ("how_are_you", re.compile(
        r"^(bạn|em|cậu)?\s*(có )?khỏe (không|hông|hem)\??$", re.IGNORECASE),
     ["Mình khỏe re à! Còn bạn thì sao nè?",
      "Mình vẫn chạy ngon lành nè, cảm ơn bạn hỏi thăm!"]),
    ("thanks", re.compile(
        r"^(cảm ơn|cám ơn)( bạn| em| cậu| nhiều| nha| nhé)*[\s!.,~]*$", re.IGNORECASE),
     ["Hổng có chi nè! Cần gì cứ gọi mình nha.",
      "Dạ không có gì đâu, mình vui mà!"]),
    ("goodbye", re.compile(
        r"^(tạm biệt|bye( bye)?|chào tạm biệt|hẹn gặp lại)( bạn| em| cậu| nha| nhé)*[\s!.,~]*$",
        re.IGNORECASE),
     ["Tạm biệt bạn nha, hẹn gặp lại!",
      "Bye bạn nè! Khi nào cần cứ ghé mình."]),
]


def match_small_talk(text: str, *, persona_name: str) -> str | None:
    """Return a canned reply, or None if the utterance must go to the LLM."""
    cleaned = text.strip()
    if not cleaned or len(cleaned.split()) > _MAX_WORDS:
        return None
    if _SCHOOL_TOPIC.search(cleaned):
        return None
    if any(p.search(cleaned) for _, p in _SAFETY_PATTERNS):
        return None
    for intent, pattern, replies in _RULES:
        if pattern.match(cleaned):
            reply = random.choice(replies).format(name=persona_name)
            logger.info("small_talk_bypass", intent=intent, text=cleaned[:40])
            return reply
    return None


class SmallTalkBypassProcessor(FrameProcessor):
    def __init__(self, context, *, persona_name: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self._context = context
        self._persona_name = persona_name

    async def process_frame(self, frame: Frame, direction: FrameDirection) -> None:
        await super().process_frame(frame, direction)
        if type(frame).__name__ == "LLMContextFrame":
            try:
                reply = match_small_talk(
                    self._last_user_text(), persona_name=self._persona_name
                )
            except Exception as exc:  # bypass bug must never kill the turn
                logger.error("small_talk_bypass_failed", error=str(exc))
                reply = None
            if reply is not None:
                # Swallow the context frame (LLM never runs) and speak directly.
                await self.push_frame(LLMFullResponseStartFrame(), direction)
                await self.push_frame(TextFrame(reply), direction)
                await self.push_frame(LLMFullResponseEndFrame(), direction)
                return
        await self.push_frame(frame, direction)

    def _last_user_text(self) -> str:
        for msg in reversed(list(self._context.messages)):
            role = msg.get("role") if isinstance(msg, dict) else getattr(msg, "role", "")
            if role == "user":
                content = (
                    msg.get("content") if isinstance(msg, dict)
                    else getattr(msg, "content", "")
                )
                return content if isinstance(content, str) else ""
        return ""
