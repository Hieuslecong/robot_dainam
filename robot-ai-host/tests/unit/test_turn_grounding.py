"""Grounding + safety injection tests (design 2026-07-26) with a real store."""

import json

from app.core.knowledge import KnowledgeStore
from app.processors.turn_grounding import (
    GROUNDING_PREFIX,
    SAFETY_PREFIX,
    TurnGroundingProcessor,
)


class FakeContext:
    def __init__(self, messages):
        self.messages = messages

    def set_messages(self, messages):
        self.messages = list(messages)


def _processor(tmp_path, messages):
    ctx = FakeContext(messages)
    proc = TurnGroundingProcessor.__new__(TurnGroundingProcessor)
    proc._context = ctx
    proc._store = KnowledgeStore()
    proc._alerts_path = tmp_path / "alerts.jsonl"
    return proc, ctx


def _system_notes(ctx, prefix):
    return [
        m for m in ctx.messages
        if m.get("role") == "system" and m.get("content", "").startswith(prefix)
    ]


def test_school_question_with_data_injects_sourced_evidence(tmp_path):
    proc, ctx = _processor(tmp_path, [{"role": "user", "content": "Thư viện mở cửa mấy giờ?"}])
    proc._ground_turn()
    notes = _system_notes(ctx, GROUNDING_PREFIX)
    assert len(notes) == 1
    assert "Nguồn:" in notes[0]["content"]
    assert "thư viện" in notes[0]["content"].lower()


def test_school_question_without_data_injects_refusal_note(tmp_path):
    proc, ctx = _processor(
        tmp_path, [{"role": "user", "content": "Thủ tục chuyển ngành cần giấy tờ gì?"}]
    )
    proc._ground_turn()
    notes = _system_notes(ctx, GROUNDING_PREFIX)
    assert len(notes) == 1
    assert "KHÔNG có tài liệu" in notes[0]["content"]


def test_small_talk_injects_nothing(tmp_path):
    proc, ctx = _processor(tmp_path, [{"role": "user", "content": "Hôm nay vui ghê!"}])
    proc._ground_turn()
    assert _system_notes(ctx, GROUNDING_PREFIX) == []
    assert _system_notes(ctx, SAFETY_PREFIX) == []


def test_previous_notes_are_replaced_not_accumulated(tmp_path):
    proc, ctx = _processor(tmp_path, [{"role": "user", "content": "Thư viện ở đâu?"}])
    proc._ground_turn()
    ctx.messages.append({"role": "assistant", "content": "Tầng 3 tòa A nè."})
    ctx.messages.append({"role": "user", "content": "Hạn nộp học phí khi nào?"})
    proc._ground_turn()
    notes = _system_notes(ctx, GROUNDING_PREFIX)
    assert len(notes) == 1  # old note removed, only current turn's note remains
    assert "học phí" in notes[0]["content"].lower()


def test_safety_keyword_injects_note_and_writes_alert(tmp_path):
    proc, ctx = _processor(
        tmp_path, [{"role": "user", "content": "Mình bị bắt nạt ở lớp, sợ lắm"}]
    )
    proc._ground_turn()
    assert len(_system_notes(ctx, SAFETY_PREFIX)) == 1
    lines = (tmp_path / "alerts.jsonl").read_text(encoding="utf-8").strip().splitlines()
    record = json.loads(lines[0])
    assert record["categories"] == ["bao_luc"]
    assert "bắt nạt" in record["excerpt"]


def test_safety_note_not_triggered_by_normal_text(tmp_path):
    proc, ctx = _processor(
        tmp_path, [{"role": "user", "content": "Kể mình nghe một câu chuyện vui đi"}]
    )
    proc._ground_turn()
    assert _system_notes(ctx, SAFETY_PREFIX) == []
    assert not (tmp_path / "alerts.jsonl").exists()
