"""auth tables: departments, roles, users, user_roles, auth_tokens

Revision ID: 0001
Revises:
Create Date: 2026-10-19
"""
import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "departments",
        sa.Column("id", sa.Integer(), sa.Identity(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False, unique=True),
    )
    op.create_table(
        "roles",
        sa.Column("id", sa.Integer(), sa.Identity(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=True),
    )
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("email", sa.String(254), nullable=False, unique=True),
        sa.Column("full_name", sa.Text(), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("department_id", sa.Integer(), sa.ForeignKey("departments.id"), nullable=False),
        sa.Column("clearance_level", sa.SmallInteger(), server_default=sa.text("0"), nullable=False),
        sa.Column("country", sa.String(2), nullable=False),
        sa.Column("employment_type", sa.Text(), server_default=sa.text("'full_time'"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("auth_valid_after", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("email = lower(email)", name="ck_users_email_lowercase"),
        sa.CheckConstraint("clearance_level BETWEEN 0 AND 4", name="ck_users_clearance_range"),
        sa.CheckConstraint("char_length(country) = 2", name="ck_users_country_iso2"),
        sa.CheckConstraint(
            "employment_type IN ('full_time','part_time','contractor','intern')",
            name="ck_users_employment_type",
        ),
    )
    op.create_table(
        "user_roles",
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("role_id", sa.Integer(), sa.ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    )
    op.create_table(
        "auth_tokens",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("type", sa.Text(), nullable=False),
        sa.Column("token_hash", sa.Text(), nullable=False, unique=True),
        sa.Column("family_id", sa.Uuid(), nullable=True),
        sa.Column("remember_me", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("type IN ('REFRESH','RESET')", name="ck_auth_tokens_type"),
    )
    op.create_index("ix_auth_tokens_user_type", "auth_tokens", ["user_id", "type"])
    op.create_index("ix_auth_tokens_family", "auth_tokens", ["family_id"])


def downgrade() -> None:
    op.drop_table("auth_tokens")
    op.drop_table("user_roles")
    op.drop_table("users")
    op.drop_table("roles")
    op.drop_table("departments")
