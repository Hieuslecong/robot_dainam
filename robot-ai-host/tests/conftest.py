"""Shared test fixtures."""

import asyncio
import os

import pytest

# Set test environment
os.environ.setdefault("PROVISIONING_SECRET", "test-secret")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-key-32-bytes-minimum-value")
os.environ.setdefault("MAX_SESSIONS", "4")
os.environ.setdefault("DEFAULT_PROFILE", "mock")


@pytest.fixture
def settings():
    """Test settings."""
    from app.config import Settings
    return Settings(
        provisioning_secret="test-secret",
        jwt_secret_key="test-jwt-key-32-bytes-minimum-value",
        max_sessions=4,
        default_profile="mock",
    )


@pytest.fixture
def session_manager(settings):
    """Test session manager."""
    from app.sessions import SessionManager
    return SessionManager(settings)
