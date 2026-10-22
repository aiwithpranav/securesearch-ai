"""THE access resolver: the single place that decides who may read, download or manage a document.

Everything is decided in SQL, per request, from the database as it is RIGHT NOW. Nothing is cached and
nothing is read from the login token (the token carries only the user id), so a removed group
membership, a changed department or an expired rule takes effect on the very next call.

READ rules (blueprint 9.2). A document may be read only if ALL of these hold:
  user   the user exists and is active
  A      the document is not deleted and its status is READY
  B      NO matching DENY rule exists            (deny wins)
  C      a matching, unexpired ALLOW rule exists (deny by default: no rule means no access)
  D      user.clearance_level >= document.sensitivity_level
  E      document.allowed_countries is empty (NULL) or contains user.country

A rule "matches" a user when its principal is: the user, one of the user's roles, one of the user's
groups, the user's department, or COMPANY (everybody). An expired rule is ignored (ALLOW or DENY).

DOWNLOAD = everything READ needs, AND an unexpired ALLOW DOWNLOAD rule, AND no matching DENY DOWNLOAD.
MANAGE   = may edit the document's metadata and rules. It does NOT imply READ and is not limited by
           clearance or country. Needs a not-deleted document (any status, so failed uploads can be
           fixed) and either the system_admin role (implicit, cannot be locked out by a DENY, so there
           is always someone who can repair the rules) or an ALLOW MANAGE rule without a matching DENY MANAGE.
           Being system_admin NEVER gives READ.

Two kinds of entry points use the same rule pieces, so they cannot disagree:
  readable_ids_stmt / manageable_ids_stmt  -> the allow-list (a SELECT of document ids)
  decision_steps                           -> the same checks one by one, to explain a decision
"""
import uuid
from dataclasses import dataclass

from sqlalchemy import ColumnElement, Select, String, and_, any_, cast, exists, func, literal, not_, or_, select
from sqlalchemy.orm import aliased

from app.models import Document, DocumentAcl, Role, User, user_groups, user_roles
from app.models import document as dm

READ, DOWNLOAD, MANAGE = "READ", "DOWNLOAD", "MANAGE"
ADMIN_ROLE = "system_admin"

# Decision codes (stable words, safe to show to administrators)
ALLOWED = "ALLOWED"
USER_INACTIVE = "USER_INACTIVE"
DOCUMENT_UNAVAILABLE = "DOCUMENT_UNAVAILABLE"
DENIED_BY_RULE = "DENIED_BY_RULE"
NO_ALLOW_RULE = "NO_ALLOW_RULE"
CLEARANCE_TOO_LOW = "CLEARANCE_TOO_LOW"
COUNTRY_NOT_ALLOWED = "COUNTRY_NOT_ALLOWED"
ADMIN_IMPLICIT = "ADMIN_IMPLICIT"


# --------------------------------------------------------------------------- rule pieces

def _user_value(user_id: uuid.UUID, column) -> ColumnElement:  # type: ignore[no-untyped-def]
    return select(column).where(User.id == user_id).scalar_subquery()


def _matches_user(acl, user_id: uuid.UUID) -> ColumnElement[bool]:  # type: ignore[no-untyped-def]
    """True when the rule's principal is this user, one of their roles or groups, their department, or everybody."""
    return or_(
        and_(acl.principal_type == "USER", acl.principal_id == str(user_id)),
        and_(
            acl.principal_type == "ROLE",
            acl.principal_id.in_(select(cast(user_roles.c.role_id, String)).where(user_roles.c.user_id == user_id)),
        ),
        and_(
            acl.principal_type == "GROUP",
            acl.principal_id.in_(select(cast(user_groups.c.group_id, String)).where(user_groups.c.user_id == user_id)),
        ),
        and_(acl.principal_type == "DEPARTMENT", acl.principal_id == _user_value(user_id, cast(User.department_id, String))),
        acl.principal_type == "COMPANY",
    )


