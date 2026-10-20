"""access tables: groups, user_groups, document_acl, permission_change_events

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-20
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "groups",
        sa.Column("id", sa.Integer(), sa.Identity(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=True),
    )
    op.create_table(
        "user_groups",
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("group_id", sa.Integer(), sa.ForeignKey("groups.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "document_acl",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("document_id", sa.Uuid(), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("principal_type", sa.Text(), nullable=False),
        sa.Column("principal_id", sa.Text(), nullable=True),
        sa.Column("effect", sa.Text(), nullable=False),
        sa.Column("permission", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("granted_by", sa.Uuid(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "principal_type IN ('USER','ROLE','GROUP','DEPARTMENT','COMPANY')", name="ck_document_acl_principal_type"
        ),
        sa.CheckConstraint("effect IN ('ALLOW','DENY')", name="ck_document_acl_effect"),
        sa.CheckConstraint("permission IN ('READ','DOWNLOAD','MANAGE')", name="ck_document_acl_permission"),
        sa.CheckConstraint(
            "(principal_type = 'COMPANY' AND principal_id IS NULL) OR (principal_type <> 'COMPANY' AND principal_id IS NOT NULL)",
            name="ck_document_acl_principal_id",
        ),
    )
    op.create_index("ix_document_acl_document", "document_acl", ["document_id"])
    op.create_index("ix_document_acl_principal", "document_acl", ["principal_type", "principal_id"])
    op.create_index(
        "uq_document_acl_rule", "document_acl",
        ["document_id", "principal_type", sa.text("coalesce(principal_id, '')"), "effect", "permission"],
        unique=True,
    )

    op.create_table(
        "permission_change_events",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("document_id", sa.Uuid(), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("prev_acl", postgresql.JSONB(), nullable=False),
        sa.Column("new_acl", postgresql.JSONB(), nullable=False),
        sa.Column("changed_by", sa.Uuid(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("changed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_permission_change_events_document", "permission_change_events", ["document_id", "changed_at"])


def downgrade() -> None:
    op.drop_table("permission_change_events")
    op.drop_table("document_acl")
    op.drop_table("user_groups")
    op.drop_table("groups")
