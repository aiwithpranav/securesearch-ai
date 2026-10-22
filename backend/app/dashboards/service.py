"""Numbers for the dashboards (Phase 7C). Aggregates only.

Privacy rules, in the order they matter:
- The admin overview holds counts, percentages and times. No question text, no document text, no names.
- Knowledge gaps show the questions people could not get an answer to, normalised and counted, with emails, links
  and long numbers masked, and WITHOUT who asked them (only how many different people did).
- Suggested questions for a person are built only from the titles of documents that person may read."""
import re
import uuid
from collections import defaultdict

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.access.resolver import readable_ids_stmt
from app.models import Document

REFUSED = ("REFUSED_LOW_CONFIDENCE", "REFUSED_NO_ACCESS_EVIDENCE")
GAP_WINDOW_DAYS = 30
GAP_SCAN_LIMIT = 5000  # the most recent unanswered questions that are looked at
GAP_TOP = 20

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", re.IGNORECASE)
_LINK = re.compile(r"(?:https?://|www\.)\S+", re.IGNORECASE)
_PHONE = re.compile(r"\+?\d[\d\s().-]{7,}\d")
_LONG_NUMBER = re.compile(r"\d{6,}")
_SPACES = re.compile(r"\s+")
_PUNCT = re.compile(r"[^a-z0-9\[\] ]+")


def normalise_question(question: str) -> str:
    """The same question asked in slightly different ways counts as one; personal details are masked first."""
    t = _EMAIL.sub(" [email] ", question)
    t = _LINK.sub(" [link] ", t)
    t = _PHONE.sub(" [number] ", t)
    t = _LONG_NUMBER.sub(" [number] ", t)
    t = _PUNCT.sub(" ", t.lower())
    return _SPACES.sub(" ", t).strip()[:160]


async def admin_overview(db: AsyncSession) -> dict:  # type: ignore[type-arg]
    rows = lambda sql, **p: db.execute(text(sql), p)  # noqa: E731
    by_status = {r.status: r.n for r in await rows("select status, count(*) n from documents where deleted_at is null group by status")}
    people = (await rows("select count(*) filter (where is_active) active, count(*) total from users")).one()
    groups = (await rows("select count(*) n from groups")).scalar() or 0
    days = [
        {"day": r.day.isoformat(), "searches": r.searches, "questions": r.questions, "answered": r.answered}
        for r in await rows(
            "select d::date as day, count(q.id) filter (where q.kind = 'SEARCH') searches, count(q.id) filter (where q.kind = 'CHAT') questions, "
            "count(q.id) filter (where q.response_status = 'ANSWERED') answered "
            "from generate_series(current_date - 6, current_date, interval '1 day') d "
            "left join query_audit_logs q on q.created_at >= d and q.created_at < d + interval '1 day' group by 1 order by 1"
        )
    ]
    outcome = {r.response_status: r.n for r in await rows(
        "select response_status, count(*) n from query_audit_logs where kind = 'CHAT' and created_at >= now() - interval '30 days' group by 1")}
    answered, refused = outcome.get("ANSWERED", 0), sum(outcome.get(s, 0) for s in REFUSED)
    reasons = {r.refusal_reason: r.n for r in await rows(
        "select refusal_reason, count(*) n from answer_audit_logs where refusal_reason is not null and created_at >= now() - interval '30 days' group by 1 order by n desc")}
    latency = {r.kind: round(r.p95) for r in await rows(
        "select kind, percentile_cont(0.95) within group (order by latency_ms) p95 from query_audit_logs where created_at >= now() - interval '30 days' group by kind")}
    feedback = (await rows("select count(*) filter (where rating = 1) up, count(*) filter (where rating = -1) down from chat_feedback")).one()
    changes = (await rows("select count(*) n from permission_change_events where changed_at >= now() - interval '7 days'")).scalar() or 0
    failed_jobs = (await rows("select count(*) n from ingestion_jobs where status = 'FAILED' and created_at >= now() - interval '7 days'")).scalar() or 0
    latest_eval = (await rows("select started_at, status, total, passed, leak_count from eval_runs order by started_at desc limit 1")).first()
    return {
        "documents_by_status": by_status,
        "documents_total": sum(by_status.values()),
        "people_active": people.active, "people_total": people.total, "groups": groups,
        "per_day": days,
        "answers": {"answered": answered, "refused": refused, "unavailable": outcome.get("UNAVAILABLE", 0),
                    "refusal_rate": round(refused / (answered + refused), 3) if answered + refused else None},
        "refusal_reasons": reasons,
        "p95_latency_ms": latency,
        "feedback": {"up": feedback.up, "down": feedback.down, "helpful_rate": round(feedback.up / (feedback.up + feedback.down), 3) if feedback.up + feedback.down else None},
        "permission_changes_7d": changes,
        "failed_ingestions_7d": failed_jobs,
        "latest_evaluation": None if latest_eval is None else {
            "started_at": latest_eval.started_at.isoformat(), "status": latest_eval.status, "total": latest_eval.total,
            "passed": latest_eval.passed, "leak_count": latest_eval.leak_count,
        },
        "window_days": 30,
    }


async def knowledge_gaps(db: AsyncSession) -> list[dict]:  # type: ignore[type-arg]
    rows = (await db.execute(
        text("select user_id, query_text, created_at from query_audit_logs where kind = 'CHAT' and response_status = any(:s) "
             "and created_at >= now() - make_interval(days => :d) order by created_at desc limit :n"),
        {"s": list(REFUSED), "d": GAP_WINDOW_DAYS, "n": GAP_SCAN_LIMIT},
    )).all()
    groups: dict[str, dict] = defaultdict(lambda: {"asked": 0, "people": set(), "last_asked": None})  # type: ignore[type-arg]
    for r in rows:
        norm = normalise_question(r.query_text)
        if not norm:
            continue
        g = groups[norm]
        g["asked"] += 1
        g["people"].add(r.user_id)
        if g["last_asked"] is None or r.created_at > g["last_asked"]:
            g["last_asked"] = r.created_at
    ranked = sorted(groups.items(), key=lambda kv: (-kv[1]["asked"], -kv[1]["last_asked"].timestamp()))
    return [
        {"question": q, "asked": g["asked"], "people": len(g["people"]), "last_asked": g["last_asked"].isoformat(),
         "suggested_action": "Add or update a document that answers this, then check the access rules."}
        for q, g in ranked[:GAP_TOP]
    ]


async def suggested_questions(db: AsyncSession, user_id: uuid.UUID, limit: int = 5) -> list[str]:
    """Ideas for what to ask, from the titles of the documents this person may read (most recently updated first)."""
    titles = (await db.scalars(
        select(Document.title).where(Document.id.in_(readable_ids_stmt(user_id))).order_by(Document.updated_at.desc(), Document.title).limit(limit)
    )).all()
    return [f"What does the {t} say?" for t in titles]
