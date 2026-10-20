"""Tables for Phase 4: groups, group membership, document access rules (ACL) and the history of rule changes.

Security reminders:
- Deny by default: a document with no matching ALLOW rule cannot be read by anybody.
- A matching DENY always beats any ALLOW.
- Chunks do NOT carry their own ACL: they inherit the rules of their document (blueprint 10.2)."""
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Index, Integer, Table, Text, Uuid, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

PRINCIPAL_TYPES = ("USER", "ROLE", "GROUP", "DEPARTMENT", "COMPANY")
EFFECTS = ("ALLOW", "DENY")
PERMISSIONS = ("READ", "DOWNLOAD", "MANAGE")


class Group(Base):
    __tablename__ = "groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


# Plain link table: which user belongs to which group.
user_groups = Table(
    "user_groups",
    Base.metadata,
    Column("user_id", Uuid, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("group_id", Integer, ForeignKey("groups.id", ondelete="CASCADE"), primary_key=True),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)


class DocumentAcl(Base):
    """One access rule on one document: WHO (principal) gets or loses WHICH permission, until WHEN.

    principal_id is text because it points at different kinds of rows (a user id, a role id, a group id,
    a department id) with no foreign key (blueprint 10.1: polymorphic). The service checks that the
    principal exists. COMPANY means "everybody" and has no principal_id."""

    __tablename__ = "document_acl"
    __table_args__ = (
        CheckConstraint("principal_type IN ('USER','ROLE','GROUP','DEPARTMENT','COMPANY')", name="ck_document_acl_principal_type"),
        CheckConstraint("effect IN ('ALLOW','DENY')", name="ck_document_acl_effect"),
        CheckConstraint("permission IN ('READ','DOWNLOAD','MANAGE')", name="ck_document_acl_permission"),
        CheckConstraint(
            "(principal_type = 'COMPANY' AND principal_id IS NULL) OR (principal_type <> 'COMPANY' AND principal_id IS NOT NULL)",
            name="ck_document_acl_principal_id",
        ),
        Index("ix_document_acl_document", "document_id"),
        Index("ix_document_acl_principal", "principal_type", "principal_id"),
        Index(
            "uq_document_acl_rule", "document_id", "principal_type", text("coalesce(principal_id, '')"), "effect", "permission",
            unique=True,
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()")
    )
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    principal_type: Mapped[str] = mapped_column(Text, nullable=False)
    principal_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    effect: Mapped[str] = mapped_column(Text, nullable=False)
    permission: Mapped[str] = mapped_column(Text, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    granted_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class PermissionChangeEvent(Base):
    """History of rule changes on a document: the full rule list before and after (never document text)."""

    __tablename__ = "permission_change_events"
    __table_args__ = (Index("ix_permission_change_events_document", "document_id", "changed_at"),)

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()")
    )
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    prev_acl: Mapped[Any] = mapped_column(JSONB, nullable=False)
    new_acl: Mapped[Any] = mapped_column(JSONB, nullable=False)
    changed_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