def _rule_exists(user_id: uuid.UUID, permission: str, effect: str) -> ColumnElement[bool]:
    """EXISTS a matching, unexpired rule of this effect and permission on the outer Document row."""
    acl = aliased(DocumentAcl)
    return exists().where(
        acl.document_id == Document.id,
        acl.effect == effect,
        acl.permission == permission,
        or_(acl.expires_at.is_(None), acl.expires_at > func.now()),
        _matches_user(acl, user_id),
    )


def user_is_active(user_id: uuid.UUID) -> ColumnElement[bool]:
    return exists().where(User.id == user_id, User.is_active.is_(True))


def _is_admin(user_id: uuid.UUID) -> ColumnElement[bool]:
    return exists().where(
        user_roles.c.user_id == user_id, user_roles.c.role_id == Role.id, Role.name == ADMIN_ROLE,
    )


def _document_readable_state() -> ColumnElement[bool]:  # rule A
    return and_(Document.deleted_at.is_(None), Document.status == dm.READY)


def _clearance_ok(user_id: uuid.UUID) -> ColumnElement[bool]:  # rule D
    return Document.sensitivity_level <= _user_value(user_id, User.clearance_level)


def _country_ok(user_id: uuid.UUID) -> ColumnElement[bool]:  # rule E
    return or_(
        Document.allowed_countries.is_(None),
        _user_value(user_id, User.country) == any_(Document.allowed_countries),
    )


def _no_deny(user_id: uuid.UUID, permission: str) -> ColumnElement[bool]:  # rule B
    return not_(_rule_exists(user_id, permission, "DENY"))


def _has_allow(user_id: uuid.UUID, permission: str) -> ColumnElement[bool]:  # rule C
    return _rule_exists(user_id, permission, "ALLOW")


# --------------------------------------------------------------------------- the allow-lists

def _read_conditions(user_id: uuid.UUID) -> list[ColumnElement[bool]]:
    return [
        user_is_active(user_id),
        _document_readable_state(),
        _no_deny(user_id, READ),
        _has_allow(user_id, READ),
        _clearance_ok(user_id),
        _country_ok(user_id),
    ]


def count_readable(session, user_id: uuid.UUID) -> int:  # type: ignore[no-untyped-def]
    """How many documents this person may READ (for the audit log and the progress view)."""
    return session.scalar(select(func.count()).select_from(readable_ids_stmt(user_id).subquery())) or 0


def readable_ids_stmt(user_id: uuid.UUID) -> Select:  # type: ignore[type-arg]
    """SELECT of the ids of every document this user may READ (chunks of other documents never leave the database)."""
    return select(Document.id).where(*_read_conditions(user_id))


def downloadable_ids_stmt(user_id: uuid.UUID) -> Select:  # type: ignore[type-arg]
    return select(Document.id).where(
        *_read_conditions(user_id), _no_deny(user_id, DOWNLOAD), _has_allow(user_id, DOWNLOAD)
    )


def _manage_conditions(user_id: uuid.UUID) -> list[ColumnElement[bool]]:
    return [
        user_is_active(user_id),
        Document.deleted_at.is_(None),
        or_(_is_admin(user_id), and_(_no_deny(user_id, MANAGE), _has_allow(user_id, MANAGE))),
    ]


def manageable_ids_stmt(user_id: uuid.UUID) -> Select:  # type: ignore[type-arg]
    return select(Document.id).where(*_manage_conditions(user_id))


def ids_stmt(user_id: uuid.UUID, permission: str) -> Select:  # type: ignore[type-arg]
    return {READ: readable_ids_stmt, DOWNLOAD: downloadable_ids_stmt, MANAGE: manageable_ids_stmt}[permission](user_id)


def check_stmt(user_id: uuid.UUID, document_id: uuid.UUID, permission: str) -> Select:  # type: ignore[type-arg]
    """One document: returns a row only if the permission is granted."""
    return select(literal(1)).where(
        Document.id == document_id,
        Document.id.in_(ids_stmt(user_id, permission).correlate(None)),  # the inner SELECT keeps its own FROM
    )


