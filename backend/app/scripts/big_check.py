"""Checks the scale demo: is every document indexed, how fast is search, and does anything leak? (Phase 10)

Run inside the backend container of the SEPARATE big stack:
    python -m app.scripts.big_check --status        # how far the worker is
    python -m app.scripts.big_check                 # latency + leak check, prints a report (exit code 1 on any leak)

The leak check uses the canary markers the loader put into restricted documents. For people who must NOT read a
document it searches for that document's marker and checks that nothing of it comes back. Which documents a person
may read is decided by an independent plain-Python oracle (app/scale/oracle.py), not by the SQL resolver. On top of
that, EVERY hit of EVERY query is checked against the oracle. One single violation fails the run.
Nothing is changed in the database. Synthetic people and public documents only."""
import argparse
import json
import random
import statistics
import sys
import time
from typing import Any

from sqlalchemy import text

from app.core.config import settings
from app.db.sync import SyncSession
from app.retrieval.search import retrieve
from app.scale.corpus import CANARY_PREFIX
from app.scale.oracle import FastOracle

PERSONAS = ["swara@demo", "pranav@demo", "dhanashree@demo", "akshay@demo", "sanjana@demo", "shivam@demo", "prashant@demo", "karunesh@demo"]
MODES = [("keyword", "keyword", False), ("vector", "vector", False), ("hybrid", "hybrid", False), ("hybrid + reranker (default)", "hybrid", True)]


def status(session) -> dict:  # type: ignore[no-untyped-def]
    docs = dict(session.execute(text("select status, count(*) from documents where deleted_at is null group by status")).all())
    chunks = session.execute(text("select count(*) from document_chunks where is_active")).scalar()
    users = session.execute(text("select count(*) from users where email like 'big%@demo'")).scalar()
    rules = session.execute(text("select count(*) from document_acl")).scalar()
    return {"documents": docs, "total_documents": sum(docs.values()), "active_passages": chunks, "synthetic_people": users, "access_rules": rules}


def _pct(values: list[float], p: int) -> float:
    if not values:
        return 0.0
    if len(values) < 20:
        return max(values)
    return statistics.quantiles(values, n=100)[p - 1]


class Report:
    def __init__(self) -> None:
        self.violations: list[dict] = []
        self.queries = 0

    def check_hits(self, oracle: FastOracle, user_id, hits, forbidden_canary: str | None, forbidden_doc, label: str) -> None:  # noqa: ANN001
        self.queries += 1
        for h in hits:
            if not oracle.can_read(user_id, h.document_id):
                self.violations.append({"kind": "UNREADABLE_HIT", "user": str(user_id), "document": str(h.document_id), "query": label})
            if forbidden_doc is not None and h.document_id == forbidden_doc:
                self.violations.append({"kind": "FORBIDDEN_DOCUMENT", "user": str(user_id), "document": str(h.document_id), "query": label})
            if forbidden_canary and forbidden_canary in h.content:
                self.violations.append({"kind": "CANARY_IN_HIT", "user": str(user_id), "document": str(h.document_id), "query": label})


