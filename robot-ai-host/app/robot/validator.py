"""Robot behavior validator with allowlist enforcement."""

from __future__ import annotations

from typing import Any


from app.robot.messages import BehaviorCommand

from app.logging_utils import get_logger

logger = get_logger(__name__)

BEHAVIOR_ALLOWLIST: list[str] = [
    "nod",
    "shake_head",
    "greet",
    "happy",
    "sad",
    "confused",
    # Spec 15.4 — Expression Composer style-mapped behaviors.
    "attentive_idle",
    "gentle_nod",
    "happy_tilt",
    "slow_nod",
    "soft_nod",
    "positive_nod",
    "attentive_still",
]

def validate_behavior(command: BehaviorCommand) -> tuple[bool, str | None]:
    """Validate a behavior command against the allowlist.

    Args:
        command: The behavior command to validate.

    Returns:
        Tuple of (is_valid, reason_if_invalid).
        Intensity and duration are clamped (not rejected).
    """
    if command.name not in BEHAVIOR_ALLOWLIST:
        reason = f"Unknown behavior '{command.name}'. Allowed: {BEHAVIOR_ALLOWLIST}"
        logger.warning(
            "behavior_rejected",
            behavior=command.name,
            reason=reason,
        )
        return False, reason

    # Clamp intensity (field validator already does this, but be explicit)
    command.intensity = max(0.0, min(1.0, command.intensity))
    # Clamp duration
    command.duration_ms = max(100, min(5000, command.duration_ms))

    return True, None


def validate_raw_motor_check(data: dict[str, Any]) -> bool:
    """Check if data contains raw motor commands (which must be rejected).

    Args:
        data: The data dict to check.

    Returns:
        True if data contains raw motor commands (servo_id, angle, speed).
    """
    raw_motor_keys = {"servo_id", "angle", "speed", "motor_id", "pwm", "torque"}
    found = raw_motor_keys & set(data.keys())
    if found:
        logger.error(
            "raw_motor_command_rejected",
            keys=list(found),
            data_keys=list(data.keys()),
        )
        return True
    return False
