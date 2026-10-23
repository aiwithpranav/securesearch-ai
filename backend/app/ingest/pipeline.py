"""The ingestion pipeline: original file -> parse -> chunk -> embed -> index -> activate.

Safety rules (NFR-05):
1. The slow work (parse, chunk, embed) happens OUTSIDE any database transaction.
2. Publishing is ONE transaction: old chunks are switched off and new chunks are inserted as active,
   or nothing changes at all. A search therefore sees the complete old version or the complete new
   version, never a half-indexed mix, and a crash in the middle leaves no partial data.
3. The job is idempotent: running it again after a crash or a retry gives the same result. Its chunks
   are tied to its own job id, and a job that is already READY is never run twice.
4. On failure the previous index is untouched, the job records a FIXED error code (never file text),
   and every active administrator gets an in-app notification (FR-33).
5. Nothing in this module logs document text. Logs hold IDs, counts and codes only."""
import hashlib
import logging
import uuid
from collections.abc import Callable
from datetime import datetime, timezone

from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.db.sync import SyncSession
from app.embeddings import embed_documents, model_label
from app.ingest.chunker import Tokenizer, chunk_blocks
from app.ingest.errors import IngestError
from app.ingest.parsers import parse
from app.ingest.tokenizer import ModelTokenizer
from app.ingest.validation import CONTENT_TYPES
from app.models import Document, DocumentChunk, DocumentVersion, IngestionJob, Notification, Role, User
from app.models import document as doc_models
from app.models.user import user_roles
from app.storage import ObjectNotFound, StorageError, get_storage
from app.storage.base import ObjectStorage

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 3
NOTIFY_KIND = "INGESTION_FAILED"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _log(event: str, job_id: uuid.UUID, **fields: object) -> None:
    logger.info(event, extra={"event": event, "fields": {"job_id": str(job_id), **fields}})


def _notify_admins(session: Session, document_id: uuid.UUID, job_id: uuid.UUID, code: str) -> None:
    admin_ids = session.scalars(
        select(User.id)
        .join(user_roles, user_roles.c.user_id == User.id)
        .join(Role, Role.id == user_roles.c.role_id)
        .where(Role.name == "system_admin", User.is_active.is_(True))
    ).all()
    for admin_id in admin_ids:
        session.add(
            Notification(
                user_id=admin_id,
                kind=NOTIFY_KIND,
                payload={"document_id": str(document_id), "job_id": str(job_id), "error_code": code},
            )
        )


def _mark_failed(factory: sessionmaker[Session], job_id: uuid.UUID, err: IngestError) -> None:
    """Records the failure. The previous (good) index is not touched."""
    with factory.begin() as s:
        job = s.get(IngestionJob, job_id)
        if job is None:
            return
        job.status = doc_models.FAILED
        job.error_code = err.code
        job.error_message = err.message
        job.completed_at = _now()
        doc = s.get(Document, job.document_id)
        if doc is not None:
            has_active = s.scalar(
                select(func.count()).select_from(DocumentChunk).where(
                    DocumentChunk.document_id == doc.id, DocumentChunk.is_active.is_(True)
                )
            )
            if not has_active:  # nothing searchable exists, so the document itself is FAILED
                doc.status = doc_models.FAILED
            if err.code != "DELETED":  # an admin who deleted the document does not need an alert
                _notify_admins(s, job.document_id, job_id, err.code)
    _log("ingest.failed", job_id, code=err.code)


def fail_job(job_id: uuid.UUID, err: IngestError, factory: sessionmaker[Session] = SyncSession) -> None:
    """Public helper (used by the task wrapper for timeouts)."""
    _mark_failed(factory, job_id, err)


