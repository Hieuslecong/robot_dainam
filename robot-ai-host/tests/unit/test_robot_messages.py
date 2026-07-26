"""Tests for robot message schemas."""

from app.robot.messages import (
    AssistantState,
    BehaviorAck,
    BehaviorCommand,
    EventEnvelope,
    RobotCapabilities,
    RobotError,
)


def test_behavior_command_defaults():
    cmd = BehaviorCommand(name="nod")
    assert cmd.name == "nod"
    assert cmd.emotion == "neutral"
    assert 0.0 <= cmd.intensity <= 1.0
    assert 100 <= cmd.duration_ms <= 5000
    assert cmd.behavior_id.startswith("bhv_")


def test_behavior_command_custom():
    cmd = BehaviorCommand(
        name="greet",
        emotion="happy",
        intensity=0.8,
        duration_ms=1200,
    )
    assert cmd.name == "greet"
    assert cmd.emotion == "happy"
    assert cmd.intensity == 0.8
    assert cmd.duration_ms == 1200


def test_behavior_ack():
    ack = BehaviorAck(behavior_id="bhv_001", status="completed", duration_ms=900)
    assert ack.behavior_id == "bhv_001"
    assert ack.status == "completed"


def test_event_envelope_auto_fields():
    env = EventEnvelope(type="robot.behavior", session_id="sess_123")
    assert env.type == "robot.behavior"
    assert env.event_id.startswith("evt_")
    assert env.timestamp_ms > 0
    assert env.session_id == "sess_123"


def test_assistant_state_values():
    assert AssistantState.IDLE == "idle"
    assert AssistantState.LISTENING == "listening"
    assert AssistantState.THINKING == "thinking"
    assert AssistantState.SPEAKING == "speaking"
    assert AssistantState.INTERRUPTED == "interrupted"
    assert AssistantState.ERROR == "error"


def test_robot_capabilities():
    caps = RobotCapabilities()
    assert caps.audio_input is True
    assert caps.camera is False


def test_robot_error():
    err = RobotError(error_code="E001", message="Test error")
    assert err.error_code == "E001"
    assert err.recoverable is True


def test_intensity_clamping():
    cmd = BehaviorCommand(name="nod", intensity=2.0)
    assert cmd.intensity == 1.0

    cmd2 = BehaviorCommand(name="nod", intensity=-1.0)
    assert cmd2.intensity == 0.0


def test_duration_clamping():
    cmd = BehaviorCommand(name="nod", duration_ms=50)
    assert cmd.duration_ms == 100

    cmd2 = BehaviorCommand(name="nod", duration_ms=9999)
    assert cmd2.duration_ms == 5000
