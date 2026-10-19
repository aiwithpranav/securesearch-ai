import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.core import mailer
from app.db.session import get_db
from app.models import User
from app.schemas.users import RoleAssign, RoleCreate, RoleOut, UserCreate, UserOut, UserUpdate, DepartmentOut
from app.services import user_service

# Every route here needs the system_admin role (checked on the server, from the database).
router = APIRouter(tags=["admin"], dependencies=[Depends(require_admin)])


def _rid(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


@router.get("/users")
async def list_users(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    users, total = await user_service.list_users(db, limit, offset)
    return {
        "items": [UserOut.model_validate(u) for u in users],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.post("/users", status_code=status.HTTP_201_CREATED, response_model=UserOut)
async def create_user(
    body: UserCreate,
    request: Request,
    background: BackgroundTasks,
    actor: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> User:
    user, raw = await user_service.create_user(db, body, actor, _rid(request))
    background.add_task(mailer.send_invite_email, user.email, user.full_name, raw)
    return user


@router.get("/users/{user_id}", response_model=UserOut)
async def get_user(user_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> User:
    return await user_service.get_user(db, user_id)


@router.patch("/users/{user_id}", response_model=UserOut)
async def update_user(
    user_id: uuid.UUID,
    body: UserUpdate,
    request: Request,
    actor: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> User:
    return await user_service.update_user(db, user_id, body, actor, _rid(request))


@router.post("/users/{user_id}/deactivate", response_model=UserOut)
async def deactivate_user(
    user_id: uuid.UUID,
    request: Request,
    actor: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> User:
    return await user_service.deactivate_user(db, user_id, actor, _rid(request))


@router.post("/users/{user_id}/roles", response_model=UserOut)
async def set_user_roles(
    user_id: uuid.UUID,
    body: RoleAssign,
    request: Request,
    actor: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> User:
    return await user_service.set_user_roles(db, user_id, body.role_ids, actor, _rid(request))


@router.get("/roles", response_model=list[RoleOut])
async def list_roles(db: AsyncSession = Depends(get_db)) -> list[object]:
    return await user_service.list_roles(db)  # type: ignore[return-value]


@router.post("/roles", status_code=status.HTTP_201_CREATED, response_model=RoleOut)
async def create_role(body: RoleCreate, db: AsyncSession = Depends(get_db)) -> object:
    return await user_service.create_role(db, body)


@router.get("/departments", response_model=list[DepartmentOut])
async def list_departments(db: AsyncSession = Depends(get_db)) -> list[object]:
    return await user_service.list_departments(db)  # type: ignore[return-value]
