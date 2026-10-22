"""Dashboards (Phase 7C): the admin overview, the knowledge gaps report and suggested questions.

- Overview: system_admin only. Counts and times, nothing about people or text.
- Knowledge gaps: system_admin and security_admin. The questions nobody could get an answer to, masked and counted.
- Suggested questions: any signed-in person; built only from documents that person may read."""
from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_admin
from app.core.errors import AppError
from app.dashboards import service
from app.db.session import get_db
from app.models import User

router = APIRouter(tags=["dashboards"])
GAP_ROLES = {"system_admin", "security_admin"}


async def require_gap_viewer(user: User = Depends(get_current_user)) -> User:
    if not GAP_ROLES & set(user.role_names):
        raise AppError(403, "Forbidden", "You do not have permission to do this.")
    return user


@router.get("/dashboards/admin-overview")
async def admin_overview(response: Response, _: User = Depends(require_admin), db: AsyncSession = Depends(get_db)) -> dict:  # type: ignore[type-arg]
    response.headers["Cache-Control"] = "no-store"
    return await service.admin_overview(db)


@router.get("/dashboards/knowledge-gaps")
async def knowledge_gaps(response: Response, _: User = Depends(require_gap_viewer), db: AsyncSession = Depends(get_db)) -> dict:  # type: ignore[type-arg]
    response.headers["Cache-Control"] = "no-store"
    return {"window_days": service.GAP_WINDOW_DAYS, "items": await service.knowledge_gaps(db)}


@router.get("/me/suggested-questions")
async def suggested_questions(response: Response, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:  # type: ignore[type-arg]
    response.headers["Cache-Control"] = "no-store"
    return {"items": await service.suggested_questions(db, user.id)}
