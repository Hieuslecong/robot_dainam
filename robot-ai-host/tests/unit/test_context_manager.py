"""Context bounding tests — spec 13.1–13.2."""

from app.core.context_manager import SUMMARY_PREFIX, ContextManager


def _turns(n: int) -> list[dict]:
    msgs = []
    for i in range(n):
        msgs.append({"role": "user", "content": f"Câu hỏi số {i}"})
        msgs.append({"role": "assistant", "content": f"Trả lời số {i}. Chi tiết thêm."})
    return msgs


SYSTEM = {"role": "system", "content": "Bạn là trợ lý."}


def test_under_limit_untouched():
    manager = ContextManager(max_recent_turns=8)
    messages = [SYSTEM] + _turns(3)
    assert manager.compact(messages) == messages


def test_over_limit_keeps_recent_and_summarizes():
    manager = ContextManager(max_recent_turns=4)
    messages = [SYSTEM] + _turns(10)
    result = manager.compact(messages)

    assert result[0] == SYSTEM
    assert result[1]["content"].startswith(SUMMARY_PREFIX)
    user_msgs = [m for m in result if m["role"] == "user"]
    assert len(user_msgs) == 4
    assert user_msgs[0]["content"] == "Câu hỏi số 6"
    # Dropped content is represented in the summary.
    assert "Câu hỏi số 0" in result[1]["content"]


def test_summary_rolls_forward():
    manager = ContextManager(max_recent_turns=2)
    once = manager.compact([SYSTEM] + _turns(5))
    twice = manager.compact(once + _turns(3))
    summaries = [m for m in twice if m["content"].startswith(SUMMARY_PREFIX)]
    assert len(summaries) == 1  # never two summary messages
    assert "Câu hỏi số 0" in summaries[0]["content"]


def test_summary_bounded():
    manager = ContextManager(max_recent_turns=1, summary_max_chars=200)
    result = manager.compact([SYSTEM] + _turns(50))
    summary = next(m for m in result if m["content"].startswith(SUMMARY_PREFIX))
    assert len(summary["content"]) <= 200 + len(SUMMARY_PREFIX) + 1


def test_unfinished_tool_sequence_not_cut():
    manager = ContextManager(max_recent_turns=2)
    messages = [SYSTEM] + _turns(4)
    # Turn 5: assistant issues a tool call answered right after — the pair sits
    # exactly at the would-be cut boundary.
    messages += [
        {"role": "user", "content": "Đặt lịch giúp mình"},
        {"role": "assistant", "content": "", "tool_calls": [{"id": "call_1"}]},
        {"role": "tool", "tool_call_id": "call_1", "content": "ok"},
        {"role": "assistant", "content": "Xong rồi."},
        {"role": "user", "content": "Cảm ơn"},
        {"role": "assistant", "content": "Không có gì."},
    ]
    result = manager.compact(messages)
    kept_tool_results = [m for m in result if m.get("role") == "tool"]
    for tool_msg in kept_tool_results:
        call_ids = {
            call["id"]
            for m in result
            for call in (m.get("tool_calls") or [])
        }
        assert tool_msg["tool_call_id"] in call_ids


def test_reset_keeps_only_system_head():
    manager = ContextManager()
    messages = [SYSTEM] + _turns(3)
    assert manager.reset(messages) == [SYSTEM]


def test_reset_drops_summary():
    manager = ContextManager(max_recent_turns=1)
    compacted = manager.compact([SYSTEM] + _turns(5))
    assert manager.reset(compacted) == [SYSTEM]
