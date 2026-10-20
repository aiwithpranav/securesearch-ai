"""Admin operations on documents: upload, list, edit, soft delete, re-index, jobs, notifications.

Rules enforced here (the routes only call these functions):
- Nothing returned contains document text (admin is not reader).
- Upload order: store the file, then save database rows in ONE commit, then queue the job.
  If the database step fails, the stored file is removed again.
- A document with the same content as an existing one is refused (409)."""
import logging
import re
import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.core.errors import AppError
from app.core.logging import security_event
from app.ingest.validation import ValidatedFile
from app.models import Department, Document, DocumentChunk, DocumentVersion, IngestionJob, Notification, User
from app.models import document as dm
from app.schemas.documents import DocumentOut, JobOut, UserRef
from app.schemas.users import DepartmentOut
from app.storage import StorageError, get_storage
from app.storage.keys import original_key
from app.worker.celery_app import celery_app

logger = logging.getLogger(__name__)


def not_found(what: str = "Document") -> AppError:
    return AppError(404, "Not Found", f"{what} not found.")


def parse_countries(value: str | list[str] | None) -> list[str] | None:
    """'in, us' -> ['IN','US']. Empty means no country limit."""
    if value is None:
        return None
    items = value.split(",") if isinstance(value, str) else value
    out = [c.strip().upper() for c in items if c and c.strip()]
    if not out:
        return None
    if any(not re.fullmatch(r"[A-Z]{2}", c) for c in out):
        raise AppError(422, "Validation failed", "Countries must be 2-letter codes such as IN or US.")
    return sorted(set(out))


def check_type(document_type: str) -> str:
    t = document_type.strip().upper()
    if t not in dm.DOCUMENT_TYPES:
        raise AppError(422, "Validation failed", f"Document type must be one of: {', '.join(dm.DOCUMENT_TYPES)}.")
    return t


async def _require_department(db: AsyncSession, department_id: int) -> None:
    if await db.get(Department, department_id) is None:
        raise AppError(422, "Validation failed", "Department does not exist.")


# ------------------------------------------------------------------ building responses

async def _to_out(db: AsyncSession, docs: list[Document]) -> list[DocumentOut]:
    if not docs:
        return []
    ids = [d.id for d in docs]
    chunk_counts = dict(
        (await db.execute(
            select(DocumentChunk.document_id, func.count())
            .where(DocumentChunk.document_id.in_(ids), DocumentChunk.is_active.is_(True))
            .group_by(DocumentChunk.document_id)
        )).all()
    )
    version_counts = dict(
        (await db.execute(
            select(DocumentVersion.document_id, func.count()).where(DocumentVersion.document_id.in_(ids))
            .group_by(DocumentVersion.document_id)
        )).all()
    )
    version_nos = dict(
        (await db.execute(
            select(DocumentVersion.id, DocumentVersion.version_no).where(
                DocumentVersion.id.in_([d.current_version_id for d in docs if d.current_version_id])
            )
        )).all()
    )
    # newest job per document
    jobs: dict[uuid.UUID, IngestionJob] = {}
    for j in (await db.scalars(
        select(IngestionJob).where(IngestionJob.document_id.in_(ids)).order_by(IngestionJob.created_at)
    )).all():
        jobs[j.document_id] = j  # later (newer) rows overwrite earlier ones
    departments = {
        d.id: d for d in (await db.scalars(select(Department).where(Department.id.in_({x.department_id for x in docs})))).all()
    }
    users = {
        u.id: u for u in (await db.scalars(select(User).where(User.id.in_({x.uploaded_by for x in docs})))).all()
    }
    out: list[DocumentOut] = []
    for d in docs:
        job = jobs.get(d.id)
        out.append(
            DocumentOut(
                id=d.id,
                title=d.title,
                original_filename=d.original_filename,
                document_type=d.document_type,
                department=DepartmentOut.model_validate(departments[d.department_id]),
                sensitivity_level=d.sensitivity_level,
                sensitivity_name=dm.SENSITIVITY_NAMES[d.sensitivity_level],
                status=d.status,
                allowed_countries=d.allowed_countries,
                current_version_no=version_nos.get(d.current_version_id) if d.current_version_id else None,
                version_count=int(version_counts.get(d.id, 0)),
                chunk_count=int(chunk_counts.get(d.id, 0)),
                latest_job=JobOut.model_validate(job) if job else None,
                uploaded_by=UserRef(id=users[d.uploaded_by].id, full_name=users[d.uploaded_by].full_name),
                created_at=d.created_at,
                updated_at=d.updated_at,
            )
        )
    return out


