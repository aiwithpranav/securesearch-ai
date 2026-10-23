"""Answers, evidence preview, history and feedback (Phase 6B).

Security rules for this module:
- Signed in is enough to ask; WHAT can be answered is decided inside the engine by the access resolver, per request.
- Admin is not reader: nothing here gives a system_admin extra reading rights.
- Every refusal looks the same, so a refusal never reveals whether a restricted document exists.
- The question and the answer are never logged. The history keeps the question (the person's own, deletable) and the
  ids of cited passages, but not the answer text.
- The evidence preview re-checks READ on the document every time and answers 404 for anything else.
- Rate limited per person (every answer costs money); responses are never cached."""
import asyncio
import json
import time
import uuid
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi.responses import StreamingResponse
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.access.resolver import acan
from app.answers.service import ANSWERED, REFUSAL_TEXT, AnswerResult, answer_question
from app.api.deps import get_current_user
from app.api.v1.search import _search_gate
from app.audit.service import add_answer_row, add_query_row
from app.core import rate_limit
from app.core.config import settings
from app.core.errors import AppError
from app.core.logging import security_event
from app.db.session import get_db
from app.db.sync import SyncSession
from app.llm import LlmClient, LlmError, get_llm
from app.models import ChatFeedback, Document, DocumentChunk, DocumentVersion, SearchHistory, User
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    ChunkPreviewOut,
    CitationOut,
    FeedbackIn,
    FeedbackOut,
    HistoryItemOut,
    HistoryPage,
)

router = APIRouter(tags=["chat"])

def _unavailable() -> AppError:
    return AppError(503, "Answers unavailable", "Answers are not available right now. You can still search.")


def _not_found(what: str) -> AppError:
    return AppError(404, "Not found", f"{what} not found.")


async def _limit(kind: str, user: User, per_minute: int) -> None:
    allowed, retry = await rate_limit.hit(rate_limit.key_for(kind, str(user.id)), per_minute, 60)
    if not allowed:
        raise AppError(
            429, "Too many attempts", "Too many questions. Try again shortly.",
            headers={"Retry-After": str(retry)}, extra={"retry_after_seconds": retry},
        )


def _client() -> LlmClient:
    try:
        return get_llm()
    except LlmError:
        raise _unavailable() from None  # no key (or a bad setup): search still works


def _work(user_id: uuid.UUID, question: str, llm: LlmClient, progress=None) -> AnswerResult:  # type: ignore[no-untyped-def]
    with SyncSession() as session:
        return answer_question(session, user_id, question, llm=llm, progress=progress)


CHAT_FILTERS = {"mode": "hybrid", "rerank": True}


async def _save_history(db: AsyncSession, user: User, question: str, result: AnswerResult, request_id: str | None) -> uuid.UUID:
    """The person's own history AND the audit rows, in ONE transaction. If any of it fails, nothing is returned
    ("no audit, no answer")."""
    row = SearchHistory(
        user_id=user.id, question=question, status=result.status,
        citation_chunk_ids=[c.chunk_id for c in result.citations],
    )
    db.add(row)
    query_row = add_query_row(
        db, user_id=user.id, kind="CHAT", query_text=question, filters=CHAT_FILTERS, allowed_doc_count=result.allowed_doc_count,
        chunk_ids=result.retrieved_chunk_ids, status=result.status, latency_ms=result.took_ms, request_id=request_id,
    )
    await db.flush()
    add_answer_row(db, query_row, result)
    await db.commit()
    return row.id


async def _audit_unavailable(db: AsyncSession, user: User, question: str, exc: LlmError, started: float, request_id: str | None) -> None:
    """A question the model could not answer is still audited (status UNAVAILABLE), but no history item is made."""
    facts = getattr(exc, "audit", {})
    add_query_row(
        db, user_id=user.id, kind="CHAT", query_text=question, filters=CHAT_FILTERS,
        allowed_doc_count=int(facts.get("allowed_doc_count", 0)), chunk_ids=list(facts.get("retrieved_chunk_ids", [])),
        status="UNAVAILABLE", latency_ms=int((time.perf_counter() - started) * 1000), request_id=request_id,
    )
    await db.commit()


