"""Groups, document access rules, rule history and the access preview.

Rules for this module (ADR 027):
- A principal must really exist when a rule is created (the database has no foreign key for it).
- Expiry must lie in the future when it is set.
- Every change to a document's rules writes a history row (full list before and after) in the SAME
  transaction. If either fails, neither is saved.
- Nothing here returns document text."""
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.access import resolver as r
from app.core.errors import AppError
from app.core.logging import security_event
from app.models import Department, Document, DocumentAcl, Group, PermissionChangeEvent, Role, SyncSource, User, user_groups
from app.schemas.access import (
    AclOut, DecisionOut, GroupDetail, GroupOut, HistoryOut, MemberOut, PreviewOut, PreviewUser,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def not_found(what: str) -> AppError:
    return AppError(404, "Not Found", f"{what} not found.")


# ------------------------------------------------------------------ principals

async def _principal_names(db: AsyncSession, rules: list[DocumentAcl]) -> dict[tuple[str, str | None], str]:
    """Readable names for the principals of these rules (one query per kind)."""
    names: dict[tuple[str, str | None], str] = {("COMPANY", None): "Everyone"}
    ids = {t: {x.principal_id for x in rules if x.principal_type == t and x.principal_id} for t in ("USER", "ROLE", "GROUP", "DEPARTMENT")}
    if ids["USER"]:
        for u in (await db.scalars(select(User).where(User.id.in_([uuid.UUID(i) for i in ids["USER"]])))).all():
            names[("USER", str(u.id))] = f"{u.full_name} ({u.email})"
    for kind, model in (("ROLE", Role), ("GROUP", Group), ("DEPARTMENT", Department)):
        if ids[kind]:
            for row in (await db.scalars(select(model).where(model.id.in_([int(i) for i in ids[kind]])))).all():
                names[(kind, str(row.id))] = row.name
    return names


async def _check_principal(db: AsyncSession, ptype: str, pid: str | None) -> str | None:
    """Returns the normalised principal id, or raises 422 if it does not exist or is malformed."""
    if ptype == "COMPANY":
        if pid not in (None, ""):
            raise AppError(422, "Validation failed", "COMPANY rules must not name a principal.")
        return None
    if not pid:
        raise AppError(422, "Validation failed", "A principal id is required for this rule type.")
    try:
        if ptype == "USER":
            uid = uuid.UUID(pid)
            exists = await db.scalar(select(func.count()).select_from(User).where(User.id == uid))
            pid = str(uid)
        else:
            num = int(pid)
            model = {"ROLE": Role, "GROUP": Group, "DEPARTMENT": Department}[ptype]
            exists = await db.scalar(select(func.count()).select_from(model).where(model.id == num))
            pid = str(num)
    except ValueError:
        raise AppError(422, "Validation failed", "The principal id is not valid for this rule type.") from None
    if not exists:
        raise AppError(422, "Validation failed", f"The {ptype.lower()} does not exist.")
    return pid


def _aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _check_expiry(dt: datetime | None) -> datetime | None:
    dt = _aware(dt)
    if dt is not None and dt <= _now():
        raise AppError(422, "Validation failed", "The expiry must be in the future.")
    return dt


# ------------------------------------------------------------------ rules

def _to_out(rule: DocumentAcl, names: dict[tuple[str, str | None], str]) -> AclOut:
    return AclOut(
        id=rule.id, principal_type=rule.principal_type, principal_id=rule.principal_id,  # type: ignore[arg-type]
        principal_name=names.get((rule.principal_type, rule.principal_id), "(removed)"),
        effect=rule.effect, permission=rule.permission,  # type: ignore[arg-type]
        expires_at=rule.expires_at, expired=rule.expires_at is not None and rule.expires_at <= _now(),
        granted_by=rule.granted_by, created_at=rule.created_at,
    )


async def _rules(db: AsyncSession, document_id: uuid.UUID) -> list[DocumentAcl]:
    rows = await db.scalars(
        select(DocumentAcl).where(DocumentAcl.document_id == document_id).order_by(DocumentAcl.created_at, DocumentAcl.id)
    )
    return list(rows.all())


async def list_rules(db: AsyncSession, document_id: uuid.UUID) -> list[AclOut]:
    rules = await _rules(db, document_id)
    names = await _principal_names(db, rules)
    return [_to_out(x, names) for x in rules]


async def _snapshot(db: AsyncSession, document_id: uuid.UUID) -> list[dict[str, Any]]:
    rules = await _rules(db, document_id)
    names = await _principal_names(db, rules)
    return [
        {
            "id": str(x.id), "principal_type": x.principal_type, "principal_id": x.principal_id,
            "principal_name": names.get((x.principal_type, x.principal_id), "(removed)"),
            "effect": x.effect, "permission": x.permission,
            "expires_at": x.expires_at.isoformat() if x.expires_at else None,
        }
        for x in rules
    ]


async def _record(db: AsyncSession, actor: User, document_id: uuid.UUID, before: list[dict[str, Any]]) -> None:
    after = await _snapshot(db, document_id)
    db.add(PermissionChangeEvent(document_id=document_id, prev_acl=before, new_acl=after, changed_by=actor.id))


async def add_rule(db: AsyncSession, actor: User, document_id: uuid.UUID, body, request_id: str | None) -> AclOut:  # type: ignore[no-untyped-def]
    pid = await _check_principal(db, body.principal_type, body.principal_id)
    expires = _check_expiry(body.expires_at)
    before = await _snapshot(db, document_id)
    rule = DocumentAcl(
        document_id=document_id, principal_type=body.principal_type, principal_id=pid, effect=body.effect,
        permission=body.permission, expires_at=expires, granted_by=actor.id,
    )
    db.add(rule)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise AppError(409, "Conflict", "This rule already exists.") from None
    await _record(db, actor, document_id, before)
    await db.commit()
    security_event(
        "admin.acl_rule_added", request_id, actor_id=str(actor.id), document_id=str(document_id),
        rule_id=str(rule.id), principal_type=body.principal_type, effect=body.effect, permission=body.permission,
    )
    return (await list_one(db, document_id, rule.id))


async def list_one(db: AsyncSession, document_id: uuid.UUID, rule_id: uuid.UUID) -> AclOut:
    rule = await db.get(DocumentAcl, rule_id)
    if rule is None or rule.document_id != document_id:
        raise not_found("Rule")
    return _to_out(rule, await _principal_names(db, [rule]))


async def update_rule(
    db: AsyncSession, actor: User, document_id: uuid.UUID, rule_id: uuid.UUID, changes: dict[str, Any], request_id: str | None
) -> AclOut:
    rule = await db.get(DocumentAcl, rule_id)
    if rule is None or rule.document_id != document_id:
        raise not_found("Rule")
    if "effect" in changes and changes["effect"] is None or "permission" in changes and changes["permission"] is None:
        raise AppError(422, "Validation failed", "Effect and permission cannot be empty.")
    if "expires_at" in changes:
        changes["expires_at"] = _check_expiry(changes["expires_at"])
    before = await _snapshot(db, document_id)
    for field, value in changes.items():
        setattr(rule, field, value)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise AppError(409, "Conflict", "An identical rule already exists.") from None
    await _record(db, actor, document_id, before)
    await db.commit()
    security_event(
        "admin.acl_rule_updated", request_id, actor_id=str(actor.id), document_id=str(document_id),
        rule_id=str(rule_id), fields=sorted(changes),
    )
    return await list_one(db, document_id, rule_id)


async def delete_rule(db: AsyncSession, actor: User, document_id: uuid.UUID, rule_id: uuid.UUID, request_id: str | None) -> None:
    rule = await db.get(DocumentAcl, rule_id)
    if rule is None or rule.document_id != document_id:
        raise not_found("Rule")
    before = await _snapshot(db, document_id)
    await db.execute(delete(DocumentAcl).where(DocumentAcl.id == rule_id))
    await _record(db, actor, document_id, before)
    await db.commit()
    security_event("admin.acl_rule_deleted", request_id, actor_id=str(actor.id), document_id=str(document_id), rule_id=str(rule_id))


async def history(db: AsyncSession, document_id: uuid.UUID, limit: int) -> list[HistoryOut]:
    events = (await db.scalars(
        select(PermissionChangeEvent).where(PermissionChangeEvent.document_id == document_id)
        .order_by(PermissionChangeEvent.changed_at.desc(), PermissionChangeEvent.id).limit(limit)
    )).all()
    users = {u.id: u for u in (await db.scalars(select(User).where(User.id.in_({e.changed_by for e in events if e.changed_by})))).all()} if events else {}
    return [
        HistoryOut(
            id=e.id, changed_at=e.changed_at, prev_acl=e.prev_acl, new_acl=e.new_acl,
            changed_by=MemberOut(id=users[e.changed_by].id, email=users[e.changed_by].email, full_name=users[e.changed_by].full_name)
            if e.changed_by in users else None,
        )
        for e in events
    ]


# ------------------------------------------------------------------ preview

async def preview(db: AsyncSession, document_id: uuid.UUID, user_id: uuid.UUID) -> PreviewOut:
    """Why can (or can't) this user read, download or manage this document? Codes and matching rules only."""
    user = await db.get(User, user_id)
    doc = await db.get(Document, document_id)
    if user is None:
        raise not_found("User")
    if doc is None:
        raise not_found("Document")
    decisions = {p: await r.aexplain(db, user_id, document_id, p) for p in (r.READ, r.DOWNLOAD, r.MANAGE)}
    rule_ids: set[uuid.UUID] = set()
    for p in (r.READ, r.DOWNLOAD, r.MANAGE):
        rule_ids |= set((await db.scalars(r.matching_rules_stmt(user_id, document_id, p))).all())
    rules = [x for x in await _rules(db, document_id) if x.id in rule_ids]
    names = await _principal_names(db, rules)
    return PreviewOut(
        user=PreviewUser(
            id=user.id, email=user.email, full_name=user.full_name, department=user.department,  # type: ignore[arg-type]
            clearance_level=user.clearance_level, country=user.country, is_active=user.is_active, roles=user.role_names,
        ),
        document_status=doc.status, sensitivity_level=doc.sensitivity_level, allowed_countries=doc.allowed_countries,
        read=DecisionOut(allowed=decisions[r.READ].allowed, code=decisions[r.READ].code),
        download=DecisionOut(allowed=decisions[r.DOWNLOAD].allowed, code=decisions[r.DOWNLOAD].code),
        manage=DecisionOut(allowed=decisions[r.MANAGE].allowed, code=decisions[r.MANAGE].code),
        matching_rules=[_to_out(x, names) for x in rules],
    )


# ------------------------------------------------------------------ groups

async def list_groups(db: AsyncSession) -> list[GroupOut]:
    counts = dict((await db.execute(select(user_groups.c.group_id, func.count()).group_by(user_groups.c.group_id))).all())
    groups = (await db.scalars(select(Group).order_by(Group.name))).all()
    return [GroupOut(id=g.id, name=g.name, description=g.description, member_count=int(counts.get(g.id, 0))) for g in groups]


async def get_group(db: AsyncSession, group_id: int) -> GroupDetail:
    g = await db.get(Group, group_id)
    if g is None:
        raise not_found("Group")
    members = (await db.scalars(
        select(User).join(user_groups, user_groups.c.user_id == User.id).where(user_groups.c.group_id == group_id).order_by(User.full_name)
    )).all()
    return GroupDetail(
        id=g.id, name=g.name, description=g.description, member_count=len(members),
        members=[MemberOut(id=u.id, email=u.email, full_name=u.full_name) for u in members],
    )


async def create_group(db: AsyncSession, actor: User, name: str, description: str | None, request_id: str | None) -> GroupOut:
    group = Group(name=name.strip(), description=description)
    db.add(group)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise AppError(409, "Conflict", "A group with this name already exists.") from None
    security_event("admin.group_created", request_id, actor_id=str(actor.id), group_id=group.id)
    return GroupOut(id=group.id, name=group.name, description=group.description, member_count=0)


async def _refuse_if_managed(db: AsyncSession, group: Group) -> None:
    """Teams created by a sync source follow the source. Editing them by hand would be undone at the next sync."""
    managed = await db.scalar(
        select(func.count()).select_from(SyncSource).where(func.starts_with(group.name, func.lower(SyncSource.kind) + ":" + SyncSource.name + ":"))
    )
    if managed:
        raise AppError(409, "Conflict", "This team is managed by a sync source. Change it in the source.")


async def add_member(db: AsyncSession, actor: User, group_id: int, user_id: uuid.UUID, request_id: str | None) -> GroupDetail:
    group = await db.get(Group, group_id)
    if group is None:
        raise not_found("Group")
    await _refuse_if_managed(db, group)
    if await db.get(User, user_id) is None:
        raise AppError(422, "Validation failed", "The user does not exist.")
    already = await db.scalar(
        select(func.count()).select_from(user_groups).where(user_groups.c.group_id == group_id, user_groups.c.user_id == user_id)
    )
    if not already:
        await db.execute(user_groups.insert().values(user_id=user_id, group_id=group_id))
        await db.commit()
        security_event("admin.group_member_added", request_id, actor_id=str(actor.id), group_id=group_id, user_id=str(user_id))
    return await get_group(db, group_id)


async def remove_member(db: AsyncSession, actor: User, group_id: int, user_id: uuid.UUID, request_id: str | None) -> None:
    group = await db.get(Group, group_id)
    if group is None:
        raise not_found("Group")
    await _refuse_if_managed(db, group)
    result = await db.execute(
        delete(user_groups).where(user_groups.c.group_id == group_id, user_groups.c.user_id == user_id)
    )
    await db.commit()
    if result.rowcount:  # type: ignore[attr-defined]
        security_event("admin.group_member_removed", request_id, actor_id=str(actor.id), group_id=group_id, user_id=str(user_id))
