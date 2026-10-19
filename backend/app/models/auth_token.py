import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Text, Uuid, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AuthToken(Base):
    """Refresh tokens (login sessions) and reset tokens (password reset / invite).

    We store only a SHA-256 hash of the token, never the token itself, so a
    database leak does not hand out working sessions or reset links.
    """

    __tablename__ = "auth_tokens"
    __table_args__ = (
        CheckConstraint("type IN ('REFRESH','RESET')", name="ck_auth_tokens_type"),
        Index("ix_auth_tokens_user_type", "user_id", "type"),
        Index("ix_auth_tokens_family", "family_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[str] = mapped_column(Text, nullable=False)
    token_hash: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    # All refresh tokens from one login share a family. If an old (already used)
    # token shows up again, we revoke the whole family: it was probably stolen.
    family_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    remember_me: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
