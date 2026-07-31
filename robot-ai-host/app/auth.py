"""Authentication: backward-compatible re-exports from app.security.

This module is kept for existing import paths. New code should import
directly from app.security.
"""

from __future__ import annotations

from app.security.tokens import (
    TokenType,
    create_access_token,
    create_admin_token,
    create_connection_token,
    get_current_device,
    verify_access_token,
    verify_connection_token,
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
