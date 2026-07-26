"""Intent/complexity/risk router (spec 9.8, 10.1–10.4).

Hard rules:
1. Heuristic bypass runs BEFORE any LLM call (target ≥60% of ordinary turns).
2. LLM router budget P50 ≤300 ms; timeout ⇒ fallback to conversation executor
   with intent ``unclear`` — the turn is never blocked.
3. ``router_latency`` and ``router_bypass_rate`` are reported separately.
"""

from __future__ import annotations

import asyncio
import json
import re
import time
from enum import Enum

from pydantic import BaseModel, ConfigDict

from app.logging_utils import get_logger

logger = get_logger(__name__)

ROUTER_TIMEOUT_S = 0.3  # spec 9.8 rule 1


class Intent(str, Enum):
    SMALL_TALK = "small_talk"
    SCHOOL_INFORMATION = "school_information"
    KNOWLEDGE_LOOKUP = "knowledge_lookup"
    PERSONAL_PRODUCTIVITY = "personal_productivity"
    ACTION_REQUEST = "action_request"
    SENSITIVE_ACTION = "sensitive_action"
    ROBOT_BEHAVIOR_REQUEST = "robot_behavior_request"
    UNCLEAR = "unclear"
    UNSUPPORTED = "unsupported"


class Risk(str, Enum):
    READ_ONLY = "read_only"
    LOW_RISK_WRITE = "low_risk_write"
    CONFIRMED_WRITE = "confirmed_write"
    SENSITIVE = "sensitive"
    UNSUPPORTED = "unsupported"


class RouteDecision(BaseModel):
    model_config = ConfigDict(extra="ignore")

    intent: Intent
    risk: Risk = Risk.READ_ONLY
    confidence: float = 1.0
    path: str = "direct"  # "direct" | "flow" (spec 10.3/10.4)
    source: str = "bypass"  # "bypass" | "llm" | "fallback"
    latency_ms: float = 0.0


# --- Heuristic bypass (no LLM) -------------------------------------------------

_GREETING = re.compile(
    r"^(xin ch[àa]o|ch[àa]o|hello|hi|al[ôo])\b|ch[àa]o (bạn|em|anh|chị)", re.IGNORECASE
)
_FAREWELL_THANKS = re.compile(
    r"(tạm biệt|hẹn gặp lại|c[ảa]m ơn|cám ơn|thank)", re.IGNORECASE
)
_STOP = re.compile(r"^(dừng( lại)?|thôi|stop|im( lặng)?|đừng nói nữa)\b", re.IGNORECASE)
_SMALL_TALK = re.compile(
    r"(bạn là ai|bạn tên (là )?gì|khỏe không|kh[oỏ]e ch[ưứ]|mấy giờ|hôm nay (là )?(thứ|ngày))",
    re.IGNORECASE,
)
_ROBOT_BEHAVIOR = re.compile(r"(gật đầu|lắc đầu|vẫy tay|cười lên|nhảy)", re.IGNORECASE)


def heuristic_route(text: str) -> RouteDecision | None:
    """Rule/regex classification for common turns. None = needs LLM router."""
    normalized = " ".join(text.strip().split())
    if not normalized:
        return RouteDecision(intent=Intent.UNCLEAR, source="bypass")
    if _STOP.search(normalized):
        return RouteDecision(intent=Intent.SMALL_TALK, source="bypass")
    if _GREETING.search(normalized) or _FAREWELL_THANKS.search(normalized):
        return RouteDecision(intent=Intent.SMALL_TALK, source="bypass")
    if _SMALL_TALK.search(normalized):
        return RouteDecision(intent=Intent.SMALL_TALK, source="bypass")
    if _ROBOT_BEHAVIOR.search(normalized):
        return RouteDecision(intent=Intent.ROBOT_BEHAVIOR_REQUEST, source="bypass")
    if len(normalized.split()) <= 2:
        # Too short to carry a task; treat as small talk, don't wake the LLM.
        return RouteDecision(intent=Intent.SMALL_TALK, confidence=0.6, source="bypass")
    return None


