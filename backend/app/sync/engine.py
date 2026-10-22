"""The sync engine (Phase 8B): makes the documents of one source match the source, doing only what changed.

For every item the source lists, the engine decides:
- new item                        -> upload it (version 1) and give it the source's teams as readers;
- same content, same readers      -> skip (nothing is read again, nothing is embedded again);
- same content, other readers     -> update the access rules only (a permission-only change, no re-indexing);
- changed content                 -> a new version (Phase 8A): the old version keeps answering until the new one is ready;
- item gone from the source       -> soft delete (and restored if it comes back).
Team membership follows the source: a person removed from a team loses access at the next query.

Safety rules:
- Only teams whose name starts with the source's prefix are managed. The engine writes ALLOW READ for those teams and nothing
  else: no DENY, no rule for any other principal. Rules an administrator added by hand are never touched.
- A listing that is empty (or would delete too many documents) stops the whole run before anything changes: a broken source
  must never wipe the index. An unreachable source changes nothing.
- One bad item never stops the run: it is counted, its id and a code word are kept, and the run ends PARTIAL.
- One run per source at a time (a database rule). A run that is still RUNNING after 30 minutes counts as stale.
- Nothing here logs document text."""
import logging
import uuid
from collections import Counter
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, exists, func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from starlette.concurrency import run_in_threadpool

from app.core.config import settings
from app.core.errors import AppError
from app.core.logging import security_event
from app.db.session import _async_url
from app.ingest.errors import IngestError
from app.ingest.validation import validate_file
from app.models import Document, DocumentAcl, DocumentVersion, Group, SyncRun, SyncSource, User, user_groups
from app.services import access_service, document_service as svc
from app.sync.base import REGISTRY, Connector, SourceItem, permission_hash
from app.worker.celery_app import celery_app

logger = logging.getLogger(__name__)

STALE_AFTER = timedelta(minutes=30)
MAX_ERRORS = 20
DELETE_GUARD_MIN_DOCS = 4  # below this many documents the "too many deletes" guard does not apply
DELETE_GUARD_FRACTION = 0.5
RUNNING, DONE, PARTIAL, FAILED = "RUNNING", "DONE", "PARTIAL", "FAILED"


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ------------------------------------------------------------------ starting runs

async def enqueue_run(run_id: uuid.UUID) -> None:
    """Sends the run to the worker. Raises if the queue is down."""
    await run_in_threadpool(celery_app.send_task, "sync.execute_run", args=[str(run_id)])


async def start_run(db: AsyncSession, source: SyncSource, trigger: str, started_by: uuid.UUID | None) -> SyncRun:
    """Creates the RUNNING row (one per source) and queues the work. A run that is stale is closed first."""
    await db.execute(
        update(SyncRun).where(SyncRun.source_id == source.id, SyncRun.status == RUNNING, SyncRun.started_at < _now() - STALE_AFTER)
        .values(status=FAILED, finished_at=_now(), error_code="STALE")
    )
    run = SyncRun(source_id=source.id, trigger=trigger, started_by=started_by)
    db.add(run)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise AppError(409, "Conflict", "A sync is already running for this source.") from None
    try:
        await enqueue_run(run.id)
    except Exception as exc:  # noqa: BLE001
        logger.error("sync.enqueue_failed type=%s", type(exc).__name__)
        run.status, run.finished_at, run.error_code = FAILED, _now(), "QUEUE_UNAVAILABLE"
        await db.commit()
        raise AppError(503, "Service Unavailable", "The background worker is not available. Try again later.") from None
    return run


async def due_sources(db: AsyncSession) -> list[SyncSource]:
    """Enabled sources whose last run is older than their interval and that have no run going."""
    running = exists().where(SyncRun.source_id == SyncSource.id, SyncRun.status == RUNNING, SyncRun.started_at >= _now() - STALE_AFTER)
    due = or_(SyncSource.last_run_at.is_(None), SyncSource.last_run_at <= _now() - SyncSource.interval_minutes * timedelta(minutes=1))
    return list((await db.scalars(select(SyncSource).where(SyncSource.enabled.is_(True), due, ~running).order_by(SyncSource.name))).all())


async def tick(maker: async_sessionmaker[AsyncSession] | None = None) -> int:
    """Called every minute by the scheduler: starts a run for every source that is due. Returns how many were started."""
    engine = None
    if maker is None:
        engine = create_async_engine(_async_url(settings.database_url), poolclass=NullPool)
        maker = async_sessionmaker(engine, expire_on_commit=False)
    started = 0
    try:
        async with maker() as db:
            for source in await due_sources(db):
                try:
                    await start_run(db, source, "SCHEDULE", None)
                    started += 1
                except AppError:
                    continue  # already running, or the queue is down: try again at the next tick
    finally:
        if engine is not None:
            await engine.dispose()
    return started


# ------------------------------------------------------------------ running

