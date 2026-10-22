"""Tables for Phase 8B: the connected sources and the history of sync runs (CR-004).

Privacy: a source holds NON-secret settings only (tokens stay in .env). A run holds counts, code words and source item ids,
never document text."""
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, Text, Uuid, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SyncSource(Base):
    __tablename__ = "sync_sources"
    __table_args__ = (CheckConstraint("interval_minutes between 1 and 1440", name="ck_sync_sources_interval"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    name: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    config: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    interval_minutes: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("15"))
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    @property
    def group_prefix(self) -> str:
        """Groups created by this source start with this text. Only they are managed by the sync."""
        return f"{self.kind.lower()}:{self.name}:"

    @property
    def external_key(self) -> str:
        """The value stored in documents.external_source for this source's documents."""
        return f"{self.kind.lower()}:{self.name}"


class SyncRun(Base):
    __tablename__ = "sync_runs"
    __table_args__ = (
        CheckConstraint("status in ('RUNNING','DONE','PARTIAL','FAILED')", name="ck_sync_runs_status"),
        CheckConstraint("trigger in ('SCHEDULE','MANUAL')", name="ck_sync_runs_trigger"),
        Index("ix_sync_runs_source_started", "source_id", "started_at"),
        Index("uq_sync_runs_one_running", "source_id", unique=True, postgresql_where=text("status = 'RUNNING'")),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    source_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sync_sources.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'RUNNING'"))
    trigger: Mapped[str] = mapped_column(Text, nullable=False)
    started_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    counts: Mapped[dict[str, int]] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    errors: Mapped[list[dict[str, str]]] = mapped_column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))  # first few: item id + code
    error_code: Mapped[str | None] = mapped_column(Text, nullable=True)  # a fixed code when the whole run stopped
