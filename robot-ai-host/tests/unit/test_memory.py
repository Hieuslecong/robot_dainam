"""Long-term memory tests (spec 13.3–13.5, Phase 4 gate: zero cross-user leakage)."""

import pytest

from app.core.memory import MemoryRefused, MemoryStore


@pytest.fixture
def store(tmp_path):
    return MemoryStore(tmp_path)


def test_consent_required(store):
    with pytest.raises(MemoryRefused):
        store.remember("u1", "preferred_name", "Hiếu", consent=False)


def test_store_and_view_after_consent(store):
    store.remember("u1", "preferred_name", "Hiếu", consent=True)
    view = store.view("u1")
    assert view["items"]["preferred_name"]["value"] == "Hiếu"


def test_zero_cross_user_leakage(store):
    store.remember("alice", "preferred_name", "Alice", consent=True)
    assert store.view("bob")["items"] == {}


def test_non_allowlisted_kind_refused(store):
    with pytest.raises(MemoryRefused):
        store.remember("u1", "full_transcript", "...", consent=True)


def test_sensitive_content_refused_even_with_consent(store):
    for value in ("mật khẩu là 1234", "api key sk-abc", "tôi bị bệnh tiểu đường"):
        with pytest.raises(MemoryRefused):
            store.remember("u1", "preferred_name", value, consent=True)


def test_delete_one_and_all(store):
    store.remember("u1", "preferred_name", "Hiếu", consent=True)
    store.remember("u1", "address_style", "mình - bạn", consent=True)
    assert store.delete_one("u1", "preferred_name") is True
    assert "preferred_name" not in store.view("u1")["items"]
    store.delete_all("u1")
    assert store.view("u1")["items"] == {}


def test_disable_clears_and_blocks(store):
    store.remember("u1", "preferred_name", "Hiếu", consent=True)
    store.set_disabled("u1", True)
    assert store.view("u1")["items"] == {}
    with pytest.raises(MemoryRefused):
        store.remember("u1", "preferred_name", "Hiếu", consent=True)
    store.set_disabled("u1", False)
    store.remember("u1", "preferred_name", "Hiếu", consent=True)
    assert store.view("u1")["items"]
