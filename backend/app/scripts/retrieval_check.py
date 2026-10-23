"""Quick retrieval measurement on the 12 demo documents (a smoke check, NOT the Phase 7 evaluation).

Run:  docker compose exec backend python -m app.scripts.retrieval_check

It asks 20 labelled questions as one demo person (default shivam@demo, clearance 4) in four set-ups and prints
Recall@5 (is the right document in the top 5 chunks?) and MRR (how high is it?). It also prints the reranker score of
the best chunk for off-topic questions, which is how the refusal threshold for Phase 6 is chosen.
Needs the demo data (seed_users, load_demo_documents, seed_access). Reads only; changes nothing."""
import sys
import time

from sqlalchemy import select

from app.access.resolver import readable_ids_stmt
from app.db.sync import SyncSession
from app.models import Document, User
from app.retrieval import search

QUESTIONS = [
    ("How many days of annual leave do employees get?", "Leave policy"),
    ("How can unused leave be carried over?", "Leave policy"),
    ("How much paid time off do I get per year?", "Leave policy"),
    ("When is Republic Day?", "Company holiday calendar 2026"),
    ("What should I do when the payments error rate is high?", "Payments service runbook"),
    ("Who do I page when the service is failing?", "Payments service runbook"),
    ("What is the maximum discount a sales executive can give?", "Pricing playbook"),
    ("How big a price reduction may a rep offer?", "Pricing playbook"),
    ("What is the salary range of band L3?", "Salary bands 2026"),
    ("What are the compensation grades?", "Salary bands 2026"),
    ("Should I click links in unexpected emails?", "Security awareness basics"),
    ("Where do I report suspicious emails?", "Security awareness basics"),
    ("When must a customer problem be escalated?", "Support escalation guide"),
    ("A customer has been blocked for several hours, what now?", "Support escalation guide"),
    ("What happened in the phishing incident in July?", "Incident report July 2026"),
    ("What are the operating costs in the budget forecast?", "FY2026 budget forecast"),
    ("What do I do in my first week and how do I set up my laptop?", "Employee onboarding guide"),
    ("What are the office timings and lunch time?", "text.txt"),
    ("Summarise the vendor contract.", "Vendor contract summary"),
    ("Which day did the team meeting move to?", "Team note (contains an injection test)"),
]
OFF_TOPIC = [
    "recipe for chocolate cake", "who won the football world cup", "how tall is Mount Everest",
    "best way to learn the guitar", "weather forecast for tomorrow",
]
SETUPS = [("keyword", "keyword", False), ("vector", "vector", False), ("hybrid", "hybrid", False), ("hybrid+rerank", "hybrid", True)]


def main(email: str = "shivam@demo") -> None:
    with SyncSession() as s:
        user = s.scalar(select(User.id).where(User.email == email))
        if user is None:
            sys.exit(f"{email} not found: load the demo data first.")
        search.retrieve(s, user, "warm up", mode="hybrid")  # load the models once, outside the timings
        readable = set(s.scalars(select(Document.title).where(Document.id.in_(readable_ids_stmt(user)))))
        questions = [(q, t) for q, t in QUESTIONS if t in readable]  # a person cannot find what they may not read
        print(f"{email} may read {len(readable)} documents; {len(questions)} of {len(QUESTIONS)} questions apply.")
        print(f"{'set-up':14} Recall@5  MRR    median ms")
        for label, mode, rerank in SETUPS:
            hit_at_5, rr, times = 0, 0.0, []
            for question, expected in questions:
                t = time.time()
                chunks = search.retrieve(s, user, question, mode=mode, rerank=rerank, final_k=5)
                times.append((time.time() - t) * 1000)
                titles = [c.document_title for c in chunks]
                if expected in titles:
                    hit_at_5 += 1
                    rr += 1.0 / (titles.index(expected) + 1)
            print(f"{label:14} {hit_at_5 / len(questions):8.2f}  {rr / len(questions):.2f}   {sorted(times)[len(times) // 2]:7.0f}")

        def best_score(question: str) -> float:
            chunks = search.retrieve(s, user, question, mode="hybrid", rerank=True, final_k=1)
            return chunks[0].score if chunks else 0.0

        on = sorted(best_score(q) for q, _ in questions)
        off = sorted(best_score(q) for q in OFF_TOPIC)
        print(f"\nBest rerank score, on-topic questions: min {on[0]:.3f}, 10th percentile {on[len(on) // 10]:.3f}, median {on[len(on) // 2]:.3f}")
        print(f"Best rerank score, off-topic questions: max {off[-1]:.3f}, median {off[len(off) // 2]:.3f}")


if __name__ == "__main__":
    main(*sys.argv[1:2])
