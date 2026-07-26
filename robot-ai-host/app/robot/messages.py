"""Robot behavior messaging protocol schemas."""

from __future__ import annotations

import time
import uuid
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class AssistantState(str, Enum):
    """Bot assistant states as defined by RTVI/Pipecat."""

    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    SPEAKING = "speaking"
    INTERRUPTED = "interrupted"
    ERROR = "error"


class BehaviorCommand(BaseModel):
    """Command to trigger a robot behavior.

    Sent from server to robot via data channel.
    """

    behavior_id: str = Field(default_factory=lambda: f"bhv_{uuid.uuid4().hex[:8]}")
    name: str
    emotion: str = "neutral"
    intensity: float = Field(default=0.5, ge=0.0, le=1.0)
    duration_ms: int = Field(default=500, ge=100, le=5000)

    @field_validator("intensity", mode="before")
    @classmethod
    def clamp_intensity(cls, v: float) -> float:
        """Clamp intensity to [0, 1]."""
        if isinstance(v, (int, float)):
            return max(0.0, min(1.0, float(v)))
        return v

    @field_validator("duration_ms", mode="before")
    @classmethod
    def clamp_duration(cls, v: int) -> int:
        """Clamp duration_ms to [100, 5000]."""
        if isinstance(v, (int, float)):
            return max(100, min(5000, int(v)))
        return v


class BehaviorAck(BaseModel):
    """Acknowledgment of a behavior command from robot.

    Sent from robot to server via data channel.
    """

    behavior_id: str
    status: Literal["completed", "failed", "rejected"] = "completed"
    duration_ms: int = 0


class RobotCapabilities(BaseModel):
    """Robot hardware capabilities."""

    audio_input: bool = True
    audio_output: bool = True
    camera: bool = False
    motion: bool = True
    display: bool = True


class RobotError(BaseModel):
    """Robot error report."""

    error_code: str
    message: str
    recoverable: bool = True


class EventEnvelope(BaseModel):
    """Envelope for all data channel messages."""

    type: str
    event_id: str = Field(default_factory=lambda: f"evt_{uuid.uuid4().hex[:8]}")
    session_id: str = ""
    timestamp_ms: int = Field(default_factory=lambda: int(time.time() * 1000))
    data: dict[str, Any] = Field(default_factory=dict)
