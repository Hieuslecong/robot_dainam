"""Authentication: backward-compatible wrappers around app.security.

This module is kept for existing import paths. New code should import
directly from app.security.
"""

from __future__ import annotations

from typing import Any

from fastapi import Request

from app.config import Settings, get_settings
from app.security.tokens import (
    TokenType,
    create_access_token,
    create_admin_token,
    create_connection_token,
    get_current_device,
    verify_access_token,
    verify_connection_token as _verify_connection_token,
)


def _settings_from_request(request: Request) -> Settings:
    return getattr(request.app.state, "settings", None) or get_settings()


def verify_connection_token(
    request: Request,
    token: str,
    *,
    session_id: str,
) -> Any:
    """Backward-compatible wrapper — extracts settings from request."""
    return _verify_connection_token(
        token,
        _settings_from_request(request),
        session_id=session_id,
        transport="webrtc",
    )


__all__ = [
    "TokenType",
    "create_access_token",
    "create_admin_token",
    "create_connection_token",
    "get_current_device",
    "verify_access_token",
    "verify_connection_token",
]
