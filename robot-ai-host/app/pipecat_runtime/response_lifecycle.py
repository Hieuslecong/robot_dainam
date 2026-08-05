"""Response lifecycle: identity, state machine, and cancellation (PR-3).

Tracks each LLM response through its entire lifecycle:
  - response_id, turn_id, generation counter
  - state transitions: PREPARING → STREAMING → COMPLETING → COMPLETED
  - cancellation: CANCELLING → CANCELLED
  - terminal reason

Three state machines:
  ConnectionState — per-session transport state
  UserTurnState — per-utterance speech/VAD state
  ResponseState — per-LLM-response generation/delivery state
"""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum


class ResponseState(str, Enum):
    """States a single LLM response progresses through."""
    PREPARING = "preparing"        # LLM context assembled, not yet streaming
    STREAMING = "streaming"        # LLM tokens arriving
    COMPLETING = "completing"      # LLM finished, TTS still rendering
    COMPLETED = "completed"        # all audio delivered, context committed
    CANCELLING = "cancelling"      # interruption received, cleaning up
    CANCELLED = "cancelled"        # interruption complete, stale output dropped
    FAILED = "failed"              # error during generation/delivery

    @property
    def terminal(self) -> bool:
        return self in (ResponseState.COMPLETED, ResponseState.CANCELLED, ResponseState.FAILED)

    @property
    def active(self) -> bool:
        return self in (ResponseState.PREPARING, ResponseState.STREAMING, ResponseState.COMPLETING)


class DeliveryStatus(str, Enum):
    """Whether the full response reached the user's speaker."""
    COMPLETED = "completed"        # full response played
    INTERRUPTED = "interrupted"    # user barged in, partial play
    NOT_DELIVERED = "not_delivered"  # never reached audio
    FAILED = "failed"              # error prevented delivery


class UserTurnState(str, Enum):
    """State of the current user speech turn."""
    IDLE = "idle"
    SPEAKING = "speaking"
    COMMITTING = "committing"       # VAD end → final transcript pending
    COMMITTED = "committed"         # transcript finalized, LLM queued
    INTERRUPTING = "interrupting"   # user spoke while bot was responding


class ConnectionState(str, Enum):
    """Transport-level connection state."""
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTING = "disconnecting"
    DISCONNECTED = "disconnected"


@dataclass
class ResponseRuntime:
    """Tracks a single LLM response from creation to terminal state (PR-3.1)."""

    response_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    turn_id: str = ""
    generation: int = 1     # incremented on each interruption
    state: ResponseState = ResponseState.PREPARING
    delivery: DeliveryStatus = DeliveryStatus.NOT_DELIVERED
    created_at: float = field(default_factory=time.monotonic)
    terminal_reason: str = ""
    cancel_event: asyncio.Event | None = None

    # --- text tracking (PR-3.5: context consistency) ---
    text_generated: str = ""       # raw LLM output
    text_accepted: str = ""        # after ResponsePolicy filtering
    text_synthesized: str = ""     # sent to TTS
    text_played: str = ""          # acknowledged by client playback

    def begin_cancellation(self) -> None:
        """Transition to CANCELLING. Create cancel_event if needed."""
        self.state = ResponseState.CANCELLING
        if self.cancel_event is None:
            self.cancel_event = asyncio.Event()

    def complete_cancellation(self, reason: str = "user_interrupted") -> None:
        """Transition to CANCELLED. Signal the cancel event."""
        self.state = ResponseState.CANCELLED
        self.delivery = DeliveryStatus.INTERRUPTED
        self.terminal_reason = reason
        if self.cancel_event:
            self.cancel_event.set()

    def mark_generated(self, text: str) -> None:
        """Record LLM output as it streams."""
        self.text_generated = text

    def mark_accepted(self, text: str) -> None:
        """Record text after ResponsePolicy filtering."""
        self.text_accepted = text

    def mark_synthesized(self, text: str) -> None:
        """Record text sent to TTS for synthesis."""
        self.text_synthesized = text

    def mark_completed(self, delivery: DeliveryStatus = DeliveryStatus.COMPLETED) -> None:
        """Transition to terminal COMPLETED state."""
        self.state = ResponseState.COMPLETED
        self.delivery = delivery
        self.terminal_reason = delivery.value
