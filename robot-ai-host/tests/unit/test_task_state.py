"""Task state tests (spec 10.5)."""

import time

from app.core.task_state import TaskState, TaskStatus, TaskStore


def _create(store, **kwargs):
    defaults = dict(session_id="s1", user_id="u1", intent="action_request",
                    risk_level="confirmed_write")
    defaults.update(kwargs)
    return store.create(**defaults)


def test_schema_has_all_spec_fields():
    task = TaskState(session_id="s", user_id="u", intent="i", risk_level="r")
    for field in ("task_id", "session_id", "user_id", "intent", "risk_level",
                  "current_node", "collected_fields", "missing_fields",
                  "normalized_fields", "confirmation_status", "tool_calls",
                  "tool_results", "retry_count", "created_at", "updated_at", "status"):
        assert hasattr(task, field)


def test_lifecycle_transitions():
    store = TaskStore()
    task = _create(store)
    assert task.status == TaskStatus.CREATED
    task.touch(TaskStatus.COLLECTING)
    task.touch(TaskStatus.AWAITING_CONFIRMATION)
    task.touch(TaskStatus.EXECUTING)
    task.touch(TaskStatus.COMPLETED)
    assert store.get(task.task_id).status == TaskStatus.COMPLETED


def test_expiry():
    store = TaskStore(expiry_seconds=0.0)
    task = _create(store)
    task.updated_at = time.time() - 1
    assert store.get(task.task_id).status == TaskStatus.EXPIRED


def test_completed_task_never_expires():
    store = TaskStore(expiry_seconds=0.0)
    task = _create(store)
    task.touch(TaskStatus.COMPLETED)
    task.updated_at = time.time() - 999
    assert store.get(task.task_id).status == TaskStatus.COMPLETED


def test_clear_on_session_end():
    store = TaskStore()
    _create(store)
    store.clear()
    assert store.active() == []
