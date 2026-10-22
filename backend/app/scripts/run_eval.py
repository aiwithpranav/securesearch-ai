"""Runs the evaluation (62 cases) against the database this container uses and prints the result.

    docker compose exec backend python -m app.scripts.run_eval                  # fake model: free, repeatable
    docker compose exec backend python -m app.scripts.run_eval --save           # also keep the run in the database
    docker compose exec backend python -m app.scripts.run_eval --live --yes     # REAL model: asks 70+ questions, costs cents

Needs the demo people, the 48 documents and their rules (seed_users, load_synthetic_docs, seed_access,
load_eval_corpus). Exit code: 0 all passed, 1 a leak was found, 2 some other case failed.
A live run needs OPENAI_API_KEY in .env and the flag --yes, after the estimated cost has been shown."""
import argparse
import sys
import uuid

from app.core.config import settings
from app.eval.runner import create_run_row, estimate_live_cost, fail_run_row, finish_run_row, render_markdown, run_suite
from app.llm import LlmNotConfigured, get_llm


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--live", action="store_true", help="use the real model (costs money)")
    p.add_argument("--yes", action="store_true", help="confirm the cost of a live run")
    p.add_argument("--save", action="store_true", help="keep the run in the database")
    p.add_argument("--run-id", help="an existing run row to fill (used by the API)")
    p.add_argument("--label", default="manual run")
    args = p.parse_args(argv)
    if settings.app_env == "production":
        print("Refusing to run the evaluation when APP_ENV is production.")
        return 1
    if args.live:
        est = estimate_live_cost()
        print(f"A live run asks about {est['questions']} questions. Estimated cost: about ${est['estimated_usd']} (GPT-4o mini).")
        try:
            get_llm()
        except LlmNotConfigured:
            print("No OPENAI_API_KEY is set in .env, so a live run is not possible.")
            return 3
        if not args.yes:
            print("Add --yes to run it.")
            return 3
    run_id = uuid.UUID(args.run_id) if args.run_id else (create_run_row(args.label, "LIVE_MODEL" if args.live else "FAKE_MODEL", None) if args.save else None)
    try:
        report = run_suite(live=args.live, progress=lambda i, n, cid: print(f"\r{i}/{n} {cid}   ", end="", flush=True))
    except Exception as exc:  # noqa: BLE001
        if run_id:
            fail_run_row(run_id, type(exc).__name__)
        print(f"\nThe evaluation could not run: {type(exc).__name__}: {exc}")
        return 4
    print("\n" + render_markdown(report))
    if run_id:
        finish_run_row(run_id, report)
        print(f"\nSaved as run {run_id}.")
    return 1 if report.leak_count else (0 if report.passed == len(report.results) else 2)


if __name__ == "__main__":
    sys.exit(main())
