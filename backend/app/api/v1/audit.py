"""Audit API (Phase 7A): who asked what, what happened, and what administrators changed.

Security rules:
- Only the roles security_admin and auditor may call these routes. system_admin may NOT: administrators manage the
  system, they do not audit themselves ("admin is not auditor", like "admin is not reader").
- The question text is shown here (auditors need it) and nowhere else beyond the person's own history.
- The log contains no answer text and no document text; this API cannot return what is not stored.
- Exporting is itself recorded (who, when) before any data is sent."""
import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.audit import service as audit
from app.core.errors import AppError
from app.db.session import get_db
from app.models import AccessEvent, AnswerAuditLog, User
from app.schemas.audit import (
    AccessEventOut,
    AccessEventPage,
    AnswerAuditOut,
    AnswerAuditPage,
    PersonRef,
    QueryAuditOut,
    QueryAuditPage,
)

AUDIT_ROLES = {"security_admin", "auditor"}
PAGE_MAX = 200
EXPORT_MAX = 10_000

router = APIRouter(prefix="/audit", tags=["audit"])


async def require_auditor(user: User = Depends(get_current_user)) -> User:
    if not AUDIT_ROLES & set(user.role_names):
        raise AppError(403, "Forbidden", "You do not have permission to do this.")
    return user


Auditor = Annotated[User, Depends(require_auditor)]
Page = Annotated[int, Query(ge=1)]


async def _people(db: AsyncSession, ids: set[uuid.UUID | None]) -> dict[uuid.UUID, PersonRef]:
    wanted = {i for i in ids if i}
    found = {u.id: PersonRef(id=u.id, full_name=u.full_name, email=u.email) for u in (await db.scalars(select(User).where(User.id.in_(wanted)))).all()} if wanted else {}
    return {i: found.get(i, PersonRef(id=i)) for i in wanted}


@router.get("/queries", response_model=QueryAuditPage)
async def list_queries(
    _: Auditor, db: AsyncSession = Depends(get_db), user_id: uuid.UUID | None = None, kind: str | None = Query(None, pattern="^(SEARCH|CHAT)$"),
    status: str | None = Query(None, max_length=40), since: datetime | None = None, until: datetime | None = None,
    q: str | None = Query(None, max_length=200), limit: Page = 50, offset: int = Query(0, ge=0),
) -> QueryAuditPage:
    limit = min(limit, PAGE_MAX)
    stmt = audit.queries_stmt(audit.query_filters(user_id, kind, status, since, until, q))
    total = await audit.count(db, stmt)
    rows = (await db.scalars(stmt.limit(limit).offset(offset))).all()
    people = await _people(db, {r.user_id for r in rows})
    items = [
        QueryAuditOut(
            id=r.id, created_at=r.created_at, user=people[r.user_id], kind=r.kind, query_text=r.query_text, filters=r.filters,
            allowed_doc_count=r.allowed_doc_count, retrieved_chunk_ids=r.retrieved_chunk_ids, response_status=r.response_status,
            latency_ms=r.latency_ms, request_id=r.request_id,
        )
        for r in rows
    ]
    return QueryAuditPage(items=items, total=total, limit=limit, offset=offset)


@router.get("/answers", response_model=AnswerAuditPage)
async def list_answers(
    _: Auditor, db: AsyncSession = Depends(get_db), query_audit_id: uuid.UUID | None = None, limit: Page = 50, offset: int = Query(0, ge=0),
) -> AnswerAuditPage:
    limit = min(limit, PAGE_MAX)
    stmt = select(AnswerAuditLog).order_by(AnswerAuditLog.created_at.desc(), AnswerAuditLog.id)
    if query_audit_id:
        stmt = stmt.where(AnswerAuditLog.query_audit_id == query_audit_id)
    total = await audit.count(db, stmt)
    rows = (await db.scalars(stmt.limit(limit).offset(offset))).all()
    items = [
        AnswerAuditOut(
            id=r.id, query_audit_id=r.query_audit_id, created_at=r.created_at, citation_chunk_ids=r.citation_chunk_ids, model=r.model,
            prompt_version=r.prompt_version, llm_calls=r.llm_calls, input_tokens=r.input_tokens, output_tokens=r.output_tokens,
            answer_chars=r.answer_chars, refusal_reason=r.refusal_reason,
        )
        for r in rows
    ]
    return AnswerAuditPage(items=items, total=total, limit=limit, offset=offset)


@router.get("/access-events", response_model=AccessEventPage)
async def list_access_events(
    _: Auditor, db: AsyncSession = Depends(get_db), event: str | None = Query(None, max_length=60), actor_id: uuid.UUID | None = None,
    since: datetime | None = None, until: datetime | None = None, limit: Page = 50, offset: int = Query(0, ge=0),
) -> AccessEventPage:
    limit = min(limit, PAGE_MAX)
    stmt = select(AccessEvent).order_by(AccessEvent.created_at.desc(), AccessEvent.id)
    if event:
        stmt = stmt.where(AccessEvent.event == event)
    if actor_id:
        stmt = stmt.where(AccessEvent.actor_id == actor_id)
    if since:
        stmt = stmt.where(AccessEvent.created_at >= since)
    if until:
        stmt = stmt.where(AccessEvent.created_at < until)
    total = await audit.count(db, stmt)
    rows = (await db.scalars(stmt.limit(limit).offset(offset))).all()
    people = await _people(db, {r.actor_id for r in rows} | {r.subject_id for r in rows})
    items = [
        AccessEventOut(
            id=r.id, created_at=r.created_at, event=r.event, actor=people.get(r.actor_id) if r.actor_id else None,
            subject=people.get(r.subject_id) if r.subject_id else None, detail=r.detail, request_id=r.request_id,
        )
        for r in rows
    ]
    return AccessEventPage(items=items, total=total, limit=limit, offset=offset)


@router.get("/export")
async def export_queries(
    request: Request, user: Auditor, db: AsyncSession = Depends(get_db), user_id: uuid.UUID | None = None,
    kind: str | None = Query(None, pattern="^(SEARCH|CHAT)$"), status: str | None = Query(None, max_length=40),
    since: datetime | None = None, until: datetime | None = None, q: str | None = Query(None, max_length=200),
    limit: int = Query(EXPORT_MAX, ge=1),
) -> StreamingResponse:
    """CSV of the query trail (FR-19). The export itself is recorded first: no record, no export."""
    limit = min(limit, EXPORT_MAX)
    db.add(AccessEvent(event="audit.export", actor_id=user.id, detail={"kind": kind or "ALL"}, request_id=getattr(request.state, "request_id", None)))
    await db.commit()
    rows = (await db.scalars(audit.queries_stmt(audit.query_filters(user_id, kind, status, since, until, q)).limit(limit))).all()
    people = await _people(db, {r.user_id for r in rows})
    return StreamingResponse(
        audit.csv_rows(iter(rows), people), media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="query-audit.csv"', "Cache-Control": "no-store"},
    )

