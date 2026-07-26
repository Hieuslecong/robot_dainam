"""Tests for robot behavior validator."""

import pytest

from app.robot.messages import BehaviorCommand
from app.robot.validator import (
    BEHAVIOR_ALLOWLIST,
    validate_behavior,
    validate_raw_motor_check,
)


def test_validate_valid_behaviors():
    for name in BEHAVIOR_ALLOWLIST:
        cmd = BehaviorCommand(name=name)
        valid, reason = validate_behavior(cmd)
        assert valid, f"{name} should be valid, got: {reason}"


def test_validate_unknown_behavior():
    cmd = BehaviorCommand(name="dance_crazy")
    valid, reason = validate_behavior(cmd)
    assert not valid
    assert "Unknown behavior" in reason


def test_validate_clamps_intensity():
    cmd = BehaviorCommand(name="nod", intensity=1.5)
    assert cmd.intensity == 1.0  # Clamped by validator


def test_validate_clamps_intensity_negative():
    cmd = BehaviorCommand(name="nod", intensity=-0.5)
    assert cmd.intensity == 0.0


def test_validate_clamps_duration_high():
    cmd = BehaviorCommand(name="nod", duration_ms=10000)
    assert cmd.duration_ms == 5000


def test_validate_clamps_duration_low():
    cmd = BehaviorCommand(name="nod", duration_ms=10)
    assert cmd.duration_ms == 100


def test_raw_motor_check_detects_servo():
    data = {"servo_id": 3, "angle": 180, "speed": 100}
    assert validate_raw_motor_check(data) is True


def test_raw_motor_check_detects_partial():
    data = {"name": "nod", "angle": 90}
    assert validate_raw_motor_check(data) is True


def test_raw_motor_check_passes_valid():
    data = {"name": "nod", "emotion": "friendly", "intensity": 0.5}
    assert validate_raw_motor_check(data) is False


def test_behavior_command_auto_id():
    cmd1 = BehaviorCommand(name="nod")
    cmd2 = BehaviorCommand(name="nod")
    assert cmd1.behavior_id.startswith("bhv_")
    assert cmd1.behavior_id != cmd2.behavior_id
