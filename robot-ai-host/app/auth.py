"""Authentication: JWT token creation and request-bound verification."""

from __future__ import annotations

import time
from typing import Annotated, Any

import jwt
from fastapi import Header, HTTPException, Request

from app.config import Settings, get_settings
from app.logging_utils import get_logger

logger = get_logger(__name__)


def create_access_token(
    device_id: str,
    settings: Settings,
    *,
    session_id: str | None = None,
    expiry_seconds: int | None = None,
) -> str:
    now = time.time()
    payload: dict[str, Any] = {
        "device_id": device_id,
        "iat": now,
        "exp": now + (expiry_seconds or settings.jwt_expiry_seconds),
    }
    if session_id:
        payload["session_id"] = session_id
    return jwt.encode(payload, settings.jwt_secret_key, algorithm="HS256")


def verify_access_token(token: str, settings: Settings) -> dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=["HS256"])
        if not payload.get("device_id"):
            raise HTTPException(status_code=401, detail="Token has no device_id")
        return payload
    except jwt.ExpiredSignatureError as exc:
        logger.warning("token_expired")
        raise HTTPException(status_code=401, detail="Token expired") from exc
    except jwt.InvalidTokenError as exc:
        logger.warning("token_invalid", error=str(exc))
        raise HTTPException(status_code=401, detail="Invalid token") from exc


def _settings_from_request(request: Request) -> Settings:
    return getattr(request.app.state, "settings", None) or get_settings()


async def get_current_device(
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    return verify_access_token(authorization[7:], _settings_from_request(request))


def verify_connection_token(
    request: Request,
    token: str,
    *,
    session_id: str,
) -> dict[str, Any]:
    payload = verify_access_token(token, _settings_from_request(request))
    token_session = payload.get("session_id")
    if token_session and token_session != session_id:
        raise HTTPException(status_code=403, detail="Connection token session mismatch")
    return payload
