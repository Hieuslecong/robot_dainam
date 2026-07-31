"""Tests for authentication module."""

import time

import jwt
import pytest

from app.auth import create_access_token, verify_access_token
from app.config import Settings


@pytest.fixture
def settings():
    return Settings(
        jwt_secret_key="test-secret-key-32-bytes-minimum",
        jwt_expiry_seconds=3600,
        provisioning_secret="test",
    )


def test_create_access_token_returns_string(settings):
    token = create_access_token("device-001", settings)
    assert isinstance(token, str)
    assert len(token) > 10


def test_create_access_token_contains_device_id(settings):
    token = create_access_token("device-001", settings)
    claims = verify_access_token(token, settings)
    # New token format uses "sub" instead of "device_id" (JWT standard)
    assert claims["device_id"] == "device-001"
    assert claims.sub == "device-001"


def test_verify_access_token_valid(settings):
    token = create_access_token("device-001", settings)
    payload = verify_access_token(token, settings)
    assert payload["device_id"] == "device-001"


def test_verify_access_token_expired(settings):
    from fastapi import HTTPException

    # Create a token that's already expired (new format uses "sub")
    payload = {
        "sub": "device-001",
        "typ": "device_access",
        "scope": [],
        "iss": "robot-ai-host",
        "aud": "robot-ai-api",
        "jti": "test-jti",
        "iat": int(time.time()) - 7200,
        "exp": int(time.time()) - 3600,
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm="HS256")

    with pytest.raises(HTTPException) as exc_info:
        verify_access_token(token, settings)
    assert exc_info.value.status_code == 401


def test_verify_access_token_invalid_signature(settings):
    from fastapi import HTTPException

    token = create_access_token("device-001", settings)

    wrong_settings = Settings(
        jwt_secret_key="wrong-key-32-bytes-minimum-value",
        provisioning_secret="test",
    )
    with pytest.raises(HTTPException) as exc_info:
        verify_access_token(token, wrong_settings)
    assert exc_info.value.status_code == 401


def test_verify_access_token_malformed(settings):
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        verify_access_token("not-a-jwt-token", settings)
    assert exc_info.value.status_code == 401
