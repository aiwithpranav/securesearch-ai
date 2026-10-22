"""audit tables: query_audit_logs, answer_audit_logs, access_events (append-only)

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-22
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None

TABLES = ("query_audit_logs", "answer_audit_logs", "access_events")


def upgrade() -> None:
    op.create_table(
        "query_audit_logs",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("query_text", sa.Text(), nullable=False),
        sa.Column("filters", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("allowed_doc_count", sa.Integer(), nullable=False),
        sa.Column("retrieved_chunk_ids", postgresql.ARRAY(sa.Uuid()), server_default=sa.text("'{}'"), nullable=False),
        sa.Column("response_status", sa.Text(), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("request_id", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("kind in ('SEARCH','CHAT')", name="ck_query_audit_kind"),
    )
    op.create_index("ix_query_audit_created", "query_audit_logs", ["created_at"])
    op.create_index("ix_query_audit_user_created", "query_audit_logs", ["user_id", "created_at"])
    op.create_table(
        "answer_audit_logs",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("query_audit_id", sa.Uuid(), sa.ForeignKey("query_audit_logs.id"), nullable=False, unique=True),
        sa.Column("citation_chunk_ids", postgresql.ARRAY(sa.Uuid()), server_default=sa.text("'{}'"), nullable=False),
        sa.Column("model", sa.Text(), nullable=False),
        sa.Column("prompt_version", sa.Text(), nullable=False),
        sa.Column("llm_calls", sa.Integer(), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=False),
        sa.Column("output_tokens", sa.Integer(), nullable=False),
        sa.Column("answer_chars", sa.Integer(), nullable=False),
        sa.Column("refusal_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "access_events",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("event", sa.Text(), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=True),
        sa.Column("subject_id", sa.Uuid(), nullable=True),
        sa.Column("detail", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("request_id", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_access_events_created", "access_events", ["created_at"])
    op.create_index("ix_access_events_event_created", "access_events", ["event", "created_at"])
    # Append-only: whoever connects to the database, rows can be added but never changed or removed.
    op.execute(
        "CREATE FUNCTION audit_append_only() RETURNS trigger LANGUAGE plpgsql AS $$ "
        "BEGIN RAISE EXCEPTION 'audit rows are append-only (% on %)', TG_OP, TG_TABLE_NAME; END $$"
    )
    for table in TABLES:
        op.execute(
            f"CREATE TRIGGER {table}_append_only BEFORE UPDATE OR DELETE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION audit_append_only()"
        )


def downgrade() -> None:
    for table in TABLES:
        op.execute(f"DROP TRIGGER {table}_append_only ON {table}")
    op.execute("DROP FUNCTION audit_append_only()")
    op.drop_table("access_events")
    op.drop_table("answer_audit_logs")
    op.drop_index("ix_query_audit_user_created", table_name="query_audit_logs")
    op.drop_index("ix_query_audit_created", table_name="query_audit_logs")
    op.drop_table("query_audit_logs")
