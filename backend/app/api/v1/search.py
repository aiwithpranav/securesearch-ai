"""POST /search: the best passages for a question, from documents the caller may read (Phase 5B).

Security rules for this route:
- Signed in is enough; WHAT is found is decided by the access resolver inside the search, per request.
- Admin is not reader: a system_admin finds only what the rules allow, like anyone else.
- The question text is never logged and never stored (NFR-10); the log has ids, mode, count and time only.
- Rate limited per user (NFR-03). Responses are personal, so they are never cached."""
import asyncio
import time
import uuid

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
from app.access.resolver import count_readable
from app.api.deps import get_current_user
from app.audit.service import add_query_row
from app.core import rate_limit
from app.core.config import settings
from app.core.errors import AppError
from app.core.logging import security_event
from app.db.session import get_db
from app.db.sync import SyncSession
from app.models import User
from app.retrieval import search as retrieval
from app.schemas.search import HitOut, SearchRequest, SearchResponse
from app.services.user_service import ADMIN_ROLE

router = APIRouter(tags=["search"])

_gate: asyncio.Semaphore | None = None


def _search_gate() -> asyncio.Semaphore:
    global _gate
    if _gate is None:
        _gate = asyncio.Semaphore(max(1, settings.search_concurrency))
    return _gate


def _run(user_id: uuid.UUID, query: str, mode: str) -> tuple[list[retrieval.Hit], int]:
    with SyncSession() as session:
        hits = retrieval.retrieve(session, user_id, query, mode=mode)
        return hits, count_readable(session, user_id)


@router.post("/search", response_model=SearchResponse)
async def search(
    body: SearchRequest, request: Request, response: Response, user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SearchResponse:
    allowed, retry = await rate_limit.hit(rate_limit.key_for("search", str(user.id)), settings.search_limit_per_minute, 60)
    if not allowed:
        raise AppError(
            429, "Too many attempts", "Too many searches. Try again shortly.",
            headers={"Retry-After": str(retry)}, extra={"retry_after_seconds": retry},
        )
    mode = body.mode or settings.retrieval_mode
    started = time.perf_counter()
    async with _search_gate():  # the models use the CPU: only a few searches at once, the rest wait
        hits, allowed_docs = await asyncio.to_thread(_run, user.id, body.query, mode)  # off the event loop, so the API stays responsive
    took_ms = int((time.perf_counter() - started) * 1000)

    # No audit, no results: if this row cannot be saved the request fails and the person gets nothing (Phase 7A).
    add_query_row(
        db, user_id=user.id, kind="SEARCH", query_text=body.query, filters={"mode": mode}, allowed_doc_count=allowed_docs,
        chunk_ids=[h.chunk_id for h in hits], status="OK" if hits else "NO_RESULTS", latency_ms=took_ms,
        request_id=getattr(request.state, "request_id", None),
    )
    await db.commit()

    security_event(
        "search", getattr(request.state, "request_id", None),
        user_id=str(user.id), mode=mode, result_count=len(hits), took_ms=took_ms,
    )
    detailed = ADMIN_ROLE in user.role_names
    response.headers["Cache-Control"] = "no-store"
    return SearchResponse(
        mode=mode, count=len(hits), took_ms=took_ms,
        hits=[
            HitOut(
                chunk_id=h.chunk_id, document_id=h.document_id, document_title=h.document_title,
                page_number=h.page_number, section=h.section, content=h.content, score=h.score,
                scores=h.scores if detailed else None,
            )
            for h in hits
        ],
    )


def warm_up() -> None:
    """Loads both models once, so the first real search is not slow. Never raises: a failure only costs speed."""
    import logging

    from app.embeddings import embed_query
    from app.retrieval.reranker import get_reranker

    try:
        embed_query("warm up")
        get_reranker().score("warm up", ["warm up"])
    except Exception as exc:  # noqa: BLE001
        logging.getLogger("search").warning("warm_up_failed type=%s", type(exc).__name__)
