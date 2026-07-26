"""Tests for fake robot adapter."""

import pytest

from app.robot.fake_adapter import FakeRobotAdapter, ReachyMiniAdapter, StackChanAdapter
from app.robot.messages import BehaviorCommand


@pytest.mark.asyncio
async def test_fake_adapter_execute():
    adapter = FakeRobotAdapter()
    cmd = BehaviorCommand(name="nod", emotion="friendly", intensity=0.5, duration_ms=500)
    ack = await adapter.execute_behavior(cmd)
    assert ack.behavior_id == cmd.behavior_id
    assert ack.status == "completed"
    assert ack.duration_ms > 0


@pytest.mark.asyncio
async def test_fake_adapter_capabilities():
    adapter = FakeRobotAdapter()
    caps = await adapter.get_capabilities()
    assert caps.audio_input is True
    assert caps.audio_output is True
    assert caps.camera is False
    assert caps.motion is True


@pytest.mark.asyncio
async def test_reachy_stub():
    adapter = ReachyMiniAdapter()
    cmd = BehaviorCommand(name="nod")
    with pytest.raises(NotImplementedError):
        await adapter.execute_behavior(cmd)
    with pytest.raises(NotImplementedError):
        await adapter.get_capabilities()


@pytest.mark.asyncio
async def test_stackchan_stub():
    adapter = StackChanAdapter()
    cmd = BehaviorCommand(name="nod")
    with pytest.raises(NotImplementedError):
        await adapter.execute_behavior(cmd)
    with pytest.raises(NotImplementedError):
        await adapter.get_capabilities()
