"""Background tasks: two small system tasks (3A) and the document ingestion task (3B)."""
import logging
import uuid

from celery.exceptions import SoftTimeLimitExceeded
from celery.signals import worker_ready
from sqlalchemy import select

from app.core.config import settings
from app.db.sync import SyncSession
from app.models import IngestionJob
from app.embeddings import embed_documents, model_label
from app.ingest.errors import IngestError
from app.ingest.pipeline import MAX_ATTEMPTS, fail_job, run_ingestion
from app.worker.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    name="documents.ingest",
    bind=True,
    max_retries=MAX_ATTEMPTS,
    soft_time_limit=settings.ingest_time_limit_seconds,
    time_limit=settings.ingest_time_limit_seconds + 60,
)
def ingest_document(self, job_id: str) -> str:  # type: ignore[no-untyped-def]
    """Runs one ingestion job. Safe to run twice (see app/ingest/pipeline.py)."""
    jid = uuid.UUID(job_id)
    try:
        result = run_ingestion(jid)
    except SoftTimeLimitExceeded:
        fail_job(jid, IngestError("TIMEOUT"))
        return "FAILED"
    if result == "RETRY":
        raise self.retry(countdown=10 * (self.request.retries + 1))
    return result


@worker_ready.connect
def requeue_unfinished_jobs(sender=None, **kwargs) -> None:  # type: ignore[no-untyped-def]
    """Runs once when the worker starts. With Redis, a job that was being processed when the whole worker
    was killed stays 'unacknowledged' for a long time. This sweep sends every unfinished job again right
    away. It is safe because ingestion is idempotent (a job that is already READY is skipped)."""
    try:
        with SyncSession() as s:
            ids = s.scalars(
                select(IngestionJob.id).where(IngestionJob.status.in_(["QUEUED", "PROCESSING"]))
            ).all()
        for job_id in ids:
            ingest_document.apply_async(args=[str(job_id)])
        logger.info("worker.requeued_unfinished_jobs", extra={"fields": {"count": len(ids)}})
    except Exception as exc:  # never stop the worker from starting
        logger.error("worker.requeue_failed type=%s", type(exc).__name__)


@celery_app.task(name="system.ping")
def ping() -> str:
    return "pong"


@celery_app.task(name="system.embed_check")
def embed_check() -> dict[str, object]:
    """Embeds one fixed sentence inside the WORKER process. Proves the model is present and offline-ready."""
    vector = embed_documents(["The worker can embed text."])[0]
    return {"model": model_label(), "dimensions": len(vector)}
