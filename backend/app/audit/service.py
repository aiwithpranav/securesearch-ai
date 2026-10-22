"""Writing and reading the audit trail.

Rules:
- Writing is part of answering: if the audit row cannot be saved, the request fails and the person gets nothing
  ("no audit, no answer"). Callers must not swallow errors from these functions.
- Only ids, counts and code words are written, never the answer and never document text.
- Reading is for the audit roles only (the API enforces that); this module just builds the queries."""
import csv
import io
import uuid
from collections.abc import Iterator
from datetime import datetime, timezone

from sqlalchemy import ColumnElement, Select, and_, func, select, true
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.answers.prompt import PROMPT_VERSION
from app.answers.service import ANSWERED, AnswerResult
from app.core.config import settings
from app.db.sync import SyncSession
from app.models import AccessEvent, AnswerAuditLog, QueryAuditLog

# ------------------------------------------------------------------ writing the query trail


def add_query_row(
    db: AsyncSession, *, user_id: uuid.UUID, kind: str, query_text: str, filters: dict, allowed_doc_count: int,  # type: ignore[type-arg]
    chunk_ids: list[uuid.UUID], status: str, latency_ms: int, request_id: str | None,
) -> QueryAuditLog:
    row = QueryAuditLog(
        id=uuid.uuid4(), user_id=user_id, kind=kind, query_text=query_text, filters=filters,
        allowed_doc_count=allowed_doc_count, retrieved_chunk_ids=chunk_ids, response_status=status,
        latency_ms=latency_ms, request_id=request_id,
    )
    db.add(row)
    return row


def add_answer_row(db: AsyncSession, query_row: QueryAuditLog, result: AnswerResult) -> AnswerAuditLog:
    """One row per answered or refused question: model, tokens, cited ids, a code word. Never the answer text."""
    row = AnswerAuditLog(
        query_audit_id=query_row.id, citation_chunk_ids=[c.chunk_id for c in result.citations] if result.status == ANSWERED else [],
        model=settings.llm_model, prompt_version=PROMPT_VERSION, llm_calls=result.llm_calls,
        input_tokens=result.input_tokens, output_tokens=result.output_tokens,
        answer_chars=len(result.answer or ""), refusal_reason=None if result.status == ANSWERED else (result.reason or None),
    )
    db.add(row)
    return row


# ------------------------------------------------------------------ security events (written from security_event)

ID_ONLY_KEYS = (
    "document_id", "group_id", "rule_id", "job_id", "fields", "roles", "principal_type", "effect", "permission", "size", "kind",
)
AUDITED_PREFIXES = ("auth.", "admin.", "audit.")


def persist_access_event(event: str, request_id: str | None, fields: dict) -> None:  # type: ignore[type-arg]
    """Saves one security event. Only ids and fixed code words are kept. Never raises: a failure here is logged, and
    the business action it describes has already happened (the query trail is the one that fails closed)."""
    if not event.startswith(AUDITED_PREFIXES):
        return
    import logging

    try:
        actor, subject = fields.get("actor_id"), None
        if actor is not None:
            subject = fields.get("user_id")
        else:
            actor = fields.get("user_id")
        detail = {k: fields[k] for k in ID_ONLY_KEYS if fields.get(k) is not None}
        with SyncSession() as session:
            session.add(AccessEvent(
                event=event, actor_id=uuid.UUID(str(actor)) if actor else None,
                subject_id=uuid.UUID(str(subject)) if subject else None, detail=detail, request_id=request_id,
            ))
            session.commit()
    except Exception as exc:  # noqa: BLE001
        logging.getLogger("audit").error("access_event_write_failed type=%s", type(exc).__name__)


# ------------------------------------------------------------------ reading

def query_filters(
    user_id: uuid.UUID | None, kind: str | None, status: str | None, since: datetime | None, until: datetime | None,
    contains: str | None,
) -> list[ColumnElement[bool]]:
    conds: list[ColumnElement[bool]] = []
    if user_id:
        conds.append(QueryAuditLog.user_id == user_id)
    if kind:
        conds.append(QueryAuditLog.kind == kind)
    if status:
        conds.append(QueryAuditLog.response_status == status)
    if since:
        conds.append(QueryAuditLog.created_at >= since)
    if until:
        conds.append(QueryAuditLog.created_at < until)
    if contains:
        conds.append(QueryAuditLog.query_text.ilike("%" + contains.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%", escape="\\"))
    return conds


def queries_stmt(conds: list[ColumnElement[bool]]) -> Select:  # type: ignore[type-arg]
    return select(QueryAuditLog).where(and_(true(), *conds)).order_by(QueryAuditLog.created_at.desc(), QueryAuditLog.id)


async def count(db: AsyncSession, stmt: Select) -> int:  # type: ignore[type-arg]
    return await db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0


# ------------------------------------------------------------------ CSV (safe to open in a spreadsheet)

CSV_HEADER = ["time_utc", "who", "email", "type", "result", "question", "documents_readable", "passages_returned", "latency_ms", "search_mode", "reranked", "request_id"]


def csv_safe(value: object) -> str:
    """A cell that starts with = + - @ tab or return can run as a formula in a spreadsheet. A leading quote defuses it."""
    text = "" if value is None else str(value)
    return "'" + text if text[:1] in ("=", "+", "-", "@", "\t", "\r") else text


def csv_rows(rows: Iterator[QueryAuditLog], people: dict | None = None) -> Iterator[str]:  # type: ignore[type-arg]
    """One readable line per question. The file starts with a byte order mark so Excel shows special characters correctly."""
    people = people or {}
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(CSV_HEADER)
    yield "﻿" + buffer.getvalue()
    for r in rows:
        buffer.seek(0)
        buffer.truncate(0)
        who = people.get(r.user_id)
        writer.writerow([
            r.created_at.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
            csv_safe(who.full_name if who and who.full_name else f"Former user ({str(r.user_id)[:8]})"), csv_safe(who.email if who else ""),
            "Question" if r.kind == "CHAT" else "Search", csv_safe(r.response_status), csv_safe(r.query_text),
            r.allowed_doc_count, len(r.retrieved_chunk_ids), r.latency_ms,
            csv_safe(r.filters.get("mode", "")), "yes" if r.filters.get("rerank") else "no", csv_safe(r.request_id),
        ])
        yield buffer.getvalue()


def sync_rows(session: Session, stmt: Select, limit: int) -> Iterator[QueryAuditLog]:  # type: ignore[type-arg]
    yield from session.scalars(stmt.limit(limit))
