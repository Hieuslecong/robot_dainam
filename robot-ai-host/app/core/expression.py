"""Expression Composer (spec 15) — validated expressive metadata for a turn.

The LLM/orchestrator proposes style + intensity; this module clamps, validates
against the allowlist, maps style → validated robot behavior, and guarantees
metadata can never leak into spoken text.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Spec 15.2 — style allowlist. Unknown styles fall back to the default.
STYLE_ALLOWLIST = (
    "neutral",
    "friendly",
    "cheerful",
    "calm",
    "empathetic",
    "encouraging",
    "serious",
)
DEFAULT_STYLE = "friendly"

# Spec 15.4 — style → validated robot behavior ID.
BEHAVIOR_MAP = {
    "neutral": "attentive_idle",
    "friendly": "gentle_nod",
    "cheerful": "happy_tilt",
    "calm": "slow_nod",
    "empathetic": "soft_nod",
    "encouraging": "positive_nod",
    "serious": "attentive_still",
}

# Spec 15.3 — intensity is bounded; strong emotion is never used for routine info.
MAX_INTENSITY = 0.8


class Expression(BaseModel):
    """Spec 15.1 schema. ``spoken_text`` is the ONLY field ever sent to TTS."""

    model_config = ConfigDict(extra="forbid")

    spoken_text: str
    style: str = DEFAULT_STYLE
    intensity: float = Field(default=0.4, ge=0.0)
    speaking_rate: float = Field(default=1.0, gt=0.5, lt=1.5)
    pause_profile: str = "natural"
    robot_behavior: str = ""
    screen_payload: dict | None = None

    @field_validator("style")
    @classmethod
    def _fallback_unknown_style(cls, value: str) -> str:
        return value if value in STYLE_ALLOWLIST else DEFAULT_STYLE

    @field_validator("intensity")
    @classmethod
    def _clamp_intensity(cls, value: float) -> float:
        return min(value, MAX_INTENSITY)


def compose(
    spoken_text: str,
    *,
    style: str = DEFAULT_STYLE,
    intensity: float = 0.4,
    speaking_rate: float = 1.0,
    screen_payload: dict | None = None,
) -> Expression:
    """Build a validated Expression; behavior is always derived, never LLM-raw."""
    expression = Expression(
        spoken_text=spoken_text,
        style=style,
        intensity=intensity,
        speaking_rate=max(0.51, min(1.49, speaking_rate)),
        screen_payload=screen_payload,
    )
    expression.robot_behavior = BEHAVIOR_MAP[expression.style]
    return expression