# --- LLM router ---------------------------------------------------------------

_ROUTER_SYSTEM = (
    "Bạn là bộ phân loại intent cho trợ lý tiếng Việt của một trường đại học. "
    "Trả về DUY NHẤT một JSON object: "
    '{"intent": "<một trong: small_talk|school_information|knowledge_lookup|'
    "personal_productivity|action_request|sensitive_action|robot_behavior_request|"
    'unclear|unsupported>", "risk": "<read_only|low_risk_write|confirmed_write|'
    'sensitive|unsupported>", "confidence": <0..1>}'
)


class Router:
    """Heuristic-first router with a strictly budgeted LLM fallback."""

    def __init__(self, *, llm_call=None, tracker=None, session_id: str = "") -> None:
        # llm_call: async (system, user, timeout_s) -> str (JSON). Injected so
        # tests use fakes; production wires an OpenAI-compatible one-shot call.
        self._llm_call = llm_call
        self._tracker = tracker
        self._session_id = session_id
        self.total = 0
        self.bypassed = 0

    @property
    def bypass_rate(self) -> float:
        return self.bypassed / self.total if self.total else 0.0

    async def route(self, text: str) -> RouteDecision:
        self.total += 1
        started = time.monotonic()

        decision = heuristic_route(text)
        if decision is not None:
            self.bypassed += 1
            decision.latency_ms = (time.monotonic() - started) * 1000
            await self._record(decision)
            return decision

        if self._llm_call is None:
            decision = RouteDecision(
                intent=Intent.UNCLEAR, confidence=0.0, source="fallback"
            )
        else:
            try:
                raw = await asyncio.wait_for(
                    self._llm_call(_ROUTER_SYSTEM, text), timeout=ROUTER_TIMEOUT_S
                )
                payload = json.loads(raw)
                decision = RouteDecision(
                    intent=Intent(payload["intent"]),
                    risk=Risk(payload.get("risk", "read_only")),
                    confidence=float(payload.get("confidence", 0.5)),
                    source="llm",
                )
            except Exception as exc:  # timeout, bad JSON, bad enum — never block
                logger.warning("router_llm_fallback", reason=type(exc).__name__)
                decision = RouteDecision(
                    intent=Intent.UNCLEAR, confidence=0.0, source="fallback"
                )

        # Spec 10.4: structured flow for writes/sensitive/multi-step work.
        if decision.risk in (Risk.CONFIRMED_WRITE, Risk.SENSITIVE) or decision.intent in (
            Intent.ACTION_REQUEST,
            Intent.SENSITIVE_ACTION,
        ):
            decision.path = "flow"

        decision.latency_ms = (time.monotonic() - started) * 1000
        await self._record(decision)
        return decision

    async def _record(self, decision: RouteDecision) -> None:
        if self._tracker is None:
            return
        await self._tracker.record(
            "router_latency",
            decision.latency_ms,
            session_id=self._session_id,
            source=decision.source,
        )
        await self._tracker.record(
            "router_bypass_rate",
            self.bypass_rate * 100,
            session_id=self._session_id,
            source="router",
        )


def make_openai_router_call(settings):
    """One-shot, non-streaming, minimal-token router call (spec 9.8 rule 3)."""
    from openai import AsyncOpenAI

    client = AsyncOpenAI(
        api_key=settings.resolved_llm_api_key or "unused",
        base_url=settings.resolved_llm_base_url,
        default_headers=settings.llm_default_headers or None,
    )
    model = (getattr(settings, "llm_router_model", "") or settings.resolved_llm_model)

    async def call(system: str, user: str) -> str:
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            max_tokens=60,
            temperature=0.0,
            stream=False,
        )
        return response.choices[0].message.content or "{}"

    return call
