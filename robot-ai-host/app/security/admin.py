"""Admin authorization with scope-based access control.

Scopes:
  settings:read    — view admin settings
  settings:write   — modify admin settings (including API keys)
  knowledge:read   — list/view knowledge files
  knowledge:write  — upload/delete knowledge files
  system:restart   — restart the server
  metrics:read     — view runtime metrics
"""

from __future__ import annotations

from fastapi import Header, HTTPException, Request

from app.config import Settings, get_settings
from app.security.tokens import TokenClaims, TokenType, verify_access_token

# ── Scope definitions ───────────────────────────────────────────────

SCOPE_HIERARCHY: dict[str, list[str]] = {
    "settings:write": ["settings:read"],
    "knowledge:write": ["knowledge:read"],
    "system:restart": [],
    "metrics:read": [],
}

ADMIN_SCOPES = list(SCOPE_HIERARCHY.keys())


def _settings_from_request(request: Request) -> Settings:
    return getattr(request.app.state, "settings", None) or get_settings()


def require_admin(request: Request, authorization: str | None = Header(None)) -> TokenClaims:
    """FastAPI dependency: require admin_access token."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Admin authorization required")

    claims = verify_access_token(authorization[7:], _settings_from_request(request))

    if claims.typ != TokenType.ADMIN_ACCESS:
        raise HTTPException(status_code=403, detail="Admin access required — device tokens not accepted")

    if claims.role != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")

    return claims


def require_scope(scope: str):
    """FastAPI dependency factory: require a specific scope."""

    async def _check(request: Request, authorization: str | None = Header(None)) -> TokenClaims:
        claims = require_admin(request, authorization)

        # Check direct scope match or inherited scopes
        has_scope = scope in claims.scope
        if not has_scope:
            # Check SCOPE_HIERARCHY for inherited scopes
            for parent, children in SCOPE_HIERARCHY.items():
                if parent in claims.scope and scope in children:
                    has_scope = True
                    break

        if not has_scope:
            raise HTTPException(status_code=403, detail=f"Missing required scope: {scope}")

        return claims

    return _check