# --------------------------------------------------------------------------- explanations

@dataclass(frozen=True)
class Decision:
    allowed: bool
    code: str  # ALLOWED or the first rule that failed


def decision_steps(user_id: uuid.UUID, document_id: uuid.UUID, permission: str) -> list[tuple[str, Select]]:  # type: ignore[type-arg]
    """The same rule pieces as the allow-list, as separate checks in order. Each SELECT returns a row when the
    step PASSES. The first step that returns nothing explains the denial."""

    def step(code: str, condition: ColumnElement[bool]) -> tuple[str, Select]:  # type: ignore[type-arg]
        return code, select(literal(1)).where(Document.id == document_id, condition)

    steps = [step(USER_INACTIVE, user_is_active(user_id))]
    if permission == MANAGE:
        steps.append(step(DOCUMENT_UNAVAILABLE, Document.deleted_at.is_(None)))
        steps.append(step(DENIED_BY_RULE, or_(_is_admin(user_id), _no_deny(user_id, MANAGE))))
        steps.append(step(NO_ALLOW_RULE, or_(_is_admin(user_id), _has_allow(user_id, MANAGE))))
        return steps
    steps += [
        step(DOCUMENT_UNAVAILABLE, _document_readable_state()),
        step(DENIED_BY_RULE, _no_deny(user_id, READ)),
        step(NO_ALLOW_RULE, _has_allow(user_id, READ)),
        step(CLEARANCE_TOO_LOW, _clearance_ok(user_id)),
        step(COUNTRY_NOT_ALLOWED, _country_ok(user_id)),
    ]
    if permission == DOWNLOAD:
        steps.append(step(DENIED_BY_RULE, _no_deny(user_id, DOWNLOAD)))
        steps.append(step(NO_ALLOW_RULE, _has_allow(user_id, DOWNLOAD)))
    return steps


def matching_rules_stmt(user_id: uuid.UUID, document_id: uuid.UUID, permission: str) -> Select:  # type: ignore[type-arg]
    """Ids of the unexpired rules (ALLOW and DENY) of this permission that match the user on this document."""
    acl = aliased(DocumentAcl)
    return select(acl.id).where(
        acl.document_id == document_id,
        acl.permission == permission,
        or_(acl.expires_at.is_(None), acl.expires_at > func.now()),
        _matches_user(acl, user_id),
    )


# --------------------------------------------------------------------------- executors

def can(session, user_id: uuid.UUID, document_id: uuid.UUID, permission: str = READ) -> bool:  # type: ignore[no-untyped-def]
    """Synchronous check (worker, scripts, tests)."""
    return session.scalar(check_stmt(user_id, document_id, permission)) is not None


async def acan(db, user_id: uuid.UUID, document_id: uuid.UUID, permission: str = READ) -> bool:  # type: ignore[no-untyped-def]
    """Asynchronous check (API routes)."""
    return (await db.scalar(check_stmt(user_id, document_id, permission))) is not None


def allowed_ids(session, user_id: uuid.UUID, permission: str = READ) -> set[uuid.UUID]:  # type: ignore[no-untyped-def]
    return set(session.scalars(ids_stmt(user_id, permission)).all())


def explain(session, user_id: uuid.UUID, document_id: uuid.UUID, permission: str = READ) -> Decision:  # type: ignore[no-untyped-def]
    for code, stmt in decision_steps(user_id, document_id, permission):
        if session.scalar(stmt) is None:
            return Decision(False, code)
    return Decision(True, ALLOWED)


async def aexplain(db, user_id: uuid.UUID, document_id: uuid.UUID, permission: str = READ) -> Decision:  # type: ignore[no-untyped-def]
    for code, stmt in decision_steps(user_id, document_id, permission):
        if (await db.scalar(stmt)) is None:
            return Decision(False, code)
    return Decision(True, ALLOWED)
