"""Grounded answers with citations (Phase 6A). The order of work is the security design (ADR 030):

1. Retrieval (Phase 5): the access resolver builds the allow-list first; searches run only inside it.
2. Second wall: every chosen passage is checked against the resolver again (defence in depth).
3. Confidence: when even the best passage is a weak match, we refuse WITHOUT calling the language model.
4. The model receives only those passages, marked as untrusted data. It has no tools.
5. Everything it returns is validated: exact JSON shape, citations only to passages it was given, no links or HTML.
6. Anything wrong gives the same uniform refusal as "nothing found", so a refusal never reveals whether a restricted
   document exists. The reason is logged as a code word, never with text.

No answer text leaves this module before step 5 has passed."""
import logging
import re
import time
import uuid
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.access.resolver import can
from app.answers.prompt import SYSTEM_PROMPT, build_user_message, source_id
from app.answers.validator import parse, validate
from app.core.config import settings
from app.llm import LlmClient, LlmError, get_llm
from app.retrieval.search import Hit, clean_query, retrieve

ANSWERED = "ANSWERED"
REFUSED_NO_ACCESS_EVIDENCE = "REFUSED_NO_ACCESS_EVIDENCE"
REFUSED_LOW_CONFIDENCE = "REFUSED_LOW_CONFIDENCE"

# One text for every refusal, whatever the reason (blueprint 9.5 T6).
REFUSAL_TEXT = "Could not find enough accessible source material to answer this question."

logger = logging.getLogger("answers")


@dataclass
class Citation:
    source_id: str
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    document_title: str
    section: str | None
    page: int | None
    snippet: str
    document_updated_at: object | None


@dataclass
class AnswerResult:
    status: str
    answer: str | None
    citations: list[Citation] = field(default_factory=list)
    # For logs and tests only (code words and numbers, never text). The API does not return these.
    reason: str = ""
    llm_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    took_ms: int = 0


def _snippet(text: str, limit: int = 240) -> str:
    flat = re.sub(r"\s+", " ", text).strip()
    return flat if len(flat) <= limit else flat[:limit].rsplit(" ", 1)[0] + "…"


def _refuse(status: str, reason: str, started: float, calls: int = 0, tokens: tuple[int, int] = (0, 0)) -> AnswerResult:
    return AnswerResult(
        status, None, reason=reason, llm_calls=calls, input_tokens=tokens[0], output_tokens=tokens[1],
        took_ms=int((time.perf_counter() - started) * 1000),
    )


def _still_allowed(session: Session, user_id: uuid.UUID, hits: list[Hit]) -> bool:
    """Second wall: ask the resolver again for every document behind the chosen passages."""
    return all(can(session, user_id, doc_id) for doc_id in {h.document_id for h in hits})


def answer_question(session: Session, user_id: uuid.UUID, question: str, llm: LlmClient | None = None) -> AnswerResult:
    started = time.perf_counter()
    question = clean_query(question)
    if not question:
        raise ValueError("empty question")

    hits = retrieve(session, user_id, question, mode="hybrid", rerank=True, final_k=settings.answer_context_chunks)
    if not hits:
        return _refuse(REFUSED_NO_ACCESS_EVIDENCE, "NO_HITS", started)
    if not _still_allowed(session, user_id, hits):
        logger.error("answer_blocked reason=LEAK_GUARD", extra={"fields": {"user_id": str(user_id)}})
        return _refuse(REFUSED_NO_ACCESS_EVIDENCE, "LEAK_GUARD", started)
    if max(h.score for h in hits) < settings.answer_min_score:
        return _refuse(REFUSED_LOW_CONFIDENCE, "WEAK_EVIDENCE", started)
    hits = [h for h in hits if h.score >= settings.answer_min_score]  # drop passages that are only noise

    client = llm or get_llm()
    user_message = build_user_message(question, hits)
    allowed_ids = {source_id(i) for i in range(len(hits))}
    calls = in_tokens = out_tokens = 0
    verdict_reason = "MALFORMED_OUTPUT"
    parsed = None
    for _attempt in range(2):  # one retry if the reply is not in the required shape
        try:
            result = client.complete(SYSTEM_PROMPT, user_message, settings.llm_max_output_tokens)
        except LlmError as exc:
            logger.warning("llm_failed code=%s", exc, extra={"fields": {"user_id": str(user_id)}})
            raise
        calls += 1
        in_tokens += result.input_tokens
        out_tokens += result.output_tokens
        parsed = parse(result.text)
        if parsed is None:
            verdict_reason = "MALFORMED_OUTPUT"
            continue
        verdict = validate(parsed, allowed_ids)
        verdict_reason = verdict.reason
        if verdict.ok:
            break
        parsed = None
    tokens = (in_tokens, out_tokens)
    if parsed is None:
        logger.warning("answer_blocked reason=%s", verdict_reason, extra={"fields": {"user_id": str(user_id), "llm_calls": calls}})
        return _refuse(REFUSED_LOW_CONFIDENCE, verdict_reason, started, calls, tokens)
    if not parsed.can_answer:
        return _refuse(REFUSED_LOW_CONFIDENCE, "MODEL_DECLINED", started, calls, tokens)

    used = set(parsed.citations) | set(re.findall(r"\[(S\d+)\]", parsed.answer))
    citations = [
        Citation(
            source_id(i), h.chunk_id, h.document_id, h.document_title, h.section, h.page_number,
            _snippet(h.content), h.document_updated_at,
        )
        for i, h in enumerate(hits)
        if source_id(i) in used
    ]
    return AnswerResult(
        ANSWERED, parsed.answer, citations, llm_calls=calls, input_tokens=in_tokens, output_tokens=out_tokens,
        took_ms=int((time.perf_counter() - started) * 1000),
    )
