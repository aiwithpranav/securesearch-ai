"""Background tasks. Phase 3A only has two small system tasks that prove the worker works.
The ingestion task arrives in Phase 3B."""
from app.embeddings import embed_documents, model_label
from app.worker.celery_app import celery_app


@celery_app.task(name="system.ping")
def ping() -> str:
    return "pong"


@celery_app.task(name="system.embed_check")
def embed_check() -> dict[str, object]:
    """Embeds one fixed sentence inside the WORKER process. Proves the model is present and offline-ready."""
    vector = embed_documents(["The worker can embed text."])[0]
    return {"model": model_label(), "dimensions": len(vector)}
