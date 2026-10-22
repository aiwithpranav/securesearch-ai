"""Audit tables (Phase 7A). Append-only: the database refuses UPDATE and DELETE on all three (see migration 0006).

What is stored, and what is not:
- WHO asked WHAT and WHEN, which passages were retrieved and cited (ids), the outcome, the speed. The question text
  is kept because auditors need it; only the audit roles may read it.
- NEVER the answer text and NEVER document text: only ids, counts and code words. So the audit log can not leak what
  an answer said, and it never outlives the permission an answer was built on.
- user_id has no foreign key on purpose: the audit trail must survive whatever happens to the account."""
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, Text, Uuid, func, text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class QueryAuditLog(Base):
    __tablename__ = "query_audit_logs"
    __table_args__ = (
        Index("ix_query_audit_created", "created_at"),
        Index("ix_query_audit_user_created", "user_id", "created_at"),
        CheckConstraint("kind in ('SEARCH','CHAT')", name="ck_query_audit_kind"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    kind: Mapped[str] = mapped_column(Text, nullable=False)  # SEARCH or CHAT
    query_text: Mapped[str] = mapped_column(Text, nullable=False)
    filters: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))  # mode, rerank, limits
    allowed_doc_count: Mapped[int] = mapped_column(Integer, nullable=False)  # how many documents the person could read
    retrieved_chunk_ids: Mapped[list[uuid.UUID]] = mapped_column(ARRAY(Uuid), nullable=False, server_default=text("'{}'"))
    response_status: Mapped[str] = mapped_column(Text, nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    request_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class AnswerAuditLog(Base):
    __tablename__ = "answer_audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    query_audit_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("query_audit_logs.id"), unique=True, nullable=False)
    citation_chunk_ids: Mapped[list[uuid.UUID]] = mapped_column(ARRAY(Uuid), nullable=False, server_default=text("'{}'"))
    model: Mapped[str] = mapped_column(Text, nullable=False)
    prompt_version: Mapped[str] = mapped_column(Text, nullable=False)
    llm_calls: Mapped[int] = mapped_column(Integer, nullable=False)
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    answer_chars: Mapped[int] = mapped_column(Integer, nullable=False)  # the length only, never the text
    refusal_reason: Mapped[str | None] = mapped_column(Text, nullable=True)  # a fixed code word
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class AccessEvent(Base):
    """Security events: sign-ins, failures, lockouts, token reuse, password changes, and every change an administrator
    makes to people, groups, documents and access rules. Ids only."""

    __tablename__ = "access_events"
    __table_args__ = (Index("ix_access_events_created", "created_at"), Index("ix_access_events_event_created", "event", "created_at"))

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    event: Mapped[str] = mapped_column(Text, nullable=False)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)  # who did it (an administrator, or the person themselves)
    subject_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)  # who it was done to, when that is someone else
    detail: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))  # ids only
    request_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
