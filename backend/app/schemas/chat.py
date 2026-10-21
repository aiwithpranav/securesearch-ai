"""Request and response shapes for answers, evidence preview, history and feedback (Phase 6B).

The chat response follows the blueprint's agreed shape. `history_id` is one additive field so the screen can attach
feedback to the answer. A refusal carries `answer: null` and no citations, and the same text for every reason."""
import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.retrieval.search import MAX_QUERY_CHARS

ChatStatus = Literal["ANSWERED", "REFUSED_NO_ACCESS_EVIDENCE", "REFUSED_LOW_CONFIDENCE"]


class ChatRequest(BaseModel):
    question: str = Field(max_length=MAX_QUERY_CHARS * 4)

    @field_validator("question")
    @classmethod
    def _rules(cls, value: str) -> str:
        value = " ".join(value.split())
        if not value:
            raise ValueError("Enter a question.")
        if len(value) > MAX_QUERY_CHARS:
            raise ValueError(f"Keep the question under {MAX_QUERY_CHARS} characters.")
        return value


class CitationOut(BaseModel):
    source_id: str
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    document_title: str
    section: str | None = None
    page: int | None = None
    snippet: str
    document_updated_at: datetime | None = None


class ChatResponse(BaseModel):
    status: ChatStatus
    answer: str | None = None
    refusal: str | None = None  # the one uniform refusal text, only when status is a refusal
    citations: list[CitationOut] = []
    request_id: str | None = None
    history_id: uuid.UUID | None = None


class FeedbackIn(BaseModel):
    history_id: uuid.UUID
    rating: Literal["UP", "DOWN"]
    comment: str | None = Field(default=None, max_length=500)

    @field_validator("comment")
    @classmethod
    def _trim(cls, value: str | None) -> str | None:
        value = (value or "").strip()
        return value or None


class FeedbackOut(BaseModel):
    history_id: uuid.UUID
    rating: Literal["UP", "DOWN"]


class HistoryItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    question: str
    status: ChatStatus
    citation_count: int
    rating: Literal["UP", "DOWN"] | None = None
    created_at: datetime


class HistoryPage(BaseModel):
    items: list[HistoryItemOut]
    total: int
    limit: int
    offset: int


class ChunkPreviewOut(BaseModel):
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    document_title: str
    section: str | None = None
    page: int | None = None
    content: str
    document_updated_at: datetime | None = None
