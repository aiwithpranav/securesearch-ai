"""Response shapes for the audit API (Phase 7A). Ids, counts, code words and the question text, for the audit roles only.
There is deliberately no field for an answer text or for document text."""
import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class PersonRef(BaseModel):
    id: uuid.UUID
    full_name: str | None = None  # None when the account no longer exists
    email: str | None = None


class QueryAuditOut(BaseModel):
    id: uuid.UUID
    created_at: datetime
    user: PersonRef
    kind: str
    query_text: str
    filters: dict[str, Any]
    allowed_doc_count: int
    retrieved_chunk_ids: list[uuid.UUID]
    response_status: str
    latency_ms: int
    request_id: str | None = None


class QueryAuditPage(BaseModel):
    items: list[QueryAuditOut]
    total: int
    limit: int
    offset: int


class AnswerAuditOut(BaseModel):
    id: uuid.UUID
    query_audit_id: uuid.UUID
    created_at: datetime
    citation_chunk_ids: list[uuid.UUID]
    model: str
    prompt_version: str
    llm_calls: int
    input_tokens: int
    output_tokens: int
    answer_chars: int
    refusal_reason: str | None = None


class AnswerAuditPage(BaseModel):
    items: list[AnswerAuditOut]
    total: int
    limit: int
    offset: int


class AccessEventOut(BaseModel):
    id: uuid.UUID
    created_at: datetime
    event: str
    actor: PersonRef | None = None
    subject: PersonRef | None = None
    detail: dict[str, Any]
    request_id: str | None = None


class AccessEventPage(BaseModel):
    items: list[AccessEventOut]
    total: int
    limit: int
    offset: int
