"""Router tests (spec 9.8, 10.1–10.4)."""

import asyncio
import json

import pytest

from app.core.routing import Intent, Risk, Router, heuristic_route

# Representative ordinary-turn set: ≥60% must bypass without an LLM call.
ORDINARY_TURNS = [
    "xin chào",
    "chào bạn",
    "hello",
    "cảm ơn nhé",
    "tạm biệt",
    "bạn là ai",
    "bạn tên gì",
    "bạn khỏe không",
    "dừng lại",
    "thôi",
    "ừ",
    "hôm nay là thứ mấy",
    "gật đầu đi",
    "hạn đăng ký học phần là khi nào",   # needs LLM
    "tạo nhắc nhở nộp học phí ngày mai",  # needs LLM
    "phòng đào tạo ở đâu vậy",            # needs LLM
]


def test_bypass_rate_at_least_60_percent():
    bypassed = sum(1 for t in ORDINARY_TURNS if heuristic_route(t) is not None)
    assert bypassed / len(ORDINARY_TURNS) >= 0.6


def test_greeting_and_stop_bypass():
    assert heuristic_route("xin chào").intent == Intent.SMALL_TALK
    assert heuristic_route("dừng lại").intent == Intent.SMALL_TALK
    assert heuristic_route("gật đầu đi").intent == Intent.ROBOT_BEHAVIOR_REQUEST


def test_task_utterance_not_bypassed():
    assert heuristic_route("tạo nhắc nhở nộp học phí ngày mai trước 9 giờ") is None


def test_llm_router_parses_structured_output():
    async def fake_llm(system, user):
        return json.dumps({"intent": "school_information", "risk": "read_only", "confidence": 0.9})

    router = Router(llm_call=fake_llm)
    decision = asyncio.run(router.route("hạn đăng ký học phần là khi nào"))
    assert decision.intent == Intent.SCHOOL_INFORMATION
    assert decision.source == "llm"
    assert decision.path == "direct"


def test_llm_router_timeout_falls_back_without_blocking():
    async def slow_llm(system, user):
        await asyncio.sleep(2.0)
        return "{}"

    router = Router(llm_call=slow_llm)
    decision = asyncio.run(router.route("một yêu cầu phức tạp cần phân loại kỹ"))
    assert decision.intent == Intent.UNCLEAR
    assert decision.source == "fallback"
    assert decision.latency_ms < 1000  # 300ms budget + overhead, never 2s


def test_bad_json_falls_back():
    async def bad_llm(system, user):
        return "not json at all"

    router = Router(llm_call=bad_llm)
    decision = asyncio.run(router.route("yêu cầu khó phân loại nào đó dài dòng"))
    assert decision.intent == Intent.UNCLEAR


def test_action_intent_routes_to_flow():
    async def fake_llm(system, user):
        return json.dumps({"intent": "action_request", "risk": "confirmed_write", "confidence": 0.8})

    router = Router(llm_call=fake_llm)
    decision = asyncio.run(router.route("gửi email cho phòng đào tạo giúp mình"))
    assert decision.path == "flow"


def test_bypass_rate_metric_tracked():
    router = Router()
    asyncio.run(router.route("xin chào"))
    asyncio.run(router.route("làm sao để đăng ký học phần trực tuyến"))
    assert router.total == 2
    assert router.bypassed == 1
    assert router.bypass_rate == 0.5
