"""evaluation tables: eval_cases, eval_runs, eval_results

Revision ID: 0007
Revises: 0006
Create Date: 2026-10-23
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "eval_cases",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("category", sa.Text(), nullable=False),
        sa.Column("persona", sa.Text(), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("definition", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
    )
    op.create_table(
        "eval_runs",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("label", sa.Text(), nullable=False),
        sa.Column("model_mode", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), server_default=sa.text("'RUNNING'"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_by", sa.Uuid(), nullable=True),
        sa.Column("total", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("passed", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("leak_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("summary", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.CheckConstraint("status in ('RUNNING','DONE','FAILED')", name="ck_eval_runs_status"),
        sa.CheckConstraint("model_mode in ('FAKE_MODEL','LIVE_MODEL')", name="ck_eval_runs_mode"),
    )
    op.create_index("ix_eval_runs_started", "eval_runs", ["started_at"])
    op.create_table(
        "eval_results",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("run_id", sa.Uuid(), sa.ForeignKey("eval_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("case_id", sa.Text(), nullable=False),
        sa.Column("category", sa.Text(), nullable=False),
        sa.Column("passed", sa.Boolean(), nullable=False),
        sa.Column("leaked", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("latency_ms", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("detail", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
    )
    op.create_index("ix_eval_results_run", "eval_results", ["run_id"])


def downgrade() -> None:
    op.drop_index("ix_eval_results_run", table_name="eval_results")
    op.drop_table("eval_results")
    op.drop_index("ix_eval_runs_started", table_name="eval_runs")
    op.drop_table("eval_runs")
    op.drop_table("eval_cases")
