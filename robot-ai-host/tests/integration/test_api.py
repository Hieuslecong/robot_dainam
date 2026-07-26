"""Integration tests for the FastAPI application.

Tests the REST API endpoints using httpx AsyncClient.
Does NOT test WebRTC (requires actual WebRTC which needs system deps).
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client():
    """Create async test client with FastAPI lifespan initialized."""
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac


@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["version"] == "0.1.0"
    assert "active_sessions" in data
    assert "max_sessions" in data


@pytest.mark.asyncio
async def test_register_device_valid(client):
    resp = await client.post(
        "/v1/devices/register",
        json={
            "device_id": "test-device-001",
            "device_type": "browser_client",
            "firmware_version": "0.1.0",
            "provisioning_secret": "test-secret",
            "capabilities": {"audio_input": True, "audio_output": True},
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["device_id"] == "test-device-001"
    assert "access_token" in data
    assert data["expires_in"] > 0


@pytest.mark.asyncio
async def test_register_device_wrong_secret(client):
    resp = await client.post(
        "/v1/devices/register",
        json={
            "device_id": "test-device-001",
            "provisioning_secret": "wrong-secret",
        },
    )
    assert resp.status_code == 403


async def _get_token(client) -> str:
    """Helper to register and get token."""
    resp = await client.post(
        "/v1/devices/register",
        json={
            "device_id": "test-device-001",
            "provisioning_secret": "test-secret",
        },
    )
    return resp.json()["access_token"]


@pytest.mark.asyncio
async def test_create_session(client):
    token = await _get_token(client)
    resp = await client.post(
        "/v1/sessions",
        json={
            "device_id": "test-device-001",
            "profile": "mock",
            "language": "vi-VN",
            "transport": "webrtc",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["session_id"].startswith("sess_")
    assert data["status"] == "created"
    assert "webrtc" in data


@pytest.mark.asyncio
async def test_create_session_no_auth(client):
    resp = await client.post(
        "/v1/sessions",
        json={"device_id": "test", "profile": "mock"},
    )
    assert resp.status_code == 422 or resp.status_code == 401


@pytest.mark.asyncio
async def test_create_session_invalid_token(client):
    resp = await client.post(
        "/v1/sessions",
        json={"device_id": "test", "profile": "mock"},
        headers={"Authorization": "Bearer invalid-token"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_session(client):
    token = await _get_token(client)
    # Create session
    create_resp = await client.post(
        "/v1/sessions",
        json={"device_id": "test-device-001", "profile": "mock"},
        headers={"Authorization": f"Bearer {token}"},
    )
    session_id = create_resp.json()["session_id"]

    # Get session
    resp = await client.get(
        f"/v1/sessions/{session_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["session_id"] == session_id


@pytest.mark.asyncio
async def test_heartbeat(client):
    token = await _get_token(client)
    create_resp = await client.post(
        "/v1/sessions",
        json={"device_id": "test-device-001", "profile": "mock"},
        headers={"Authorization": f"Bearer {token}"},
    )
    session_id = create_resp.json()["session_id"]

    resp = await client.post(
        f"/v1/sessions/{session_id}/heartbeat",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_close_session(client):
    token = await _get_token(client)
    create_resp = await client.post(
        "/v1/sessions",
        json={"device_id": "test-device-001", "profile": "mock"},
        headers={"Authorization": f"Bearer {token}"},
    )
    session_id = create_resp.json()["session_id"]

    resp = await client.delete(
        f"/v1/sessions/{session_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "closed"


@pytest.mark.asyncio
async def test_close_session_idempotent(client):
    token = await _get_token(client)
    create_resp = await client.post(
        "/v1/sessions",
        json={"device_id": "test-device-001", "profile": "mock"},
        headers={"Authorization": f"Bearer {token}"},
    )
    session_id = create_resp.json()["session_id"]

    # Close twice
    await client.delete(
        f"/v1/sessions/{session_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    resp2 = await client.delete(
        f"/v1/sessions/{session_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp2.status_code == 200


@pytest.mark.asyncio
async def test_max_sessions_limit(client):
    token = await _get_token(client)
    # Create max sessions
    for i in range(4):
        resp = await client.post(
            "/v1/sessions",
            json={"device_id": "test-device-001", "profile": "mock"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200

    # 5th should fail
    resp = await client.post(
        "/v1/sessions",
        json={"device_id": "test-device-001", "profile": "mock"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 429


@pytest.mark.asyncio
async def test_session_bootstrap_returns_sdk_webrtc_url_and_scoped_token(client):
    token = await _get_token(client)
    resp = await client.post(
        "/v1/sessions",
        json={"device_id": "test-device-001", "profile": "mock"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["webrtcUrl"].startswith("http://test/v1/sessions/")
    assert "/api/offer?access_token=" in data["webrtcUrl"]
    assert data["webrtc"]["url"] == data["webrtcUrl"]


@pytest.mark.asyncio
async def test_session_uses_default_profile_when_omitted(client):
    token = await _get_token(client)
    resp = await client.post(
        "/v1/sessions",
        json={"device_id": "test-device-001"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    session_id = resp.json()["session_id"]
    state = await client.get(
        f"/v1/sessions/{session_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert state.json()["profile"] == "mock"


@pytest.mark.asyncio
async def test_cloud_session_fails_before_webrtc_when_credentials_missing(client):
    token = await _get_token(client)
    resp = await client.post(
        "/v1/sessions",
        json={"device_id": "test-device-001", "profile": "google_vi"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422
    assert "GOOGLE_APPLICATION_CREDENTIALS" in resp.text


@pytest.mark.asyncio
async def test_metrics_endpoint_contains_session_creation_evidence(client):
    token = await _get_token(client)
    resp = await client.post(
        "/v1/sessions",
        json={"device_id": "test-device-001", "profile": "mock"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    metrics = await client.get("/v1/metrics")
    assert metrics.status_code == 200
    assert metrics.json()["session_creation"]["count"] >= 1


@pytest.mark.asyncio
async def test_profiles_endpoint_exposes_hybrid_provider_chain(client):
    response = await client.get("/v1/profiles")
    assert response.status_code == 200
    hybrid = response.json()["hybrid_local_vi"]
    assert hybrid["stt"] == "whisper_local"
    assert hybrid["llm"] == "openai_compatible"
    assert hybrid["tts"] == "piper_http"
