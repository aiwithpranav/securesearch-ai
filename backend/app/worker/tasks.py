"""Background tasks: two small system tasks (3A), the document ingestion task (3B) and the sync tasks (8B)."""
import asyncio
import logging
import uuid

from celery.exceptions import SoftTimeLimitExceeded
from celery.signals import worker_ready
from sqlalchemy import func, select, update

from app.audit import retention
from app.core.config import settings
from app.core.status import record_heartbeat
from app.db.sync import SyncSession
from app.embeddings import embed_documents, model_label
from app.ingest import cleanup
from app.ingest.errors import IngestError
from app.ingest.pipeline import MAX_ATTEMPTS, fail_job, run_ingestion
from app.models import IngestionJob, SyncRun
from app.sync.engine import execute_run, fail_run, tick
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
        with SyncSession.begin() as s:  # a sync run that was going when the worker stopped did not finish
            s.execute(update(SyncRun).where(SyncRun.status == "RUNNING").values(status="FAILED", finished_at=func.now(), error_code="INTERRUPTED"))
        logger.info("worker.requeued_unfinished_jobs", extra={"fields": {"count": len(ids)}})
    except Exception as exc:  # never stop the worker from starting
        logger.error("worker.requeue_failed type=%s", type(exc).__name__)


@celery_app.task(name="sync.execute_run", bind=True, soft_time_limit=1800, time_limit=1860)
def sync_execute_run(self, run_id: str) -> str:  # type: ignore[no-untyped-def]
    """Runs one sync (see app/sync/engine.py). It is safe to run twice: a run that is no longer RUNNING is ignored."""
    rid = uuid.UUID(run_id)
    try:
        asyncio.run(execute_run(rid))
    except SoftTimeLimitExceeded:
        asyncio.run(fail_run(rid, "TIMEOUT"))
        return "FAILED"
    return "OK"


@celery_app.task(name="sync.tick")
def sync_tick() -> int:
    """Every minute: starts a run for each source that is due."""
    return asyncio.run(tick())


@celery_app.task(name="system.heartbeat")
def heartbeat() -> str:
    """Every minute: proves to the status page that the worker and the scheduler are alive."""
    record_heartbeat()
    return "ok"


@celery_app.task(name="audit.purge")
def audit_purge() -> dict[str, int]:
    """Every night: removes audit rows older than the retention setting (see app/audit/retention.py)."""
    counts = retention.run()
    return {"queries": counts.queries, "answers": counts.answers, "events": counts.events}


@celery_app.task(name="ingest.cleanup")
def ingest_cleanup() -> int:
    """Every night: removes the passages of document versions older than the newest KEEP_VERSIONS."""
    return cleanup.run()


@celery_app.task(name="system.ping")
def ping() -> str:
    return "pong"


@celery_app.task(name="system.embed_check")
def embed_check() -> dict[str, object]:
    """Embeds one fixed sentence inside the WORKER process. Proves the model is present and offline-ready."""
    vector = embed_documents(["The worker can embed text."])[0]
    return {"model": model_label(), "dimensions": len(vector)}
