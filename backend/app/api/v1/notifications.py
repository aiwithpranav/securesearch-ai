"""In-app notifications (FR-33), for example "ingestion failed". Each person sees only their own.
These two routes are an additive extension of the API contract (CR-002)."""
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import User
from app.schemas.documents import NotificationOut
from app.services import document_service as svc

router = APIRouter(tags=["notifications"])


@router.get("/notifications", response_model=list[NotificationOut])
async def list_notifications(
    limit: int = Query(50, ge=1, le=100),
    unread_only: bool = Query(False),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[object]:
    return await svc.list_notifications(db, user, limit, unread_only)  # type: ignore[return-value]


@router.post("/notifications/{notification_id}/read", response_model=NotificationOut)
async def mark_read(
    notification_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> object:
    return await svc.mark_notification_read(db, user, notification_id)