def run(args: argparse.Namespace) -> int:
    rng = random.Random(args.seed)
    with SyncSession() as s:
        st = status(s)
        print(json.dumps(st))
        if args.status:
            return 0
        not_ready = st["total_documents"] - st["documents"].get("READY", 0)
        if not_ready and not args.allow_partial:
            print(f"{not_ready} document(s) are not READY yet (the worker is still indexing, or some failed). "
                  "Run with --status to follow it, or --allow-partial to check what is ready.")
            return 2
        oracle = FastOracle(s)
        big = [e for e in oracle.by_email if e.startswith("big")]
        people = [e for e in PERSONAS if e in oracle.by_email] + rng.sample(big, min(args.people, len(big)))
        marked = s.execute(text(
            "select distinct on (document_id) document_id, substring(content from :pat) as canary from document_chunks "
            "where is_active and content like :like"), {"pat": CANARY_PREFIX + "[0-9A-F]{8}", "like": f"%{CANARY_PREFIX}%"}).all()
        titles = s.execute(text("select title from documents where status='READY' and deleted_at is null order by random() limit :n"), {"n": args.latency_queries}).scalars().all()
        report = Report()
        for _label, mode, rerank in MODES:  # load the models and warm the caches, so the first call is not counted
            retrieve(s, oracle.by_email[people[0]], "warm up", mode=mode, rerank=rerank)

        # 1. Latency per search mode on natural questions (titles of real pages)
        latency: dict[str, list[float]] = {}
        for label, mode, rerank in MODES:
            times = []
            for title in titles:
                uid = oracle.by_email[rng.choice(people)]
                t0 = time.perf_counter()
                hits = retrieve(s, uid, f"What does the documentation say about {title}?", mode=mode, rerank=rerank)
                times.append((time.perf_counter() - t0) * 1000)
                report.check_hits(oracle, uid, hits, None, None, f"latency:{mode}")
            latency[label] = times
            print(f"latency {label}: median {statistics.median(times):.0f} ms, P95 {_pct(times, 95):.0f} ms", flush=True)

        # 2. Leak check: marker of a document the person may NOT read
        forbidden_pairs: list[tuple] = []
        allowed_pairs: list[tuple] = []
        for _ in range(args.pairs * 50):
            if len(forbidden_pairs) >= args.pairs and len(allowed_pairs) >= args.allowed_pairs:
                break
            email, row = rng.choice(people), rng.choice(marked)
            uid = oracle.by_email[email]
            (allowed_pairs if oracle.can_read(uid, row.document_id) else forbidden_pairs).append((uid, row))
        forbidden_pairs, allowed_pairs = forbidden_pairs[: args.pairs], allowed_pairs[: args.allowed_pairs]
        for uid, row in forbidden_pairs:
            hits = retrieve(s, uid, f"Internal reference marker {row.canary}", mode="hybrid", rerank=True)
            report.check_hits(oracle, uid, hits, row.canary, row.document_id, "forbidden-canary")
        found = 0
        for uid, row in allowed_pairs:
            hits = retrieve(s, uid, f"Internal reference marker {row.canary}", mode="hybrid", rerank=True)
            report.check_hits(oracle, uid, hits, None, None, "allowed-canary")
            found += any(h.document_id == row.document_id for h in hits)

    rep: dict[str, Any] = {
        "status": st, "people_sampled": len(people), "marked_documents": len(marked), "queries": report.queries,
        "forbidden_pairs": len(forbidden_pairs), "allowed_pairs": len(allowed_pairs),
        "allowed_found_in_top": f"{found}/{len(allowed_pairs)}", "violations": len(report.violations),
        "latency_ms": {k: {"median": round(statistics.median(v)), "p95": round(_pct(v, 95))} for k, v in latency.items()},
        "settings": {"final_k": settings.retrieval_final_k, "rerank_candidates": settings.retrieval_rerank_candidates},
    }
    print(json.dumps(rep, indent=2))
    print("\n| Measure | Result |\n|---|---|")
    print(f"| Documents / passages | {st['total_documents']} / {st['active_passages']} |")
    print(f"| People (synthetic) / access rules | {st['synthetic_people']} / {st['access_rules']} |")
    for k, v in rep["latency_ms"].items():
        print(f"| Search {k}: median / P95 | {v['median']} ms / {v['p95']} ms |")
    print(f"| Forbidden-marker searches (must find nothing) | {len(forbidden_pairs)} |")
    print(f"| Allowed-marker searches found in the top results | {rep['allowed_found_in_top']} |")
    print(f"| Queries checked against the oracle | {report.queries} |")
    print(f"| **Leaks / violations** | **{len(report.violations)}** |")
    for v in report.violations[:10]:
        print("VIOLATION", json.dumps(v))
    return 1 if report.violations else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--status", action="store_true", help="only show how many documents are indexed")
    parser.add_argument("--allow-partial", action="store_true", help="check even if some documents are not READY")
    parser.add_argument("--people", type=int, default=40, help="synthetic people sampled (the 8 demo people are always included)")
    parser.add_argument("--latency-queries", type=int, default=60)
    parser.add_argument("--pairs", type=int, default=300, help="searches by people who must NOT read a marked document")
    parser.add_argument("--allowed-pairs", type=int, default=100)
    parser.add_argument("--seed", type=int, default=10)
    sys.exit(run(parser.parse_args()))
