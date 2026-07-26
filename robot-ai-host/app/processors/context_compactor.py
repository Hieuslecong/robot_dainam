"""Frame processor that bounds LLMContext growth before each LLM run."""

from __future__ import annotations

from pipecat.frames.frames import Frame
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor

from app.core.context_manager import ContextManager
from app.logging_utils import get_logger

logger = get_logger(__name__)


class ContextCompactor(FrameProcessor):
    """Compacts the shared LLMContext whenever a context frame passes by.

    Sits between the user aggregator and the LLM so every request sees a
    bounded message list (system head + rolling summary + last N turns).
    """

    def __init__(self, context: LLMContext, manager: ContextManager, **kwargs) -> None:
        super().__init__(**kwargs)
        self._context = context
        self._manager = manager

    async def process_frame(self, frame: Frame, direction: FrameDirection) -> None:
        await super().process_frame(frame, direction)
        if type(frame).__name__ == "LLMContextFrame":
            before = len(self._context.messages)
            compacted = self._manager.compact(list(self._context.messages))
            if len(compacted) < before:
                self._context.set_messages(compacted)
                logger.info(
                    "context_compacted", before=before, after=len(compacted)
                )
        await self.push_frame(frame, direction)