async def execute_run(run_id: uuid.UUID, maker: async_sessionmaker[AsyncSession] | None = None) -> None:
    engine = None
    if maker is None:  # the worker starts a new event loop for every task, so it gets its own short-lived engine
        engine = create_async_engine(_async_url(settings.database_url), poolclass=NullPool)
        maker = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with maker() as db:
            await _execute(db, run_id)
    finally:
        if engine is not None:
            await engine.dispose()


async def fail_run(run_id: uuid.UUID, code: str, maker: async_sessionmaker[AsyncSession] | None = None) -> None:
    """Closes a run that could not finish (timeout, crash)."""
    engine = None
    if maker is None:
        engine = create_async_engine(_async_url(settings.database_url), poolclass=NullPool)
        maker = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with maker() as db:
            await db.execute(update(SyncRun).where(SyncRun.id == run_id, SyncRun.status == RUNNING).values(status=FAILED, finished_at=_now(), error_code=code))
            await db.commit()
    finally:
        if engine is not None:
            await engine.dispose()


async def _finish(db: AsyncSession, run: SyncRun, source: SyncSource, counts: Counter[str], errors: list[dict[str, str]], status: str, code: str | None = None) -> None:
    run.counts, run.errors, run.status, run.error_code, run.finished_at = dict(counts), errors, status, code, _now()
    source.last_run_at = run.finished_at
    await db.commit()
    security_event("admin.sync_run_finished", None, run_id=str(run.id), source_id=str(source.id), kind=status)


def _error_code(exc: Exception) -> str:
    if isinstance(exc, IngestError):
        return exc.code
    if isinstance(exc, AppError):
        return "DUPLICATE_CONTENT" if exc.status == 409 and "identical" in exc.detail else f"REFUSED_{exc.status}"
    return "INTERNAL"


async def _execute(db: AsyncSession, run_id: uuid.UUID) -> None:
    run = await db.get(SyncRun, run_id)
    if run is None or run.status != RUNNING:
        return
    source = await db.get(SyncSource, run.source_id)
    actor = await db.get(User, source.created_by) if source else None
    counts: Counter[str] = Counter()
    errors: list[dict[str, str]] = []
    if source is None or actor is None:
        await db.execute(update(SyncRun).where(SyncRun.id == run_id).values(status=FAILED, finished_at=_now(), error_code="SOURCE_MISSING"))
        await db.commit()
        return

    spec = REGISTRY.get(source.kind.upper())
    if spec is None:
        await _finish(db, run, source, counts, errors, FAILED, "UNKNOWN_KIND")
        return
    try:
        connector = spec.build(source.config)
        items = await run_in_threadpool(connector.list_items)
        members = await run_in_threadpool(connector.members)
    except Exception as exc:  # noqa: BLE001  nothing has been changed yet
        logger.error("sync.source_unreachable type=%s", type(exc).__name__, extra={"fields": {"source_id": str(source.id)}})
        await _finish(db, run, source, counts, errors, FAILED, "SOURCE_UNREACHABLE")
        return

    ids = [i.external_id for i in items]
    if len(set(ids)) != len(ids):
        await _finish(db, run, source, counts, errors, FAILED, "BAD_LISTING")
        return
    key = source.external_key
    existing = {d.external_id: d for d in (await db.scalars(select(Document).where(Document.external_source == key))).all() if d.external_id}
    live = {k: d for k, d in existing.items() if d.deleted_at is None}
    gone = [k for k in live if k not in set(ids)]
    if not source.config.get("allow_mass_delete"):
        if not items and live:
            await _finish(db, run, source, counts, errors, FAILED, "EMPTY_LISTING")
            return
        if len(live) >= DELETE_GUARD_MIN_DOCS and len(gone) > DELETE_GUARD_FRACTION * len(live):
            await _finish(db, run, source, counts, errors, FAILED, "TOO_MANY_DELETES")
            return

    counts["items"] = len(items)
    group_ids = await _sync_teams(db, source, items, members, counts)
    managed_ids = set(group_ids.values())

    def fail(item_id: str, exc: Exception) -> None:
        counts["failed"] += 1
        if len(errors) < MAX_ERRORS:
            errors.append({"item": item_id[:200], "code": _error_code(exc)})
        if _error_code(exc) == "INTERNAL":
            logger.error("sync.item_failed type=%s", type(exc).__name__, extra={"fields": {"run_id": str(run.id)}})

    for item in items:
        try:
            await _process_item(db, source, actor, connector, item, existing.get(item.external_id), group_ids, managed_ids, counts)
        except Exception as exc:  # noqa: BLE001  one bad item never stops the run
            await db.rollback()
            fail(item.external_id, exc)
    for ext in gone:
        try:
            await svc.delete_document(db, live[ext].id, actor, None)
            counts["deleted"] += 1
        except Exception as exc:  # noqa: BLE001
            await db.rollback()
            fail(ext, exc)
    await _finish(db, run, source, counts, errors, PARTIAL if counts["failed"] else DONE)


# ------------------------------------------------------------------ teams (groups) and members

