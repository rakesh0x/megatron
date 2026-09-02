"""Run bookkeeping: one record per (task, attempt) execution."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import Enum

from pydantic import BaseModel, Field


class RunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


def _utcnow() -> datetime:
    return datetime.now(UTC)


class RunRecord(BaseModel):
    run_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    task_id: str
    model_id: str
    attempt: int = 0
    status: RunStatus = RunStatus.PENDING
    reward: float | None = None
    verified: bool | None = None
    trajectory_path: str | None = None
    error: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    metadata: dict = Field(default_factory=dict)

    def start(self) -> None:
        self.status = RunStatus.RUNNING
        self.started_at = _utcnow()

    def finish(self, *, success: bool, error: str | None = None) -> None:
        self.status = RunStatus.SUCCESS if success else RunStatus.FAILED
        self.error = error
        self.finished_at = _utcnow()
