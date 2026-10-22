"""Sync sources and runs (Phase 8B, CR-004). Every route needs the system_admin role.

A source is a place documents come from. Its settings hold no secrets (tokens stay in .env). A run only ever adds, changes or
removes documents of that source, and only grants ALLOW READ to teams that source created."""
import uuid

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.core.errors import AppError
from app.core.logging import security_event
from app.db.session import get_db
from app.models import Department, SyncRun, SyncSource, User
from app.models import document as dm
from app.schemas.sync import SyncRunOut, SyncSourceCreate, SyncSourceOut, SyncSourceUpdate
from app.sync.base import REGISTRY, find_secret_key
from app.sync.engine import start_run

router = APIRouter(tags=["sync"], dependencies=[Depends(require_admin)])


def _rid(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


async def _out(db: AsyncSession, sources: list[SyncSource]) -> list[SyncSourceOut]:
    last: dict[uuid.UUID, SyncRun] = {}
    if sources:
        for r in (await db.scalars(select(SyncRun).where(SyncRun.source_id.in_([s.id for s in sources])).order_by(SyncRun.started_at))).all():
            last[r.source_id] = r  # later (newer) rows overwrite earlier ones
    return [
        SyncSourceOut(
            id=s.id, name=s.name, kind=s.kind, config=s.config, enabled=s.enabled, interval_minutes=s.interval_minutes,
            last_run_at=s.last_run_at, created_at=s.created_at, last_run=SyncRunOut.model_validate(last[s.id]) if s.id in last else None,
        )
        for s in sources
    ]


async def _get(db: AsyncSession, source_id: uuid.UUID) -> SyncSource:
    source = await db.get(SyncSource, source_id)
    if source is None:
        raise AppError(404, "Not Found", "Source not found.")
    return source


@router.get("/sync/sources", response_model=list[SyncSourceOut])
async def list_sources(db: AsyncSession = Depends(get_db)) -> list[SyncSourceOut]:
    return await _out(db, list((await db.scalars(select(SyncSource).order_by(SyncSource.name))).all()))


@router.post("/sync/sources", response_model=SyncSourceOut, status_code=status.HTTP_201_CREATED)
async def create_source(body: SyncSourceCreate, request: Request, actor: User = Depends(require_admin), db: AsyncSession = Depends(get_db)) -> SyncSourceOut:
    kind = body.kind.strip().upper()
    spec = REGISTRY.get(kind)
    if spec is None:
        raise AppError(422, "Validation failed", f"Source kind must be one of: {', '.join(sorted(REGISTRY)) or '(none available)'}.")
    secret = find_secret_key(body.config)
    if secret:
        raise AppError(422, "Validation failed", "Settings must not contain secrets. Keep tokens in the .env file.")
    cfg = body.config
    try:
        dept, dtype, sens = int(cfg["department_id"]), str(cfg["document_type"]).upper(), int(cfg["sensitivity_level"])
    except (KeyError, TypeError, ValueError):
        raise AppError(422, "Validation failed", "Settings need department_id, document_type and sensitivity_level.") from None
    if dtype not in dm.DOCUMENT_TYPES or not 0 <= sens <= 4:
        raise AppError(422, "Validation failed", "Document type or sensitivity level is not valid.")
    if await db.get(Department, dept) is None:
        raise AppError(422, "Validation failed", "Department does not exist.")
    try:
        spec.validate(cfg)
    except ValueError as exc:
        raise AppError(422, "Validation failed", str(exc)) from None
    source = SyncSource(name=body.name.strip(), kind=kind, config={**cfg, "document_type": dtype, "department_id": dept, "sensitivity_level": sens},
                        interval_minutes=body.interval_minutes, created_by=actor.id)
    db.add(source)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise AppError(409, "Conflict", "A source with this name already exists.") from None
    security_event("admin.sync_source_created", _rid(request), actor_id=str(actor.id), source_id=str(source.id), kind=kind)
    return (await _out(db, [source]))[0]


@router.patch("/sync/sources/{source_id}", response_model=SyncSourceOut)
async def update_source(source_id: uuid.UUID, body: SyncSourceUpdate, request: Request, actor: User = Depends(require_admin), db: AsyncSession = Depends(get_db)) -> SyncSourceOut:
    source = await _get(db, source_id)
    changed: list[str] = []
    if body.enabled is not None:
        source.enabled = body.enabled
        changed.append("enabled")
    if body.interval_minutes is not None:
        source.interval_minutes = body.interval_minutes
        changed.append("interval_minutes")
    await db.commit()
    security_event("admin.sync_source_updated", _rid(request), actor_id=str(actor.id), source_id=str(source.id), fields=changed)
    return (await _out(db, [source]))[0]


@router.post("/sync/sources/{source_id}/run", response_model=SyncRunOut, status_code=status.HTTP_202_ACCEPTED)
async def run_source(source_id: uuid.UUID, request: Request, actor: User = Depends(require_admin), db: AsyncSession = Depends(get_db)) -> SyncRunOut:
    source = await _get(db, source_id)
    run = await start_run(db, source, "MANUAL", actor.id)
    security_event("admin.sync_run_started", _rid(request), actor_id=str(actor.id), source_id=str(source.id), run_id=str(run.id))
    return SyncRunOut.model_validate(run)


@router.get("/sync/sources/{source_id}/runs", response_model=list[SyncRunOut])
async def list_runs(source_id: uuid.UUID, limit: int = Query(20, ge=1, le=100), db: AsyncSession = Depends(get_db)) -> list[SyncRunOut]:
    await _get(db, source_id)
    rows = (await db.scalars(select(SyncRun).where(SyncRun.source_id == source_id).order_by(SyncRun.started_at.desc()).limit(limit))).all()
    return [SyncRunOut.model_validate(r) for r in rows]


@router.get("/sync/runs/{run_id}", response_model=SyncRunOut)
async def get_run(run_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> SyncRunOut:
    run = await db.get(SyncRun, run_id)
    if run is None:
        raise AppError(404, "Not Found", "Run not found.")
    return SyncRunOut.model_validate(run)
