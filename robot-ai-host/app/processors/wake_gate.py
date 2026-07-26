"""Idle/active gate for public-space deployment (spec 8.7).

In idle state no transcription reaches the LLM. Activation is explicit
(button / screen touch via RTVI ``robot.wake``); after ``idle_timeout_seconds``
without a valid user turn the gate returns to idle and asks the session to
drop transient context.
"""

from __future__ import annotations

import time
from collections.abc import Callable

from pipecat.frames.frames import Frame, InterimTranscriptionFrame, TranscriptionFrame
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor

from app.logging_utils import get_logger

logger = get_logger(__name__)


class WakeGate(FrameProcessor):
    def __init__(
        self,
        *,
        enabled: bool = False,
        idle_timeout_seconds: float = 30.0,
        on_idle: Callable[[], None] | None = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._enabled = enabled
        self._timeout = idle_timeout_seconds
        self._on_idle = on_idle
        # Disabled gate == always active (browser dev). Enabled gate boots idle.
        self._active = not enabled
        self._last_turn = time.monotonic()

    @property
    def active(self) -> bool:
        return self._active

    def set_on_idle(self, callback: Callable[[], None] | None) -> None:
        self._on_idle = callback

    def wake(self) -> None:
        self._active = True
        self._last_turn = time.monotonic()
        logger.info("wake_gate_active")

    def sleep(self) -> None:
        if not self._enabled:
            return
        self._active = False
        logger.info("wake_gate_idle")
        if self._on_idle:
            self._on_idle()

    def _admit(self) -> bool:
        """Decide whether a transcription may pass right now."""
        if self._enabled and self._active and (
            time.monotonic() - self._last_turn > self._timeout
        ):
            self.sleep()
        if not self._active:
            return False
        self._last_turn = time.monotonic()
        return True

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)

        if isinstance(frame, (TranscriptionFrame, InterimTranscriptionFrame)):
            if not self._admit():
                logger.debug(f"wake_gate dropped (idle): {frame.text!r}")
                return

        await self.push_frame(frame, direction)
