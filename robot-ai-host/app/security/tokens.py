"""JWT token creation and verification with token type separation.

Token types:
  device_access      — device registration / API access
  admin_access       — admin dashboard / settings / knowledge
  webrtc_connection  — WebRTC offer/answer
  websocket_connection — WebSocket handshake

Each token MUST carry: sub, typ, scope, iss, aud, jti, iat, exp.
Access tokens MUST NOT be used as connection tokens (different typ).
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Annotated, Any

import jwt
from fastapi import Header, HTTPException, Request

from app.config import Settings, get_settings
from app.logging_utils import get_logger

logger = get_logger(__name__)

TOKEN_ISSUER = "robot-ai-host"
TOKEN_AUDIENCE = "robot-ai-api"


class TokenType(str, Enum):
    DEVICE_ACCESS = "device_access"
    ADMIN_ACCESS = "admin_access"
    WEBRTC_CONNECTION = "webrtc_connection"
    WEBSOCKET_CONNECTION = "websocket_connection"


@dataclass
class TokenClaims:
    sub: str  # device_id or admin principal
    typ: TokenType
    role: str
    scope: list[str]
    iss: str
    aud: str
    jti: str
    iat: int
    exp: int
    session_id: str | None = None

    # Backward-compatible dict-like access for existing endpoint code
    def __getitem__(self, key: str) -> Any:
        mapping = {
            "device_id": self.sub,
            "sub": self.sub,
            "typ": self.typ.value,
            "token_type": self.typ.value,
            "role": self.role,
            "scope": self.scope,
            "session_id": self.session_id,
        }
        if key in mapping:
            return mapping[key]
        raise KeyError(key)

    def get(self, key: str, default: Any = None) -> Any:
        try:
            return self[key]
        except KeyError:
            return default

    def __contains__(self, key: str) -> bool:
        try:
            self[key]
            return True
        except KeyError:
            return False


def _build_payload(
    *,
    sub: str,
    typ: TokenType,
    role: str,
    scope: list[str],
    session_id: str | None = None,
    expiry_seconds: int | None = None,
    settings: Settings | None = None,
) -> dict[str, Any]:
    settings = settings or get_settings()
    now = int(time.time())
    return {
        "sub": sub,
        "typ": typ.value,
        "role": role,
        "scope": scope,
        "iss": TOKEN_ISSUER,
        "aud": TOKEN_AUDIENCE,
        "jti": uuid.uuid4().hex,
        "iat": now,
        "exp": now + (expiry_seconds or settings.jwt_expiry_seconds),
        **(dict(session_id=session_id) if session_id else {}),
    }


def create_access_token(
    device_id: str,
    settings: Settings,
    *,
    session_id: str | None = None,
    scopes: list[str] | None = None,
    expiry_seconds: int | None = None,
) -> str:
    """Create a device_access token."""
    payload = _build_payload(
        sub=device_id,
        typ=TokenType.DEVICE_ACCESS,
        role="robot",
        scope=scopes or [],
        session_id=session_id,
        expiry_seconds=expiry_seconds,
        settings=settings,
    )
    return jwt.encode(payload, settings.jwt_secret_key, algorithm="HS256")


def create_admin_token(
    admin_id: str,
    settings: Settings,
    *,
    scopes: list[str] | None = None,
    expiry_seconds: int | None = None,
) -> str:
    """Create an admin_access token with explicit scopes."""
    payload = _build_payload(
        sub=admin_id,
        typ=TokenType.ADMIN_ACCESS,
        role="admin",
        scope=scopes or ["settings:read", "settings:write", "knowledge:read", "knowledge:write", "system:restart"],
        expiry_seconds=expiry_seconds,
        settings=settings,
    )
    return jwt.encode(payload, settings.jwt_secret_key, algorithm="HS256")


def create_connection_token(
    device_id: str,
    settings: Settings,
    *,
    session_id: str,
    transport: str = "webrtc",
    expiry_seconds: int | None = None,
) -> str:
    """Create a WebRTC or WebSocket connection token (short-lived)."""
    typ = TokenType.WEBRTC_CONNECTION if transport == "webrtc" else TokenType.WEBSOCKET_CONNECTION
    exp = expiry_seconds or 60  # connection tokens are short-lived
    payload = _build_payload(
        sub=device_id,
        typ=typ,
        role="robot",
        scope=[],
        session_id=session_id,
        expiry_seconds=exp,
        settings=settings,
    )
    return jwt.encode(payload, settings.jwt_secret_key, algorithm="HS256")


def _decode_token(token: str, settings: Settings) -> dict[str, Any]:
    try:
        return jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=["HS256"],
            options={
                "require": ["sub", "typ", "scope", "iss", "aud", "jti", "iat", "exp"],
                "verify_iss": True,
                "verify_aud": True,
            },
            issuer=TOKEN_ISSUER,
            audience=TOKEN_AUDIENCE,
        )
    except jwt.ExpiredSignatureError as exc:
        logger.warning("token_expired")
        raise HTTPException(status_code=401, detail="Token expired") from exc
    except jwt.InvalidIssuerError as exc:
        logger.warning("token_invalid_issuer")
        raise HTTPException(status_code=401, detail="Invalid token issuer") from exc
    except jwt.InvalidAudienceError as exc:
        logger.warning("token_invalid_audience")
        raise HTTPException(status_code=401, detail="Invalid token audience") from exc
    except jwt.InvalidTokenError as exc:
        logger.warning("token_invalid", error=str(exc))
        raise HTTPException(status_code=401, detail="Invalid token") from exc


def verify_access_token(token: str, settings: Settings) -> TokenClaims:
    """Verify a device_access or admin_access token. Returns structured claims."""
    payload = _decode_token(token, settings)
    typ = payload.get("typ")

    if typ not in (TokenType.DEVICE_ACCESS.value, TokenType.ADMIN_ACCESS.value):
        raise HTTPException(status_code=401, detail=f"Token type '{typ}' is not an access token")

    return TokenClaims(
        sub=payload["sub"],
        typ=TokenType(typ),
        role=payload.get("role", "unknown"),
        scope=payload.get("scope", []),
        iss=payload["iss"],
        aud=payload["aud"],
        jti=payload["jti"],
        iat=payload["iat"],
        exp=payload["exp"],
        session_id=payload.get("session_id"),
    )


def verify_connection_token(
    token: str,
    settings: Settings,
    *,
    session_id: str,
    transport: str = "webrtc",
) -> TokenClaims:
    """Verify a connection token. MUST match session_id and transport."""
    payload = _decode_token(token, settings)
    typ = payload.get("typ")
    expected_typ = TokenType.WEBRTC_CONNECTION if transport == "webrtc" else TokenType.WEBSOCKET_CONNECTION

    if typ != expected_typ.value:
        raise HTTPException(
            status_code=401,
            detail=f"Token type '{typ}' cannot be used for {transport} connection",
        )

    token_session = payload.get("session_id")
    if token_session != session_id:
        raise HTTPException(status_code=403, detail="Connection token session mismatch")

    return TokenClaims(
        sub=payload["sub"],
        typ=TokenType(typ),
        role=payload.get("role", "unknown"),
        scope=[],
        iss=payload["iss"],
        aud=payload["aud"],
        jti=payload["jti"],
        iat=payload["iat"],
        exp=payload["exp"],
        session_id=token_session,
    )


# ── FastAPI dependencies ────────────────────────────────────────────

def _settings_from_request(request: Request) -> Settings:
    return getattr(request.app.state, "settings", None) or get_settings()


async def get_current_device(
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
) -> TokenClaims:
    """FastAPI dependency: extract and verify device_access token from Authorization header."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    claims = verify_access_token(authorization[7:], _settings_from_request(request))
    if claims.typ != TokenType.DEVICE_ACCESS:
        raise HTTPException(status_code=403, detail="Device token required")
    return claims