async def _get_live(db: AsyncSession, document_id: uuid.UUID) -> Document:
    doc = await db.get(Document, document_id)
    if doc is None or doc.deleted_at is not None:
        raise not_found()
    return doc


async def _enqueue(job_id: uuid.UUID) -> None:
    """Sends the job to the worker. If the queue is down the job simply stays QUEUED and can be
    started again with /reindex; the upload itself is already safely stored."""
    try:
        await run_in_threadpool(celery_app.send_task, "documents.ingest", args=[str(job_id)])
    except Exception as exc:
        logger.error("enqueue_failed type=%s", type(exc).__name__, extra={"fields": {"job_id": str(job_id)}})


# ------------------------------------------------------------------ upload

async def create_upload(
    db: AsyncSession,
    actor: User,
    vfile: ValidatedFile,
    title: str | None,
    department_id: int,
    document_type: str,
    sensitivity_level: int,
    allowed_countries: list[str] | None,
    request_id: str | None,
) -> DocumentOut:
    await _require_department(db, department_id)

    existing = await db.scalar(
        select(Document.id)
        .join(DocumentVersion, DocumentVersion.document_id == Document.id)
        .where(DocumentVersion.content_hash == vfile.sha256, Document.deleted_at.is_(None))
        .limit(1)
    )
    if existing is not None:
        raise AppError(
            409, "Conflict", "A document with identical content already exists.",
            extra={"existing_document_id": str(existing)},
        )

    document_id = uuid.uuid4()
    key = original_key(document_id, 1, vfile.sha256)
    storage = get_storage()
    try:
        await run_in_threadpool(storage.ensure_bucket)
        await run_in_threadpool(storage.put_bytes, key, vfile.data, vfile.content_type)
    except StorageError:
        raise AppError(503, "Service Unavailable", "The file store is not available. Try again later.") from None

    version_id, job_id = uuid.uuid4(), uuid.uuid4()
    doc = Document(
        id=document_id,
        title=(title or vfile.filename.rsplit(".", 1)[0]).strip()[:200] or "Untitled",
        original_filename=vfile.filename,
        document_type=document_type,
        department_id=department_id,
        sensitivity_level=sensitivity_level,
        status=dm.QUEUED,
        allowed_countries=allowed_countries,
        uploaded_by=actor.id,
    )
    db.add(doc)
    await db.flush()  # the version and job rows need the document row to exist first
    db.add(
        DocumentVersion(
            id=version_id, document_id=document_id, version_no=1, content_hash=vfile.sha256,
            storage_path=key, size_bytes=vfile.size, content_type=vfile.content_type,
        )
    )
    await db.flush()
    db.add(
        IngestionJob(
            id=job_id, document_id=document_id, document_version_id=version_id,
            status=dm.QUEUED, content_hash=vfile.sha256,
        )
    )
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        try:
            await run_in_threadpool(storage.delete, key)  # do not leave an orphan file behind
        except StorageError:
            pass
        raise

    await _enqueue(job_id)
    security_event(
        "admin.document_uploaded", request_id, actor_id=str(actor.id), document_id=str(document_id),
        size=vfile.size, kind=vfile.kind,
    )
    return (await _to_out(db, [doc]))[0]


# ------------------------------------------------------------------ read

async def list_documents(
    db: AsyncSession, limit: int, offset: int, status: str | None, department_id: int | None
) -> tuple[list[DocumentOut], int]:
    where = [Document.deleted_at.is_(None)]
    if status:
        where.append(Document.status == status)
    if department_id:
        where.append(Document.department_id == department_id)
    total = await db.scalar(select(func.count()).select_from(Document).where(*where)) or 0
    docs = (await db.scalars(
        select(Document).where(*where).order_by(Document.created_at.desc()).limit(limit).offset(offset)
    )).all()
    return await _to_out(db, list(docs)), int(total)


async def get_document(db: AsyncSession, document_id: uuid.UUID) -> DocumentOut:
    return (await _to_out(db, [await _get_live(db, document_id)]))[0]


async def list_versions(db: AsyncSession, document_id: uuid.UUID) -> list[DocumentVersion]:
    await _get_live(db, document_id)
    return list((await db.scalars(
        select(DocumentVersion).where(DocumentVersion.document_id == document_id).order_by(DocumentVersion.version_no)
    )).all())


# ------------------------------------------------------------------ change

