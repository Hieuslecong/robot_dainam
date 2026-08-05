"""Tests for session management."""

import asyncio
import time

import pytest

from app.config import Settings
from app.sessions import SessionInfo, SessionManager, SessionState


@pytest.fixture
def settings():
    return Settings(
        provisioning_secret="test",
        jwt_secret_key="test-key-32-bytes-minimum-value",
        max_sessions=4,
        local_stt_max_sessions=1,
        heartbeat_timeout_seconds=5,
    )


@pytest.fixture
def manager(settings):
    return SessionManager(settings)


@pytest.mark.asyncio
async def test_create_session(manager):
    session = await manager.create_session("dev-001", "mock")
    assert session.session_id.startswith("sess_")
    assert session.device_id == "dev-001"
    assert session.profile == "mock"
    assert session.state == SessionState.CREATED


@pytest.mark.asyncio
async def test_create_session_max_limit(manager):
    for i in range(4):
        await manager.create_session(f"dev-{i}", "mock")

    with pytest.raises(ValueError, match="Max sessions"):
        await manager.create_session("dev-extra", "mock")


@pytest.mark.asyncio
async def test_get_session(manager):
    created = await manager.create_session("dev-001", "mock")
    found = await manager.get_session(created.session_id)
    assert found is not None
    assert found.session_id == created.session_id


@pytest.mark.asyncio
async def test_get_session_unknown(manager):
    result = await manager.get_session("sess_nonexistent")
    assert result is None


@pytest.mark.asyncio
async def test_update_heartbeat(manager):
    session = await manager.create_session("dev-001", "mock")
    old_hb = session.last_heartbeat
    await asyncio.sleep(0.01)
    assert await manager.update_heartbeat(session.session_id)
    updated = await manager.get_session(session.session_id)
    assert updated.last_heartbeat >= old_hb


@pytest.mark.asyncio
async def test_close_session(manager):
    session = await manager.create_session("dev-001", "mock")
    assert await manager.close_session(session.session_id)
    closed = await manager.get_session(session.session_id)
    assert closed.state == SessionState.CLOSED


@pytest.mark.asyncio
async def test_close_session_idempotent(manager):
    session = await manager.create_session("dev-001", "mock")
    assert await manager.close_session(session.session_id)
    assert await manager.close_session(session.session_id)  # Second close should work


@pytest.mark.asyncio
async def test_close_unknown_session(manager):
    assert not await manager.close_session("sess_unknown")


@pytest.mark.asyncio
async def test_validate_ownership(manager):
    session = await manager.create_session("dev-001", "mock")
    assert manager.validate_ownership(session.session_id, "dev-001")
    assert not manager.validate_ownership(session.session_id, "dev-002")


@pytest.mark.asyncio
async def test_validate_ownership_unknown(manager):
    assert not manager.validate_ownership("sess_none", "dev-001")


@pytest.mark.asyncio
async def test_cleanup_expired(manager):
    # Create with very short timeout
    manager._settings.heartbeat_timeout_seconds = 0
    session = await manager.create_session("dev-001", "mock")
    # Force old heartbeat
    session.last_heartbeat = time.time() - 10

    closed = await manager.cleanup_expired()
    assert session.session_id in closed


@pytest.mark.asyncio
async def test_active_count(manager):
    assert manager.active_count == 0
    await manager.create_session("dev-001", "mock")
    assert manager.active_count == 1
    s2 = await manager.create_session("dev-002", "mock")
    assert manager.active_count == 2
    await manager.close_session(s2.session_id)
    assert manager.active_count == 1


@pytest.mark.asyncio
async def test_list_sessions(manager):
    await manager.create_session("dev-001", "mock")
    await manager.create_session("dev-002", "mock")
    sessions = await manager.list_sessions()
    assert len(sessions) == 2


@pytest.mark.asyncio
async def test_four_sessions_keep_device_and_profile_isolated(manager):
    expected = {}
    for index, name in enumerate(["An", "Bình", "Chi", "Dũng"], start=1):
        session = await manager.create_session(f"device-{index}", "mock")
        session.metrics_summary = {"identity": name}
        expected[session.session_id] = (f"device-{index}", name)

    sessions = await manager.list_sessions()
    assert len(sessions) == 4
    for session in sessions:
        device, identity = expected[session.session_id]
        assert session.device_id == device
        assert session.metrics_summary == {"identity": identity}


@pytest.mark.asyncio
async def test_close_session_cancels_registered_runner(manager):
    class FakeRunner:
        def __init__(self):
            self.cancelled = False
            self.reason = None

        async def cancel(self, reason=None):
            self.cancelled = True
            self.reason = reason

    session = await manager.create_session("dev-runner", "mock")
    runner = FakeRunner()
    manager.register_worker(session.session_id, worker=object(), runner=runner)
    assert await manager.close_session(session.session_id)
    assert runner.cancelled is True
    assert runner.reason == "session_closed"


@pytest.mark.asyncio
async def test_register_worker_rejects_duplicate_pipeline(manager):
    session = await manager.create_session("dev-duplicate", "mock")
    manager.register_worker(session.session_id, worker=object(), runner=object())
    assert manager.has_worker(session.session_id)
    with pytest.raises(ValueError, match="Worker already registered"):
        manager.register_worker(session.session_id, worker=object(), runner=object())


@pytest.mark.asyncio
async def test_local_whisper_profile_has_conservative_session_limit(manager):
    await manager.create_session("dev-hybrid-1", "hybrid_local_vi")
    with pytest.raises(ValueError, match="Local Whisper session limit"):
        await manager.create_session("dev-hybrid-2", "hybrid_local_vi")


@pytest.mark.asyncio
async def test_close_session_closes_pipeline_bundle(manager):
    class FakeRunner:
        async def cancel(self, reason=None):
            return None

    class FakeBundle:
        def __init__(self):
            self.closed = False

        async def aclose(self):
            self.closed = True

    session = await manager.create_session("dev-resource", "mock")
    bundle = FakeBundle()
    manager.register_worker(
        session.session_id,
        worker=object(),
        runner=FakeRunner(),
        bundle=bundle,
    )
    assert await manager.close_session(session.session_id)
    assert bundle.closed is True
