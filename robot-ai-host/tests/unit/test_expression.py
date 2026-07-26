"""Expression Composer tests (spec 15)."""

import pytest

from app.core.expression import (
    BEHAVIOR_MAP,
    DEFAULT_STYLE,
    MAX_INTENSITY,
    STYLE_ALLOWLIST,
    compose,
)
from app.robot.validator import BEHAVIOR_ALLOWLIST


def test_every_style_maps_to_validated_behavior():
    for style in STYLE_ALLOWLIST:
        expression = compose("Chào bạn.", style=style)
        assert expression.robot_behavior == BEHAVIOR_MAP[style]
        assert expression.robot_behavior in BEHAVIOR_ALLOWLIST


def test_unknown_style_falls_back_to_default():
    expression = compose("Chào bạn.", style="panicked_screaming")
    assert expression.style == DEFAULT_STYLE
    assert expression.robot_behavior == BEHAVIOR_MAP[DEFAULT_STYLE]


def test_intensity_clamped():
    expression = compose("Tin thường.", intensity=1.0)
    assert expression.intensity == MAX_INTENSITY


def test_speaking_rate_bounded():
    assert compose("A.", speaking_rate=3.0).speaking_rate < 1.5
    assert compose("A.", speaking_rate=0.1).speaking_rate > 0.5


def test_metadata_never_in_spoken_text():
    expression = compose("Mình hiểu rồi.", style="empathetic", intensity=0.4)
    dumped = expression.spoken_text
    assert "empathetic" not in dumped
    assert "soft_nod" not in dumped
