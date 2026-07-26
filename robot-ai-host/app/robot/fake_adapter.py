"""Robot adapters: fake (desktop emulator) and stubs for real robots."""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod


from app.robot.messages import BehaviorAck, BehaviorCommand, RobotCapabilities

from app.logging_utils import get_logger

logger = get_logger(__name__)


class BaseRobotAdapter(ABC):
    """Abstract base for robot behavior adapters."""

    @abstractmethod
    async def execute_behavior(self, command: BehaviorCommand) -> BehaviorAck:
        """Execute a behavior command on the robot.

        Args:
            command: The validated behavior command.

        Returns:
            Acknowledgment of the behavior execution.
        """
        ...

    @abstractmethod
    async def get_capabilities(self) -> RobotCapabilities:
        """Return the robot's hardware capabilities."""
        ...


class FakeRobotAdapter(BaseRobotAdapter):
    """Desktop emulator adapter that logs behaviors and returns ACKs."""

    async def execute_behavior(self, command: BehaviorCommand) -> BehaviorAck:
        """Simulate behavior execution with abbreviated delay."""
        logger.info(
            "fake_behavior_executing",
            behavior=command.name,
            emotion=command.emotion,
            intensity=command.intensity,
            duration_ms=command.duration_ms,
        )
        # Simulate ~10% of actual duration для test speed
        simulated_ms = max(10, command.duration_ms // 10)
        await asyncio.sleep(simulated_ms / 1000.0)

        ack = BehaviorAck(
            behavior_id=command.behavior_id,
            status="completed",
            duration_ms=simulated_ms,
        )
        logger.info(
            "fake_behavior_completed",
            behavior_id=command.behavior_id,
            status=ack.status,
        )
        return ack

    async def get_capabilities(self) -> RobotCapabilities:
        """Desktop emulator capabilities."""
        return RobotCapabilities(
            audio_input=True,
            audio_output=True,
            camera=False,
            motion=True,
            display=True,
        )


class ReachyMiniAdapter(BaseRobotAdapter):
    """Stub adapter for Reachy Mini robot. Not implemented."""

    async def execute_behavior(self, command: BehaviorCommand) -> BehaviorAck:
        raise NotImplementedError("ReachyMiniAdapter is a stub - not implemented")

    async def get_capabilities(self) -> RobotCapabilities:
        raise NotImplementedError("ReachyMiniAdapter is a stub - not implemented")


class StackChanAdapter(BaseRobotAdapter):
    """Stub adapter for StackChan robot. Not implemented."""

    async def execute_behavior(self, command: BehaviorCommand) -> BehaviorAck:
        raise NotImplementedError("StackChanAdapter is a stub - not implemented")

    async def get_capabilities(self) -> RobotCapabilities:
        raise NotImplementedError("StackChanAdapter is a stub - not implemented")
