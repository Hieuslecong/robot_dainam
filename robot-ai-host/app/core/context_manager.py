"""Bounded conversation context: recent-turn cap, rolling summary, reset.

Spec 13.1–13.2: keep the last 6–8 turns verbatim; older turns fold into one
compact summary message so context never grows unbounded. An unfinished
tool-call sequence (assistant ``tool_calls`` without all matching ``tool``
results) is never cut. Summarization here is deterministic (no LLM call) —
it preserves what the user said and what was answered in compressed form;
an LLM-written summary can replace ``_summarize`` when the orchestrator
lands (Phase 3+) without changing callers.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

SUMMARY_PREFIX = "[Tóm tắt hội thoại trước] "


def _get(msg: Any, key: str, default: Any = None) -> Any:
    if isinstance(msg, dict):
        return msg.get(key, default)
    return getattr(msg, key, default)


def _text(msg: Any) -> str:
    content = _get(msg, "content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):  # multimodal parts
        return " ".join(
            str(_get(part, "text", "")) for part in content if _get(part, "text")
        )
    return str(content or "")


@dataclass
class ContextManager:
    """Compacts a chat message list in place-compatible fashion."""

    max_recent_turns: int = 8
    summary_max_chars: int = 1200

    def compact(self, messages: list[Any]) -> list[Any]:
        """Return a bounded message list: head + summary + last N turns."""
        head: list[Any] = []
        body: list[Any] = []
        prior_summary = ""
        for msg in messages:
            role = _get(msg, "role")
            text = _text(msg)
            if role in ("system", "developer") and not body:
                if text.startswith(SUMMARY_PREFIX):
                    prior_summary = text[len(SUMMARY_PREFIX):]
                else:
                    head.append(msg)
            else:
                body.append(msg)

        turn_starts = [
            i for i, msg in enumerate(body) if _get(msg, "role") == "user"
        ]
        if len(turn_starts) <= self.max_recent_turns:
            if prior_summary:
                return head + [self._summary_message(prior_summary)] + body
            return list(messages)

        cut = turn_starts[len(turn_starts) - self.max_recent_turns]
        cut = self._respect_tool_sequences(body, cut)
        dropped, kept = body[:cut], body[cut:]
        summary = self._summarize(prior_summary, dropped)
        return head + [self._summary_message(summary)] + kept

    def reset(self, messages: list[Any]) -> list[Any]:
        """Keep only the leading system/developer head — fresh conversation."""
        head: list[Any] = []
        for msg in messages:
            role = _get(msg, "role")
            if role in ("system", "developer") and not _text(msg).startswith(
                SUMMARY_PREFIX
            ):
                head.append(msg)
            else:
                break
        return head

    def _respect_tool_sequences(self, body: list[Any], cut: int) -> int:
        """Move the cut earlier so no assistant tool_calls loses its results."""
        while cut > 0:
            window = body[cut:]
            pending = set()
            for msg in window:
                for call in _get(msg, "tool_calls") or []:
                    call_id = _get(call, "id")
                    if call_id:
                        pending.add(call_id)
                if _get(msg, "role") == "tool":
                    pending.discard(_get(msg, "tool_call_id"))
            # A tool result whose call is in the dropped part → move cut back.
            orphan = any(
                _get(msg, "role") == "tool"
                and not any(
                    _get(call, "id") == _get(msg, "tool_call_id")
                    for kept_msg in window
                    for call in _get(kept_msg, "tool_calls") or []
                )
                for msg in window
            )
            if not orphan:
                return cut
            cut -= 1
        return 0

    def _summarize(self, prior: str, dropped: list[Any]) -> str:
        parts = [prior] if prior else []
        for msg in dropped:
            role = _get(msg, "role")
            text = _text(msg).strip()
            if not text:
                continue
            first_sentence = text.split(". ")[0][:160]
            if role == "user":
                parts.append(f"Người dùng: {first_sentence}")
            elif role == "assistant":
                parts.append(f"Trợ lý: {first_sentence}")
        summary = " | ".join(parts)
        if len(summary) > self.summary_max_chars:
            summary = "…" + summary[-self.summary_max_chars:]
        return summary

    def _summary_message(self, summary: str) -> dict[str, str]:
        return {"role": "system", "content": SUMMARY_PREFIX + summary}
