"""Response shapes for the evaluation API. Ids, numbers, code words and the synthetic question: never answer or document text."""
import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class RunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    label: str
    model_mode: str
    status: str
    started_at: datetime
    finished_at: datetime | None = None
    total: int
    passed: int
    leak_count: int
    summary: dict[str, Any]


class ResultOut(BaseModel):
    case_id: str
    category: str
    persona: str | None = None
    question: str | None = None
    passed: bool
    leaked: bool
    latency_ms: int
    detail: dict[str, Any]


class RunDetail(RunOut):
    results: list[ResultOut]
