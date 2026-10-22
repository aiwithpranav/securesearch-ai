"""Response and request shapes for the sync API (Phase 8B). Counts, code words, ids and non-secret settings: never document text."""
import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SyncRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    source_id: uuid.UUID
    status: str
    trigger: str
    started_at: datetime
    finished_at: datetime | None = None
    counts: dict[str, int]
    errors: list[dict[str, str]]
    error_code: str | None = None


class SyncSourceOut(BaseModel):
    id: uuid.UUID
    name: str
    kind: str
    config: dict[str, Any]
    enabled: bool
    interval_minutes: int
    last_run_at: datetime | None = None
    created_at: datetime
    last_run: SyncRunOut | None = None


class SyncSourceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=60, pattern=r"^[A-Za-z0-9][A-Za-z0-9 _.\-/]*$")
    kind: str = Field(min_length=1, max_length=30)
    config: dict[str, Any] = Field(default_factory=dict)
    interval_minutes: int = Field(default=15, ge=1, le=1440)


class SyncSourceUpdate(BaseModel):
    enabled: bool | None = None
    interval_minutes: int | None = Field(default=None, ge=1, le=1440)
