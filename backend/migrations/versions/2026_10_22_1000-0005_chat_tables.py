"""chat tables: search_history and chat_feedback

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-22
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "search_history",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("citation_chunk_ids", postgresql.ARRAY(sa.Uuid()), server_default=sa.text("'{}'"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("status in ('ANSWERED','REFUSED_NO_ACCESS_EVIDENCE','REFUSED_LOW_CONFIDENCE')", name="ck_search_history_status"),
    )
    op.create_index("ix_search_history_user_created", "search_history", ["user_id", "created_at"])
    op.create_table(
        "chat_feedback",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("history_id", sa.Uuid(), sa.ForeignKey("search_history.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("rating", sa.SmallInteger(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("rating in (-1, 1)", name="ck_chat_feedback_rating"),
    )


def downgrade() -> None:
    op.drop_table("chat_feedback")
    op.drop_index("ix_search_history_user_created", table_name="search_history")
    op.drop_table("search_history")
