"""One-time connection tickets for WebRTC/WebSocket.

Tickets are:
  - opaque (random hex string)
  - single-use (consumed on first use)
  - short-lived (TTL 30 seconds)
  - bound to device_id, session_id, and transport type
"""

from __future__ import annotations

import secrets
import time
from dataclasses import dataclass, field


@dataclass
class ConnectionTicket:
    ticket: str
    device_id: str
    session_id: str
    transport: str
    origin: str | None = None
    created_at: float = field(default_factory=time.time)
    ttl_seconds: int = 30
    used: bool = False

    @property
    def expired(self) -> bool:
        return time.time() > self.created_at + self.ttl_seconds

    @property
    def valid(self) -> bool:
        return not self.used and not self.expired


class TicketStore:
    """In-memory ticket store. Single-use, auto-expire."""

    def __init__(self) -> None:
        self._tickets: dict[str, ConnectionTicket] = {}

    def issue(
        self,
        device_id: str,
        session_id: str,
        *,
        transport: str = "webrtc",
        origin: str | None = None,
        ttl_seconds: int = 30,
    ) -> ConnectionTicket:
        """Issue a new one-time ticket."""
        ticket_str = secrets.token_hex(32)
        ticket = ConnectionTicket(
            ticket=ticket_str,
            device_id=device_id,
            session_id=session_id,
            transport=transport,
            origin=origin,
            ttl_seconds=ttl_seconds,
        )
        self._tickets[ticket_str] = ticket
        # Clean expired tickets on each issue
        self._prune()
        return ticket

    def validate_and_consume(
        self,
        ticket_str: str,
        *,
        session_id: str,
        transport: str,
        origin: str | None = None,
    ) -> ConnectionTicket | None:
        """Validate and consume a ticket. Returns None if invalid."""
        ticket = self._tickets.get(ticket_str)
        if ticket is None:
            return None
        if ticket.used or ticket.expired:
            return None
        if ticket.session_id != session_id:
            return None
        if ticket.transport != transport:
            return None
        if ticket.origin and origin and ticket.origin != origin:
            return None
        ticket.used = True
        return ticket

    def _prune(self) -> None:
        """Remove expired tickets."""
        now = time.time()
        expired = [k for k, t in self._tickets.items() if t.expired or now > t.created_at + t.ttl_seconds + 60]
        for k in expired:
            del self._tickets[k]
