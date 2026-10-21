"""Tables for Phase 3: documents, their versions, the text chunks with vectors, ingestion jobs
and in-app notifications. There is NO ACL table yet (Phase 4): until then no reader can see any document."""
import uuid
from datetime import datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Computed,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    Text,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# Status words (blueprint user story US-15): QUEUED > PROCESSING > READY, or FAILED.
QUEUED, PROCESSING, READY, FAILED = "QUEUED", "PROCESSING", "READY", "FAILED"
STATUSES = (QUEUED, PROCESSING, READY, FAILED)
DOCUMENT_TYPES = ("POLICY", "RUNBOOK", "REPORT", "PLAYBOOK", "FORECAST", "CONTRACT", "OTHER")
SENSITIVITY_NAMES = {0: "PUBLIC", 1: "INTERNAL", 2: "CONFIDENTIAL", 3: "RESTRICTED", 4: "HIGHLY_RESTRICTED"}


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (
        CheckConstraint("status IN ('QUEUED','PROCESSING','READY','FAILED')", name="ck_documents_status"),
        CheckConstraint("sensitivity_level BETWEEN 0 AND 4", name="ck_documents_sensitivity"),
        CheckConstraint(
            "document_type IN ('POLICY','RUNBOOK','REPORT','PLAYBOOK','FORECAST','CONTRACT','OTHER')",
            name="ck_documents_type",
        ),
        Index("ix_documents_status", "status"),
        Index("ix_documents_department", "department_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()")
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    original_filename: Mapped[str] = mapped_column(Text, nullable=False)  # cleaned, shown to admins only
    document_type: Mapped[str] = mapped_column(Text, nullable=False)
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"), nullable=False)
    sensitivity_level: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'QUEUED'"))
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    external_source: Mapped[str | None] = mapped_column(Text, nullable=True)  # Phase 8
    external_id: Mapped[str | None] = mapped_column(Text, nullable=True)  # Phase 8
    allowed_countries: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    current_version_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    uploaded_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class DocumentVersion(Base):
    __tablename__ = "document_versions"
    __table_args__ = (
        UniqueConstraint("document_id", "version_no", name="uq_document_versions_no"),
        Index("ix_document_versions_hash", "content_hash"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()")
    )
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    content_hash: Mapped[str] = mapped_column(Text, nullable=False)  # SHA-256 of the original file
    permission_hash: Mapped[str | None] = mapped_column(Text, nullable=True)  # Phase 8
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)  # key in object storage
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    content_type: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class IngestionJob(Base):
    __tablename__ = "ingestion_jobs"
    __table_args__ = (
        CheckConstraint("status IN ('QUEUED','PROCESSING','READY','FAILED')", name="ck_ingestion_jobs_status"),
        Index("ix_ingestion_jobs_document", "document_id"),
        Index("ix_ingestion_jobs_status", "status"),
        Index(
            "uq_ingestion_jobs_one_active", "document_id", unique=True,
            postgresql_where=text("status IN ('QUEUED','PROCESSING')"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()")
    )
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    document_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("document_versions.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'QUEUED'"))
    content_hash: Mapped[str] = mapped_column(Text, nullable=False)
    attempt: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    error_code: Mapped[str | None] = mapped_column(Text, nullable=True)  # fixed codes only
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)  # fixed text, never file content
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class DocumentChunk(Base):
    """One piece of a document's text with its vector. Chunks inherit the document's ACL (no chunk ACL)."""

    __tablename__ = "document_chunks"
    __table_args__ = (
        Index("ix_document_chunks_document_active", "document_id", "is_active"),
        Index("ix_document_chunks_job", "ingestion_job_id"),
        UniqueConstraint("ingestion_job_id", "chunk_index", name="uq_document_chunks_job_index"),
        Index("ix_document_chunks_tsv", "tsv", postgresql_using="gin"),
        Index(
            "ix_document_chunks_embedding_hnsw", "embedding", postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64}, postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()")
    )
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    document_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("document_versions.id", ondelete="CASCADE"), nullable=False
    )
    ingestion_job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ingestion_jobs.id", ondelete="CASCADE"), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    section: Mapped[str | None] = mapped_column(Text, nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False)
    embedding: Mapped[Any] = mapped_column(Vector(384), nullable=False)
    embedding_model: Mapped[str] = mapped_column(Text, nullable=False)
    # Full-text search column, filled by Postgres itself (GIN index ix_document_chunks_tsv).
    tsv: Mapped[Any] = mapped_column(TSVECTOR, Computed("to_tsvector('english', content)", persisted=True))


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (Index("ix_notifications_user_unread", "user_id", "read_at"),)

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
