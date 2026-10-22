"""sync tables: sync_sources, sync_runs, one document per source item

Revision ID: 0008
Revises: 0007
Create Date: 2026-10-23
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sync_sources",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False, unique=True),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("config", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("interval_minutes", sa.Integer(), server_default=sa.text("15"), nullable=False),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("interval_minutes between 1 and 1440", name="ck_sync_sources_interval"),
    )
    op.create_table(
        "sync_runs",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("source_id", sa.Uuid(), sa.ForeignKey("sync_sources.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.Text(), server_default=sa.text("'RUNNING'"), nullable=False),
        sa.Column("trigger", sa.Text(), nullable=False),
        sa.Column("started_by", sa.Uuid(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("counts", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("errors", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("error_code", sa.Text(), nullable=True),
        sa.CheckConstraint("status in ('RUNNING','DONE','PARTIAL','FAILED')", name="ck_sync_runs_status"),
        sa.CheckConstraint("trigger in ('SCHEDULE','MANUAL')", name="ck_sync_runs_trigger"),
    )
    op.create_index("ix_sync_runs_source_started", "sync_runs", ["source_id", "started_at"])
    op.create_index("uq_sync_runs_one_running", "sync_runs", ["source_id"], unique=True, postgresql_where=sa.text("status = 'RUNNING'"))
    op.create_index(
        "uq_documents_external_item", "documents", ["external_source", "external_id"], unique=True,
        postgresql_where=sa.text("external_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_documents_external_item", table_name="documents")
    op.drop_index("uq_sync_runs_one_running", table_name="sync_runs")
    op.drop_index("ix_sync_runs_source_started", table_name="sync_runs")
    op.drop_table("sync_runs")
    op.drop_table("sync_sources")