async def update_document(
    db: AsyncSession, document_id: uuid.UUID, changes: dict[str, object], actor: User, request_id: str | None
) -> DocumentOut:
    doc = await _get_live(db, document_id)
    if "department_id" in changes and changes["department_id"] is not None:
        await _require_department(db, int(changes["department_id"]))  # type: ignore[arg-type]
    if "document_type" in changes and changes["document_type"] is not None:
        changes["document_type"] = check_type(str(changes["document_type"]))
    if "allowed_countries" in changes:
        changes["allowed_countries"] = parse_countries(changes["allowed_countries"])  # type: ignore[arg-type]
    for field, value in changes.items():
        if value is not None or field == "allowed_countries":
            setattr(doc, field, value)
    await db.commit()
    await db.refresh(doc)
    security_event(
        "admin.document_updated", request_id, actor_id=str(actor.id), document_id=str(doc.id), fields=sorted(changes)
    )
    return (await _to_out(db, [doc]))[0]


async def delete_document(db: AsyncSession, document_id: uuid.UUID, actor: User, request_id: str | None) -> None:
    """Soft delete: the row stays, chunks stop being active, the original file is kept (cleanup is backlog)."""
    doc = await _get_live(db, document_id)
    doc.deleted_at = datetime.now(timezone.utc)
    await db.execute(
        update(DocumentChunk).where(DocumentChunk.document_id == doc.id, DocumentChunk.is_active.is_(True))
        .values(is_active=False)
    )
    await db.commit()
    security_event("admin.document_deleted", request_id, actor_id=str(actor.id), document_id=str(doc.id))


async def reindex(db: AsyncSession, document_id: uuid.UUID, actor: User, request_id: str | None) -> JobOut:
    """Re-reads the stored original and builds the chunks again. The old chunks stay active until the new
    ones are complete (the swap is one transaction in the pipeline)."""
    doc = await _get_live(db, document_id)
    busy = await db.scalar(
        select(func.count()).select_from(IngestionJob).where(
            IngestionJob.document_id == doc.id, IngestionJob.status.in_([dm.QUEUED, dm.PROCESSING])
        )
    )
    if busy:
        raise AppError(409, "Conflict", "This document is already being processed.")
    version = await db.scalar(
        select(DocumentVersion).where(DocumentVersion.document_id == doc.id).order_by(DocumentVersion.version_no.desc())
    )
    assert version is not None
    job = IngestionJob(
        document_id=doc.id, document_version_id=version.id, status=dm.QUEUED, content_hash=version.content_hash
    )
    db.add(job)
    if doc.status == dm.FAILED:
        doc.status = dm.QUEUED
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise AppError(409, "Conflict", "This document is already being processed.") from None
    await _enqueue(job.id)
    security_event("admin.document_reindex", request_id, actor_id=str(actor.id), document_id=str(doc.id), job_id=str(job.id))
    return JobOut.model_validate(job)


# ------------------------------------------------------------------ jobs

async def list_jobs(
    db: AsyncSession, limit: int, offset: int, status: str | None, document_id: uuid.UUID | None = None
) -> tuple[list[IngestionJob], int]:
    where = []
    if status:
        where.append(IngestionJob.status == status)
    if document_id:
        where.append(IngestionJob.document_id == document_id)
    total = await db.scalar(select(func.count()).select_from(IngestionJob).where(*where)) or 0
    rows = await db.scalars(
        select(IngestionJob).where(*where).order_by(IngestionJob.created_at.desc()).limit(limit).offset(offset)
    )
    return list(rows.all()), int(total)


async def get_job(db: AsyncSession, job_id: uuid.UUID) -> IngestionJob:
    job = await db.get(IngestionJob, job_id)
    if job is None:
        raise not_found("Job")
    return job


# ------------------------------------------------------------------ notifications

async def list_notifications(db: AsyncSession, user: User, limit: int, unread_only: bool) -> list[Notification]:
    where = [Notification.user_id == user.id]
    if unread_only:
        where.append(Notification.read_at.is_(None))
    rows = await db.scalars(select(Notification).where(*where).order_by(Notification.created_at.desc()).limit(limit))
    return list(rows.all())


async def mark_notification_read(db: AsyncSession, user: User, notification_id: uuid.UUID) -> Notification:
    n = await db.get(Notification, notification_id)
    if n is None or n.user_id != user.id:  # someone else's notification looks like a missing one
        raise not_found("Notification")
    if n.read_at is None:
        n.read_at = datetime.now(timezone.utc)
        await db.commit()
    return n
