"""Robot-specific custom messaging over the official RTVI processor."""

from __future__ import annotations

from typing import Any

from pipecat.processors.frameworks.rtvi import RTVIProcessor

from app.logging_utils import get_logger
from app.robot.messages import BehaviorCommand
from app.robot.validator import validate_behavior, validate_raw_motor_check

logger = get_logger(__name__)


async def send_robot_behavior(
    rtvi: RTVIProcessor,
    behavior: BehaviorCommand,
    *,
    session_id: str,
) -> bool:
    """Validate and send a robot behavior as an RTVI server message."""

    data = behavior.model_dump()
    if validate_raw_motor_check(data):
        return False
    valid, reason = validate_behavior(behavior)
    if not valid:
        logger.warning("robot_behavior_rejected", session_id=session_id, reason=reason)
        return False

    await rtvi.send_server_message(
        {
            "type": "robot.behavior",
            "session_id": session_id,
            "data": behavior.model_dump(),
        }
    )
    logger.info(
        "robot_behavior_sent",
        session_id=session_id,
        behavior=behavior.name,
        behavior_id=behavior.behavior_id,
    )
    return True


def client_message_parts(message: Any) -> tuple[str, dict[str, Any]]:
    """Extract custom message type/data across RTVI model representations."""

    message_type = getattr(message, "type", None)
    data = getattr(message, "data", None)
    if isinstance(message, dict):
        message_type = message.get("type", message_type)
        data = message.get("data", data)
    return str(message_type or ""), data if isinstance(data, dict) else {}
