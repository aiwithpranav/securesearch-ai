"""Builds the whole 48-document evaluation world inside the TEST database: the demo people, their groups, every
document with its passages (real local embeddings) and every access rule. The development database gets the same
world through the real upload and ingestion instead."""
import re

from app.db.sync import SyncSession
from app.eval.corpus import ALL_RULES, ALL_SAMPLES
from app.eval.loader import apply_rules, chunks_for
from app.scripts.seed_access import GROUPS
from app.scripts.seed_users import DEPARTMENTS, USERS
from tests.access_world import World
from tests.retrieval_world import add_chunks


class StrictOverlapReranker:
    """A fast stand-in for the real reranker. A passage scores high only when it shares at least two longer words with
    the question and covers most of them; otherwise it scores 0 (below the confidence gate). Ties keep the search order."""

    def score(self, query, passages):
        stem = lambda w: w[:5]  # a crude stem, so "approve" and "approved" match  # noqa: E731
        words = {stem(w) for w in re.findall(r"[a-z0-9]+", query.lower()) if len(w) > 3}
        out = []
        for i, p in enumerate(passages):
            have = words & {stem(w) for w in re.findall(r"[a-z0-9]+", p.lower())}
            ratio = len(have) / len(words) if words else 0.0
            out.append((ratio if len(have) >= 2 and ratio >= 0.4 else 0.0) + max(0.0, 0.001 - i * 1e-5))
        return out


def build(pg):
    """Returns the World. Call once per test (the autouse cleanup empties the database before every test)."""
    for name in DEPARTMENTS:
        if not pg.execute("select 1 from departments where name=%s", (name,)).fetchone():
            pg.execute("insert into departments (name) values (%s)", (name,))
    w = World(pg)
    members: dict[str, list[str]] = {}
    for group, emails in GROUPS.items():
        for email in emails:
            members.setdefault(email, []).append(group)
    for group in GROUPS:
        w.group_id(group)
    for email, _name, dept, clearance, country, _emp, roles, active in USERS:
        w.user(email=email, dept=dept, clearance=clearance, country=country, active=active, roles=tuple(roles), groups=tuple(members.get(email, ())))
    for s in ALL_SAMPLES:
        doc = pg.execute(
            "insert into documents (title, original_filename, document_type, department_id, sensitivity_level, status, uploaded_by)"
            " values (%s,%s,%s,%s,%s,'READY',%s) returning id",
            (s.title, s.filename, s.document_type, w.dept_id(s.department), s.sensitivity, w.uploader),
        ).fetchone()[0]
        add_chunks(pg, doc, [text for _heading, text in chunks_for(s)])
    with SyncSession.begin() as session:
        apply_rules(session, ALL_RULES)
    return w
