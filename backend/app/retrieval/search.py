"""Authorized hybrid retrieval.

The order of work is the security design (ADR 028):
1. The access resolver builds the allow-list: ids of documents this person may READ (deny by default, DENY wins,
   clearance, country, expiry, document ready and not deleted).
2. Full-text search and vector search BOTH run only inside that allow-list, in SQL. Chunks of other documents are
   never read, never ranked, never held in memory.
3. RRF fuses the two ranked lists; the reranker reorders the best candidates; the top few are returned.
4. The final text is loaded with the allow-list applied AGAIN, so even a bug in steps 2 or 3 could not widen access.

Three modes share the SAME allow-list: keyword, vector, hybrid (setting RETRIEVAL_MODE). No mode can leak."""
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy import ColumnElement, and_, func, select, text
from sqlalchemy.orm import Session

from app.access.resolver import readable_ids_stmt
from app.core.config import settings
from app.embeddings import embed_query
from app.models import Document, DocumentChunk
from app.retrieval.fusion import rrf
from app.retrieval.reranker import get_reranker

MODES = ("keyword", "vector", "hybrid")
MAX_QUERY_CHARS = 500


@dataclass
class Hit:
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    document_title: str
    page_number: int | None
    section: str | None
    content: str
    score: float  # final ordering score: rerank score (0..1) when reranked, else RRF, ts_rank or 1 - distance
    scores: dict[str, float] = field(default_factory=dict)  # every signal that was computed, for explanations
    document_updated_at: datetime | None = None


def _allowed(user_id: uuid.UUID) -> ColumnElement[bool]:
    return and_(DocumentChunk.is_active.is_(True), DocumentChunk.document_id.in_(readable_ids_stmt(user_id)))


def clean_query(query: str) -> str:
    return " ".join(query.split())[:MAX_QUERY_CHARS]


def keyword_candidates(session: Session, user_id: uuid.UUID, query: str, limit: int) -> list[tuple[uuid.UUID, float]]:
    """Full-text search (PostgreSQL ts_rank_cd; this is NOT BM25). Odd input never raises an error."""
    # Questions are written in natural language, so ANY word may match (ranking prefers chunks that match more words).
    # Quotes and search operators are not supported: only the words are used. Stop words are dropped by Postgres.
    words = re.findall(r"\w+", query)
    if not words:
        return []
    tsquery = func.websearch_to_tsquery("english", " or ".join(words))
    rank = func.ts_rank_cd(DocumentChunk.tsv, tsquery)
    stmt = (
        select(DocumentChunk.id, rank.label("score"))
        .where(_allowed(user_id), DocumentChunk.tsv.op("@@")(tsquery))
        .order_by(rank.desc(), DocumentChunk.id)
        .limit(limit)
    )
    return [(row.id, float(row.score)) for row in session.execute(stmt)]


def vector_candidates(
    session: Session, user_id: uuid.UUID, query_vector: list[float], limit: int
) -> list[tuple[uuid.UUID, float]]:
    """Nearest chunks by cosine distance, inside the allow-list. pgvector 0.8 filters AFTER the index scan, so
    iterative scan keeps scanning until enough allowed rows are found (strict_order keeps the true order)."""
    session.execute(text("SET LOCAL hnsw.iterative_scan = strict_order"))
    session.execute(text("SET LOCAL hnsw.ef_search = 100"))
    distance = DocumentChunk.embedding.cosine_distance(query_vector)
    stmt = (
        select(DocumentChunk.id, distance.label("distance"))
        .where(_allowed(user_id))
        .order_by(distance, DocumentChunk.id)
        .limit(limit)
    )
    return [(row.id, 1.0 - float(row.distance)) for row in session.execute(stmt)]


def _load_hits(session: Session, user_id: uuid.UUID, chunk_ids: list[uuid.UUID]) -> dict[uuid.UUID, Hit]:
    """Loads the text of the chosen chunks, with the allow-list applied again (step 4)."""
    if not chunk_ids:
        return {}
    stmt = (
        select(
            DocumentChunk.id, DocumentChunk.document_id, Document.title, DocumentChunk.page_number,
            DocumentChunk.section, DocumentChunk.content, Document.updated_at,
        )
        .join(Document, Document.id == DocumentChunk.document_id)
        .where(DocumentChunk.id.in_(chunk_ids), _allowed(user_id))
    )
    return {
        r.id: Hit(r.id, r.document_id, r.title, r.page_number, r.section, r.content, 0.0, document_updated_at=r.updated_at)
        for r in session.execute(stmt)
    }


def retrieve(
    session: Session,
    user_id: uuid.UUID,
    query: str,
    mode: str | None = None,
    rerank: bool | None = None,
    final_k: int | None = None,
) -> list[Hit]:
    """Best chunks for this person and this question, best first. Empty when nothing is allowed or nothing matches.

    rerank=None means: rerank in hybrid mode only (the blueprint compares keyword, vector, hybrid and hybrid+rerank)."""
    mode = mode or settings.retrieval_mode
    if mode not in MODES:
        raise ValueError(f"Unknown retrieval mode: {mode}")
    query = clean_query(query)
    if not query:
        return []
    final_k = final_k or settings.retrieval_final_k
    if rerank is None:
        rerank = mode == "hybrid"

    signals: dict[uuid.UUID, dict[str, float]] = {}
    keyword: list[tuple[uuid.UUID, float]] = []
    vector: list[tuple[uuid.UUID, float]] = []
    if mode in ("keyword", "hybrid"):
        keyword = keyword_candidates(session, user_id, query, settings.retrieval_fts_limit)
        for rank, (cid, score) in enumerate(keyword, start=1):
            signals.setdefault(cid, {}).update(keyword_rank=float(rank), keyword_score=score)
    if mode in ("vector", "hybrid"):
        vector = vector_candidates(session, user_id, embed_query(query), settings.retrieval_vector_limit)
        for rank, (cid, score) in enumerate(vector, start=1):
            signals.setdefault(cid, {}).update(vector_rank=float(rank), vector_score=score)

    if mode == "keyword":
        ordered = [(cid, score) for cid, score in keyword]
    elif mode == "vector":
        ordered = [(cid, score) for cid, score in vector]
    else:
        ordered = rrf([[c for c, _ in keyword], [c for c, _ in vector]], k=settings.retrieval_rrf_k)
        for cid, score in ordered:
            signals[cid]["rrf_score"] = score

    candidates = [cid for cid, _ in ordered[: settings.retrieval_rerank_candidates if rerank else final_k]]
    hits = _load_hits(session, user_id, candidates)
    base_score = dict(ordered)
    result = [hits[cid] for cid in candidates if cid in hits]
    for hit in result:
        hit.scores = signals[hit.chunk_id]
        hit.score = base_score[hit.chunk_id]

    if rerank and result:
        scores = get_reranker().score(query, [h.content for h in result])
        for hit, score in zip(result, scores, strict=True):
            hit.scores["rerank_score"] = score
            hit.score = score
        result.sort(key=lambda h: (-h.score, str(h.chunk_id)))
    return result[:final_k]
