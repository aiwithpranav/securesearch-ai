"""documents tables: documents, document_versions, ingestion_jobs, document_chunks, notifications

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-20
"""
import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # pgvector ships in our Postgres image but must be switched on once per database.
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "documents",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("original_filename", sa.Text(), nullable=False),
        sa.Column("document_type", sa.Text(), nullable=False),
        sa.Column("department_id", sa.Integer(), sa.ForeignKey("departments.id"), nullable=False),
        sa.Column("sensitivity_level", sa.SmallInteger(), nullable=False),
        sa.Column("status", sa.Text(), server_default=sa.text("'QUEUED'"), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("external_source", sa.Text(), nullable=True),
        sa.Column("external_id", sa.Text(), nullable=True),
        sa.Column("allowed_countries", postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column("current_version_id", sa.Uuid(), nullable=True),
        sa.Column("uploaded_by", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("status IN ('QUEUED','PROCESSING','READY','FAILED')", name="ck_documents_status"),
        sa.CheckConstraint("sensitivity_level BETWEEN 0 AND 4", name="ck_documents_sensitivity"),
        sa.CheckConstraint(
            "document_type IN ('POLICY','RUNBOOK','REPORT','PLAYBOOK','FORECAST','CONTRACT','OTHER')",
            name="ck_documents_type",
        ),
    )
    op.create_index("ix_documents_status", "documents", ["status"])
    op.create_index("ix_documents_department", "documents", ["department_id"])

    op.create_table(
        "document_versions",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("document_id", sa.Uuid(), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("content_hash", sa.Text(), nullable=False),
        sa.Column("permission_hash", sa.Text(), nullable=True),
        sa.Column("storage_path", sa.Text(), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("content_type", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("document_id", "version_no", name="uq_document_versions_no"),
    )
    op.create_index("ix_document_versions_hash", "document_versions", ["content_hash"])

    op.create_table(
        "ingestion_jobs",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("document_id", sa.Uuid(), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "document_version_id", sa.Uuid(), sa.ForeignKey("document_versions.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("status", sa.Text(), server_default=sa.text("'QUEUED'"), nullable=False),
        sa.Column("content_hash", sa.Text(), nullable=False),
        sa.Column("attempt", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("error_code", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("status IN ('QUEUED','PROCESSING','READY','FAILED')", name="ck_ingestion_jobs_status"),
    )
    op.create_index("ix_ingestion_jobs_document", "ingestion_jobs", ["document_id"])
    op.create_index("ix_ingestion_jobs_status", "ingestion_jobs", ["status"])
    # At most ONE unfinished job per document, enforced by the database itself (no double processing).
    op.create_index(
        "uq_ingestion_jobs_one_active", "ingestion_jobs", ["document_id"], unique=True,
        postgresql_where=sa.text("status IN ('QUEUED','PROCESSING')"),
    )

    op.create_table(
        "document_chunks",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("document_id", sa.Uuid(), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "document_version_id", sa.Uuid(), sa.ForeignKey("document_versions.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "ingestion_job_id", sa.Uuid(), sa.ForeignKey("ingestion_jobs.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("section", sa.Text(), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=False),
        sa.Column("embedding", Vector(384), nullable=False),
        sa.Column("embedding_model", sa.Text(), nullable=False),
        sa.Column(
            "tsv", postgresql.TSVECTOR(), sa.Computed("to_tsvector('english', content)", persisted=True)
        ),
        sa.UniqueConstraint("ingestion_job_id", "chunk_index", name="uq_document_chunks_job_index"),
    )
    op.create_index("ix_document_chunks_document_active", "document_chunks", ["document_id", "is_active"])
    op.create_index("ix_document_chunks_job", "document_chunks", ["ingestion_job_id"])
    # No GIN (full-text) or HNSW (vector) index yet: those belong to Phase 5.

    op.create_table(
        "notifications",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("payload", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_notifications_user_unread", "notifications", ["user_id", "read_at"])


def downgrade() -> None:
    op.drop_table("notifications")
    op.drop_table("document_chunks")
    op.drop_table("ingestion_jobs")
    op.drop_table("document_versions")
    op.drop_table("documents")
    # The vector extension is left installed on purpose (other databases objects may use it).
