"""Task state schema and per-session store (spec 10.5)."""

from __future__ import annotations

import time
import uuid
from enum import Enum

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    CREATED = "created"
    COLLECTING = "collecting"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class TaskState(BaseModel):
    task_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    session_id: str
    user_id: str
    intent: str
    risk_level: str
    current_node: str = "start"
    collected_fields: dict = Field(default_factory=dict)
    missing_fields: list[str] = Field(default_factory=list)
    normalized_fields: dict = Field(default_factory=dict)
    confirmation_status: str = "not_required"  # not_required|pending|confirmed|denied
    tool_calls: list[dict] = Field(default_factory=list)
    tool_results: list[dict] = Field(default_factory=list)
    retry_count: int = 0
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)
    status: TaskStatus = TaskStatus.CREATED

    def touch(self, status: TaskStatus | None = None) -> None:
        self.updated_at = time.time()
        if status is not None:
            self.status = status


class TaskStore:
    """In-memory task state, strictly scoped to one session (spec 19.2)."""

    def __init__(self, *, expiry_seconds: float = 600.0) -> None:
        self._tasks: dict[str, TaskState] = {}
        self._expiry = expiry_seconds

    def create(self, **kwargs) -> TaskState:
        task = TaskState(**kwargs)
        self._tasks[task.task_id] = task
        return task

    def get(self, task_id: str) -> TaskState | None:
        task = self._tasks.get(task_id)
        if task is None:
            return None
        if time.time() - task.updated_at > self._expiry and task.status not in (
            TaskStatus.COMPLETED,
            TaskStatus.FAILED,
            TaskStatus.CANCELLED,
        ):
            task.touch(TaskStatus.EXPIRED)
        return task

    def active(self) -> list[TaskState]:
        return [
            t
            for t in self._tasks.values()
            if self.get(t.task_id).status
            in (TaskStatus.CREATED, TaskStatus.COLLECTING, TaskStatus.AWAITING_CONFIRMATION, TaskStatus.EXECUTING)
        ]

    def clear(self) -> None:
        self._tasks.clear()
