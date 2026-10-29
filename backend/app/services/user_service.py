"""Admin operations: users, roles, departments.

Reminder (blueprint 9.4): being an admin lets you MANAGE accounts. It does NOT
grant permission to read document content. That rule arrives with documents/ACL."""
import uuid
from datetime import timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.core.config import settings
from app.core.errors import AppError
from app.core.logging import security_event
from app.core.security import hash_password, new_opaque_token
from app.models import Department, Role, User
from app.models.user import user_roles
from app.schemas.users import RoleCreate, UserCreate, UserUpdate
from app.services import auth_service

ADMIN_ROLE = "system_admin"
DEFAULT_ROLE = "employee"


def not_found(what: str) -> AppError:
    return AppError(404, "Not Found", f"{what} not found.")


def _like_pattern(text: str) -> str:
    """A 'contains' pattern for LIKE where the person's own %, _ and backslash are plain characters, not wildcards."""
    escaped = text.lower().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


async def list_users(
    db: AsyncSession,
    limit: int,
    offset: int,
    q: str | None = None,
    department_id: int | None = None,
    is_active: bool | None = None,
    role: str | None = None,
) -> tuple[list[User], int]:
    """One page of people plus the number of ALL people that match (for 'x to y of total').
    q is a case-insensitive 'contains' search in the e-mail and the name; the filters are exact."""
    conditions = []
    if q and q.strip():
        pattern = _like_pattern(q.strip())
        conditions.append(or_(func.lower(User.email).like(pattern, escape="\\"), func.lower(User.full_name).like(pattern, escape="\\")))
    if department_id is not None:
        conditions.append(User.department_id == department_id)
    if is_active is not None:
        conditions.append(User.is_active.is_(is_active))
    if role:
        has_role = select(user_roles.c.user_id).join(Role, Role.id == user_roles.c.role_id).where(
            user_roles.c.user_id == User.id, Role.name == role
        )
        conditions.append(has_role.exists())
    total = await db.scalar(select(func.count()).select_from(User).where(*conditions)) or 0
    rows = await db.scalars(select(User).where(*conditions).order_by(User.email).limit(limit).offset(offset))
    return list(rows.unique()), int(total)


async def get_user(db: AsyncSession, user_id: uuid.UUID) -> User:
    user = await db.get(User, user_id)
    if user is None:
        raise not_found("User")
    return user


async def _roles_by_ids(db: AsyncSession, role_ids: list[int]) -> list[Role]:
    ids = set(role_ids)
    roles = list((await db.scalars(select(Role).where(Role.id.in_(ids)))).all()) if ids else []
    if len(roles) != len(ids):
        raise AppError(422, "Validation failed", "One or more roles do not exist.")
    return roles


async def _require_department(db: AsyncSession, department_id: int) -> None:
    if await db.get(Department, department_id) is None:
        raise AppError(422, "Validation failed", "Department does not exist.")


async def create_user(
    db: AsyncSession, data: UserCreate, actor: User, request_id: str | None
) -> tuple[User, str]:
    """Creates the account with a random unusable password and returns (user, raw invite token).
    The person sets their own password through the emailed link."""
    await _require_department(db, data.department_id)
    roles = await _roles_by_ids(db, data.role_ids)
    if not roles:
        default = await db.scalar(select(Role).where(Role.name == DEFAULT_ROLE))
        roles = [default] if default else []

    unusable = await run_in_threadpool(hash_password, new_opaque_token())
    user = User(
        email=data.email,
        full_name=data.full_name,
        password_hash=unusable,
        department_id=data.department_id,
        clearance_level=data.clearance_level,
        country=data.country,
        employment_type=data.employment_type,
    )
    user.roles = roles
    db.add(user)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise AppError(409, "Conflict", "A user with this email already exists.") from None
    raw = await auth_service.create_reset_token(
        db, user, timedelta(hours=settings.invite_token_hours)
    )
    await db.commit()
    await db.refresh(user)
    security_event("admin.user_created", request_id, actor_id=str(actor.id), user_id=str(user.id))
    return user, raw


async def update_user(
    db: AsyncSession, user_id: uuid.UUID, data: UserUpdate, actor: User, request_id: str | None
) -> User:
    user = await get_user(db, user_id)
    changes = data.model_dump(exclude_unset=True)
    if "department_id" in changes and changes["department_id"] is not None:
        await _require_department(db, changes["department_id"])
    if changes.get("is_active") is False and user.id == actor.id:
        raise AppError(400, "Not allowed", "You cannot deactivate your own account.")
    for field, value in changes.items():
        if value is not None:
            setattr(user, field, value)
    if changes.get("is_active") is False:
        await auth_service.revoke_all_sessions(db, user)
    await db.commit()
    await db.refresh(user)
    security_event(
        "admin.user_updated",
        request_id,
        actor_id=str(actor.id),
        user_id=str(user.id),
        fields=sorted(changes),
    )
    return user


async def deactivate_user(
    db: AsyncSession, user_id: uuid.UUID, actor: User, request_id: str | None
) -> User:
    if user_id == actor.id:
        raise AppError(400, "Not allowed", "You cannot deactivate your own account.")
    user = await get_user(db, user_id)
    user.is_active = False
    await auth_service.revoke_all_sessions(db, user)  # takes effect immediately (FR-03)
    await db.commit()
    await db.refresh(user)
    security_event("admin.user_deactivated", request_id, actor_id=str(actor.id), user_id=str(user.id))
    return user


async def set_user_roles(
    db: AsyncSession, user_id: uuid.UUID, role_ids: list[int], actor: User, request_id: str | None
) -> User:
    user = await get_user(db, user_id)
    roles = await _roles_by_ids(db, role_ids)
    if user.id == actor.id and ADMIN_ROLE not in {r.name for r in roles}:
        raise AppError(400, "Not allowed", "You cannot remove your own admin role.")
    user.roles = roles
    await db.commit()
    await db.refresh(user)
    security_event(
        "admin.roles_set",
        request_id,
        actor_id=str(actor.id),
        user_id=str(user.id),
        roles=sorted(r.name for r in roles),
    )
    return user


async def list_roles(db: AsyncSession) -> list[Role]:
    return list((await db.scalars(select(Role).order_by(Role.name))).all())


async def create_role(db: AsyncSession, data: RoleCreate) -> Role:
    role = Role(name=data.name, description=data.description)
    db.add(role)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise AppError(409, "Conflict", "A role with this name already exists.") from None
    return role


async def list_departments(db: AsyncSession) -> list[Department]:
    return list((await db.scalars(select(Department).order_by(Department.name))).all())