async def _sync_teams(
    db: AsyncSession, source: SyncSource, items: list[SourceItem], members: dict[str, set[str]], counts: Counter[str]
) -> dict[str, int]:
    """Makes the source's teams exist and makes their members match the source. Returns team name -> group id."""
    prefix = source.group_prefix
    wanted = {g for i in items for g in i.groups} | set(members)
    have = {g.name[len(prefix):]: g for g in (await db.scalars(select(Group).where(func.starts_with(Group.name, prefix)))).all()}
    for name in wanted - set(have):
        g = Group(name=prefix + name, description=f"Managed by sync source {source.name}")
        db.add(g)
        have[name] = g
    await db.flush()
    emails = {e.strip().lower() for names in members.values() for e in names if e and e.strip()}
    user_by_email = {u.email.lower(): u.id for u in (await db.scalars(select(User).where(func.lower(User.email).in_(emails)))).all()} if emails else {}
    counts["unknown_members"] = len(emails - set(user_by_email))
    for name, group in have.items():  # a team that vanished from the source ends up with nobody in it
        desired = {user_by_email[e.strip().lower()] for e in members.get(name, set()) if e and e.strip().lower() in user_by_email}
        current = set((await db.scalars(select(user_groups.c.user_id).where(user_groups.c.group_id == group.id))).all())
        for uid in desired - current:
            await db.execute(user_groups.insert().values(user_id=uid, group_id=group.id))
            counts["members_added"] += 1
        if current - desired:
            await db.execute(delete(user_groups).where(user_groups.c.group_id == group.id, user_groups.c.user_id.in_(current - desired)))
            counts["members_removed"] += len(current - desired)
    await db.commit()
    return {name: g.id for name, g in have.items()}


# ------------------------------------------------------------------ one item

async def _newest_version(db: AsyncSession, document_id: uuid.UUID) -> DocumentVersion:
    version = await db.scalar(select(DocumentVersion).where(DocumentVersion.document_id == document_id).order_by(DocumentVersion.version_no.desc()).limit(1))
    assert version is not None
    return version


async def _apply_rules(db: AsyncSession, actor: User, document_id: uuid.UUID, wanted: set[int], managed: set[int], phash: str) -> bool:
    """Makes the document's ALLOW READ rules for the source's teams equal `wanted`. Other rules are never touched.
    Marks the newest version with the permission hash only after the rules are in place."""
    before = await access_service._snapshot(db, document_id)
    rules = (await db.scalars(
        select(DocumentAcl).where(
            DocumentAcl.document_id == document_id, DocumentAcl.principal_type == "GROUP", DocumentAcl.effect == "ALLOW",
            DocumentAcl.permission == "READ", DocumentAcl.principal_id.in_({str(g) for g in managed}),
        )
    )).all()
    have = {r.principal_id: r for r in rules}
    changed = False
    for pid, rule in have.items():
        if int(pid) not in wanted:
            await db.delete(rule)
            changed = True
    for gid in wanted:
        if str(gid) not in have:
            db.add(DocumentAcl(document_id=document_id, principal_type="GROUP", principal_id=str(gid), effect="ALLOW", permission="READ", granted_by=actor.id))
            changed = True
    await db.flush()
    if changed:
        await access_service._record(db, actor, document_id, before)
    (await _newest_version(db, document_id)).permission_hash = phash
    await db.commit()
    return changed


async def _process_item(
    db: AsyncSession, source: SyncSource, actor: User, connector: Connector, item: SourceItem, doc: Document | None,
    group_ids: dict[str, int], managed: set[int], counts: Counter[str],
) -> None:
    data = await run_in_threadpool(connector.read, item)
    vfile = validate_file(item.filename, data)
    wanted = {group_ids[g] for g in item.groups}
    phash = permission_hash(item.groups)
    cfg = source.config
    if doc is None:
        out = await svc.create_upload(
            db, actor, vfile, item.title[:200], int(cfg["department_id"]), str(cfg["document_type"]), int(cfg["sensitivity_level"]), None, None,
            external_source=source.external_key, external_id=item.external_id, source_url=item.url,
        )
        counts["new"] += 1
        await _apply_rules(db, actor, out.id, wanted, managed, phash)
        return
    newest = await _newest_version(db, doc.id)
    if doc.deleted_at is not None:  # it is back in the source: restore it (a changed file is picked up by the next run)
        await svc.restore_document(db, doc.id, actor, None)
        counts["restored"] += 1
        await _apply_rules(db, actor, doc.id, wanted, managed, phash)
        return
    if newest.content_hash != vfile.sha256:
        await svc.upload_new_version(db, actor, doc.id, vfile, None)
        counts["changed"] += 1
        await _apply_rules(db, actor, doc.id, wanted, managed, phash)
        return
    if newest.permission_hash != phash:  # same file, other readers: no re-indexing
        await _apply_rules(db, actor, doc.id, wanted, managed, phash)
        counts["permission_only"] += 1
        return
    counts["unchanged"] += 1
