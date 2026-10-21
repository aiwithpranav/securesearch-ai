"""Tables for Phase 6B: each person's own search history and their feedback on answers.

Privacy design: the history belongs to the person and they can delete it. It stores the question, the outcome and
the ids of the cited passages, but NOT the answer text, so an answer never outlives the permission it was built on.
The audit log for security staff is a separate thing (Phase 7)."""
import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, SmallInteger, Text, Uuid, func, text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

CHAT_STATUSES = ("ANSWERED", "REFUSED_NO_ACCESS_EVIDENCE", "REFUSED_LOW_CONFIDENCE")


class SearchHistory(Base):
    __tablename__ = "search_history"
    __table_args__ = (
        Index("ix_search_history_user_created", "user_id", "created_at"),
        CheckConstraint("status in ('ANSWERED','REFUSED_NO_ACCESS_EVIDENCE','REFUSED_LOW_CONFIDENCE')", name="ck_search_history_status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    citation_chunk_ids: Mapped[list[uuid.UUID]] = mapped_column(ARRAY(Uuid), nullable=False, server_default=text("'{}'"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class ChatFeedback(Base):
    __tablename__ = "chat_feedback"
    __table_args__ = (CheckConstraint("rating in (-1, 1)", name="ck_chat_feedback_rating"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    # one rating per history item; rating again replaces it. Deleting the history item deletes its feedback.
    history_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("search_history.id", ondelete="CASCADE"), unique=True, nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    rating: Mapped[int] = mapped_column(SmallInteger, nullable=False)  # 1 thumbs up, -1 thumbs down
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