def run_ingestion(
    job_id: uuid.UUID,
    *,
    factory: sessionmaker[Session] = SyncSession,
    storage: ObjectStorage | None = None,
    embed: Callable[[list[str]], list[list[float]]] = embed_documents,
    tokenizer: Tokenizer | None = None,
) -> str:
    """Runs one ingestion job. Returns READY, FAILED, RETRY or SKIPPED."""
    storage = storage or get_storage()
    tokenizer = tokenizer or ModelTokenizer()

    # --- 1. Claim the job (short transaction) ---
    with factory.begin() as s:
        job = s.execute(select(IngestionJob).where(IngestionJob.id == job_id).with_for_update()).scalar_one_or_none()
        if job is None:
            return "SKIPPED"
        if job.status in (doc_models.READY, doc_models.FAILED):
            return "SKIPPED"  # already finished: running twice must change nothing
        job.status = doc_models.PROCESSING
        job.attempt += 1
        job.started_at = job.started_at or _now()
        attempt = job.attempt
        document_id, version_id = job.document_id, job.document_version_id
        doc = s.get(Document, document_id)
        version = s.get(DocumentVersion, version_id)
        if doc is None or version is None:
            return "SKIPPED"
        deleted = doc.deleted_at is not None
        if doc.status == doc_models.QUEUED:
            doc.status = doc_models.PROCESSING
        storage_key, expected_hash, content_type = version.storage_path, version.content_hash, version.content_type
    _log("ingest.started", job_id, document_id=str(document_id), attempt=attempt)

    try:
        if deleted:
            raise IngestError("DELETED")

        # --- 2. Read the original and check it is the file we stored ---
        try:
            data = storage.get_bytes(storage_key)
        except ObjectNotFound:
            raise IngestError("STORAGE_ERROR", retryable=False) from None
        except StorageError:
            raise IngestError("STORAGE_ERROR", retryable=True) from None
        if hashlib.sha256(data).hexdigest() != expected_hash:
            raise IngestError("INTEGRITY_ERROR")

        # --- 3. Parse and chunk (no database, no network) ---
        kind = {v: k for k, v in CONTENT_TYPES.items()}.get(content_type)
        if kind is None:
            raise IngestError("UNSUPPORTED_TYPE")
        blocks = parse(kind, data)
        chunks = chunk_blocks(
            blocks, tokenizer, settings.chunk_target_tokens, settings.chunk_overlap_tokens, settings.chunk_max_tokens
        )
        if not chunks:
            raise IngestError("NO_TEXT")

        # --- 4. Embed ---
        try:
            vectors = embed([c.text for c in chunks])
        except Exception:
            raise IngestError("EMBEDDING_ERROR", retryable=True) from None
        if len(vectors) != len(chunks) or any(len(v) != settings.embedding_dimensions for v in vectors):
            raise IngestError("EMBEDDING_ERROR")
        label = model_label()

        # --- 5. Publish: ONE transaction ---
        with factory.begin() as s:
            locked = s.execute(select(Document).where(Document.id == document_id).with_for_update()).scalar_one()
            if locked.deleted_at is not None:
                raise IngestError("DELETED")
            s.execute(delete(DocumentChunk).where(DocumentChunk.ingestion_job_id == job_id))  # leftovers of a retry
            s.execute(
                update(DocumentChunk)
                .where(DocumentChunk.document_id == document_id, DocumentChunk.is_active.is_(True))
                .values(is_active=False)
            )
            s.execute(
                DocumentChunk.__table__.insert(),  # type: ignore[attr-defined]
                [
                    {
                        "id": uuid.uuid4(),
                        "document_id": document_id,
                        "document_version_id": version_id,
                        "ingestion_job_id": job_id,
                        "is_active": True,
                        "chunk_index": c.index,
                        "page_number": c.page,
                        "section": c.section,
                        "content": c.text,
                        "token_count": c.token_count,
                        "embedding": v,
                        "embedding_model": label,
                    }
                    for c, v in zip(chunks, vectors)
                ],
            )
            # The replaced chunks of this same version are no longer needed.
            s.execute(
                delete(DocumentChunk).where(
                    DocumentChunk.document_version_id == version_id,
                    DocumentChunk.is_active.is_(False),
                    DocumentChunk.ingestion_job_id != job_id,
                )
            )
            locked.current_version_id = version_id
            locked.status = doc_models.READY
            j = s.get(IngestionJob, job_id)
            assert j is not None
            j.status = doc_models.READY
            j.error_code = None
            j.error_message = None
            j.completed_at = _now()
        _log("ingest.ready", job_id, document_id=str(document_id), chunks=len(chunks))
        return doc_models.READY

    except IngestError as err:
        if err.retryable and attempt < MAX_ATTEMPTS:
            with factory.begin() as s:  # put the job back in the queue; Celery will run it again
                s.execute(
                    update(IngestionJob).where(IngestionJob.id == job_id).values(status=doc_models.QUEUED)
                )
            _log("ingest.retry", job_id, code=err.code, attempt=attempt)
            return "RETRY"
        _mark_failed(factory, job_id, err)
        return doc_models.FAILED
    except DBAPIError:
        # Database trouble (connection lost...). Treat like a transient error.
        if attempt < MAX_ATTEMPTS:
            try:
                with factory.begin() as s:
                    s.execute(update(IngestionJob).where(IngestionJob.id == job_id).values(status=doc_models.QUEUED))
            except Exception:
                pass
            _log("ingest.retry", job_id, code="DATABASE", attempt=attempt)
            return "RETRY"
        _mark_failed(factory, job_id, IngestError("INTERNAL"))
        return doc_models.FAILED
    except Exception as exc:  # a bug: never leak details, record a generic code
        logger.error("ingest.unexpected type=%s", type(exc).__name__, extra={"fields": {"job_id": str(job_id)}})
        _mark_failed(factory, job_id, IngestError("INTERNAL"))
        return doc_models.FAILED