def _response(result: AnswerResult, request_id: str | None, history_id: uuid.UUID) -> ChatResponse:
    answered = result.status == ANSWERED
    return ChatResponse(
        status=result.status,  # type: ignore[arg-type]
        answer=result.answer if answered else None,
        refusal=None if answered else REFUSAL_TEXT,
        citations=[
            CitationOut(
                source_id=c.source_id, chunk_id=c.chunk_id, document_id=c.document_id, document_title=c.document_title,
                section=c.section, page=c.page, snippet=c.snippet, document_updated_at=c.document_updated_at,  # type: ignore[arg-type]
            )
            for c in (result.citations if answered else [])
        ],
        request_id=request_id, history_id=history_id,
    )


def _log(request: Request, user: User, result: AnswerResult) -> None:
    security_event(
        "chat", getattr(request.state, "request_id", None), user_id=str(user.id), status=result.status,
        reason=result.reason or None, llm_calls=result.llm_calls, input_tokens=result.input_tokens,
        output_tokens=result.output_tokens, citation_count=len(result.citations), took_ms=result.took_ms,
    )


@router.post("/chat", response_model=ChatResponse)
async def chat(
    body: ChatRequest, request: Request, response: Response, user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ChatResponse:
    await _limit("chat", user, settings.chat_limit_per_minute)
    llm = _client()
    request_id = getattr(request.state, "request_id", None)
    started = time.perf_counter()
    try:
        async with _search_gate():  # the models use the CPU: only a few at once
            result = await asyncio.to_thread(_work, user.id, body.question, llm)
    except LlmError as exc:
        await _audit_unavailable(db, user, body.question, exc, started, request_id)
        raise _unavailable() from None
    _log(request, user, result)
    history_id = await _save_history(db, user, body.question, result, request_id)
    response.headers["Cache-Control"] = "no-store"
    return _response(result, request_id, history_id)


def _sse(event: str, data: dict) -> bytes:  # type: ignore[type-arg]
    return f"event: {event}\ndata: {json.dumps(data)}\n\n".encode()


@router.post("/chat/stream")
async def chat_stream(
    body: ChatRequest, request: Request, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Progress as Server-Sent Events: small `stage` messages, then one `result` with the same shape as /chat.
    No answer text is sent before the citations have been validated (the stage labels hold no document text)."""
    await _limit("chat", user, settings.chat_limit_per_minute)
    llm = _client()
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue[tuple[str, dict] | None] = asyncio.Queue()  # type: ignore[type-arg]
    started = time.perf_counter()

    def progress(stage: str, label: str, status: str) -> None:  # called from the worker thread
        elapsed = int((time.perf_counter() - started) * 1000)
        loop.call_soon_threadsafe(queue.put_nowait, ("stage", {"id": stage, "label": label, "status": status, "elapsed_ms": elapsed}))

    async def run() -> None:
        try:
            async with _search_gate():
                result = await asyncio.to_thread(_work, user.id, body.question, llm, progress)
            _log(request, user, result)
            history_id = await _save_history(db, user, body.question, result, getattr(request.state, "request_id", None))
            payload = _response(result, getattr(request.state, "request_id", None), history_id).model_dump(mode="json")
            await queue.put(("result", payload))
        except LlmError as exc:
            try:
                await _audit_unavailable(db, user, body.question, exc, started, getattr(request.state, "request_id", None))
            except Exception:  # noqa: BLE001  (a failed audit must not turn into a leak; the person just gets the error)
                pass
            await queue.put(("error", {"status": 503, "title": "Answers unavailable", "detail": _unavailable().args[0]}))
        except Exception:  # noqa: BLE001  (never leak details into the stream)
            await queue.put(("error", {"status": 500, "title": "Something went wrong", "detail": "The answer could not be completed."}))
        finally:
            await queue.put(None)

    async def events() -> AsyncIterator[bytes]:
        task = asyncio.create_task(run())
        try:
            while (item := await queue.get()) is not None:
                yield _sse(*item)
        finally:
            await task

    return StreamingResponse(events(), media_type="text/event-stream", headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"})


@router.post("/chat/feedback", response_model=FeedbackOut)
async def feedback(body: FeedbackIn, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> FeedbackOut:
    item = await db.get(SearchHistory, body.history_id)
    if item is None or item.user_id != user.id:  # someone else's history item looks like a missing one
        raise _not_found("Answer")
    rating = 1 if body.rating == "UP" else -1
    existing = await db.scalar(select(ChatFeedback).where(ChatFeedback.history_id == item.id))
    if existing is None:
        db.add(ChatFeedback(history_id=item.id, user_id=user.id, rating=rating, comment=body.comment))
    else:
        existing.rating, existing.comment = rating, body.comment
    await db.commit()
    return FeedbackOut(history_id=item.id, rating=body.rating)


@router.get("/chunks/{chunk_id}/preview", response_model=ChunkPreviewOut)
async def chunk_preview(
    chunk_id: uuid.UUID, response: Response, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
) -> ChunkPreviewOut:
    """The passage behind a citation. READ is checked again here, every time: no rule, a denied rule, a deleted
    document, a document still processing, an old (inactive) passage or a missing id all give the same 404."""
    await _limit("preview", user, settings.preview_limit_per_minute)
    row = (
        await db.execute(
            select(DocumentChunk, Document, DocumentVersion.created_at.label("version_date"))
            .join(Document, Document.id == DocumentChunk.document_id)
            .join(DocumentVersion, DocumentVersion.id == DocumentChunk.document_version_id)
            .where(DocumentChunk.id == chunk_id, DocumentChunk.is_active.is_(True))
        )
    ).first()
    if row is None or not await acan(db, user.id, row.Document.id):
        raise _not_found("Passage")
    chunk, doc = row.DocumentChunk, row.Document
    response.headers["Cache-Control"] = "no-store"
    return ChunkPreviewOut(
        chunk_id=chunk.id, document_id=doc.id, document_title=doc.title, section=chunk.section, page=chunk.page_number,
        content=chunk.content, document_updated_at=row.version_date,
    )


@router.get("/me/search-history", response_model=HistoryPage)
async def list_history(
    limit: int = Query(20, ge=1), offset: int = Query(0, ge=0), user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> HistoryPage:
    limit = min(limit, settings.history_page_max)
    total = await db.scalar(select(func.count()).select_from(SearchHistory).where(SearchHistory.user_id == user.id)) or 0
    rows = (
        await db.execute(
            select(SearchHistory, ChatFeedback.rating)
            .outerjoin(ChatFeedback, ChatFeedback.history_id == SearchHistory.id)
            .where(SearchHistory.user_id == user.id)
            .order_by(SearchHistory.created_at.desc(), SearchHistory.id)
            .limit(limit).offset(offset)
        )
    ).all()
    items = [
        HistoryItemOut(
            id=h.id, question=h.question, status=h.status, citation_count=len(h.citation_chunk_ids or []),  # type: ignore[arg-type]
            rating=None if rating is None else ("UP" if rating > 0 else "DOWN"), created_at=h.created_at,
        )
        for h, rating in rows
    ]
    return HistoryPage(items=items, total=total, limit=limit, offset=offset)


@router.delete("/me/search-history/{history_id}", status_code=204)
async def delete_history_item(history_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> Response:
    result = await db.execute(delete(SearchHistory).where(SearchHistory.id == history_id, SearchHistory.user_id == user.id))
    await db.commit()
    if result.rowcount == 0:  # type: ignore[attr-defined]
        raise _not_found("History item")
    return Response(status_code=204)
