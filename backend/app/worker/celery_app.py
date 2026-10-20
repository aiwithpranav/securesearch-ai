"""The Celery application: runs background jobs (document ingestion from Phase 3B).

Why Celery and not FastAPI background tasks: Celery jobs survive a restart and can be retried
(NFR-05). Settings below make a job safe to retry:
- acks_late: a job is removed from the queue only AFTER it finishes, so a crash re-delivers it.
- reject_on_worker_lost: if the worker process dies mid-job, the job goes back to the queue.
- prefetch 1: one job at a time per worker slot, so a long job never hides others.
Jobs MUST therefore be written to be idempotent (running twice gives the same result)."""
from celery import Celery

from app.core.config import settings


def _redis_db(url: str, db: int) -> str:
    """redis://redis:6379/0 -> redis://redis:6379/<db>  (queue and results use their own databases)."""
    base = url.rsplit("/", 1)[0] if url.count("/") >= 3 else url
    return f"{base}/{db}"


celery_app = Celery(
    "securesearch",
    broker=_redis_db(settings.redis_url, 1),
    backend=_redis_db(settings.redis_url, 2),
    include=["app.worker.tasks"],
)

celery_app.conf.update(
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    result_expires=3600,
    broker_connection_retry_on_startup=True,
    # If a worker dies, Redis hands its unfinished job to another worker after this many seconds.
    # Must be longer than the longest job (ingest time limit 600 s + 60 s). The worker also re-sends
    # unfinished jobs when it starts (see tasks.py), so recovery after a restart is much faster.
    broker_transport_options={"visibility_timeout": 900},
    timezone="UTC",
    enable_utc=True,
)
