"""API for groups and document access rules (Phase 4B).

Who may call what:
- Groups: system_admin only.
- Rules, rule history, access preview and editing a document's metadata: anybody who may MANAGE that
  document (a system_admin, or a user with an ALLOW MANAGE rule and no DENY MANAGE). Anybody else gets
  "Document not found" (404) so the answer never reveals whether the document exists.
MANAGE never means READ: nothing here returns document text."""
import uuid

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.access import acan
from app.access.resolver import MANAGE
from app.api.deps import get_current_user, require_admin
from app.core.errors import AppError
from app.db.session import get_db
from app.models import User
from app.schemas.access import (
    AclCreate,
    AclOut,
    AclPatch,
    GroupCreate,
    GroupDetail,
    GroupOut,
    HistoryOut,
    MemberAdd,
    PreviewOut,
)
from app.schemas.documents import DocumentOut, DocumentUpdate
from app.services import access_service as svc
from app.services import document_service as docs

groups_router = APIRouter(tags=["groups"], dependencies=[Depends(require_admin)])
manage_router = APIRouter(tags=["access"])


def _rid(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


async def require_manage(
    document_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> User:
    """The caller must be allowed to MANAGE this document. Otherwise: 404 (same as a missing document)."""
    if not await acan(db, user.id, document_id, MANAGE):
        raise AppError(404, "Not Found", "Document not found.")
    return user


# ------------------------------------------------------------------ groups (admin)

@groups_router.get("/groups", response_model=list[GroupOut])
async def list_groups(db: AsyncSession = Depends(get_db)) -> list[GroupOut]:
    return await svc.list_groups(db)


@groups_router.post("/groups", status_code=status.HTTP_201_CREATED, response_model=GroupOut)
async def create_group(
    body: GroupCreate, request: Request, actor: User = Depends(require_admin), db: AsyncSession = Depends(get_db)
) -> GroupOut:
    return await svc.create_group(db, actor, body.name, body.description, _rid(request))


@groups_router.get("/groups/{group_id}", response_model=GroupDetail)
async def get_group(group_id: int, db: AsyncSession = Depends(get_db)) -> GroupDetail:
    return await svc.get_group(db, group_id)


@groups_router.post("/groups/{group_id}/members", response_model=GroupDetail)
async def add_member(
    group_id: int, body: MemberAdd, request: Request, actor: User = Depends(require_admin), db: AsyncSession = Depends(get_db)
) -> GroupDetail:
    return await svc.add_member(db, actor, group_id, body.user_id, _rid(request))


@groups_router.delete("/groups/{group_id}/members", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    group_id: int,
    request: Request,
    user_id: uuid.UUID = Query(...),
    actor: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> None:
    await svc.remove_member(db, actor, group_id, user_id, _rid(request))


# ------------------------------------------------------------------ rules (MANAGE holders)

@manage_router.get("/documents/{document_id}/acl", response_model=list[AclOut])
async def list_rules(document_id: uuid.UUID, _: User = Depends(require_manage), db: AsyncSession = Depends(get_db)) -> list[AclOut]:
    return await svc.list_rules(db, document_id)


@manage_router.post("/documents/{document_id}/acl", status_code=status.HTTP_201_CREATED, response_model=AclOut)
async def add_rule(
    document_id: uuid.UUID, body: AclCreate, request: Request,
    actor: User = Depends(require_manage), db: AsyncSession = Depends(get_db),
) -> AclOut:
    return await svc.add_rule(db, actor, document_id, body, _rid(request))


@manage_router.patch("/documents/{document_id}/acl/{rule_id}", response_model=AclOut)
async def update_rule(
    document_id: uuid.UUID, rule_id: uuid.UUID, body: AclPatch, request: Request,
    actor: User = Depends(require_manage), db: AsyncSession = Depends(get_db),
) -> AclOut:
    return await svc.update_rule(db, actor, document_id, rule_id, body.model_dump(exclude_unset=True), _rid(request))


@manage_router.delete("/documents/{document_id}/acl/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rule(
    document_id: uuid.UUID, rule_id: uuid.UUID, request: Request,
    actor: User = Depends(require_manage), db: AsyncSession = Depends(get_db),
) -> None:
    await svc.delete_rule(db, actor, document_id, rule_id, _rid(request))


@manage_router.get("/documents/{document_id}/acl/history", response_model=list[HistoryOut])
async def rule_history(
    document_id: uuid.UUID, limit: int = Query(50, ge=1, le=200),
    _: User = Depends(require_manage), db: AsyncSession = Depends(get_db),
) -> list[HistoryOut]:
    return await svc.history(db, document_id, limit)


@manage_router.get("/documents/{document_id}/access-preview", response_model=PreviewOut)
async def access_preview(
    document_id: uuid.UUID, user_id: uuid.UUID = Query(...),
    _: User = Depends(require_manage), db: AsyncSession = Depends(get_db),
) -> PreviewOut:
    return await svc.preview(db, document_id, user_id)


# ------------------------------------------------------------------ metadata edit (MANAGE holders)

@manage_router.patch("/documents/{document_id}", response_model=DocumentOut)
async def update_document(
    document_id: uuid.UUID, body: DocumentUpdate, request: Request,
    actor: User = Depends(require_manage), db: AsyncSession = Depends(get_db),
) -> DocumentOut:
    """Moved here from the admin-only router: editing metadata needs MANAGE on the document, not the admin role."""
    return await docs.update_document(db, document_id, body.model_dump(exclude_unset=True), actor, _rid(request))
