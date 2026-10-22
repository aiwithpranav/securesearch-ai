# ADR 032: Evaluation design and the refusal threshold (Phase 7B)

## Status
Accepted (2026-10-22). Part of the Phase 7 plan the owner approved ("do what you think right"). The owner can reverse any item.

## Context
Blueprint FR-14 and sections 3.4, 13.2, 13.3 and 23.3: an evaluation of 60+ cases must prove 0% leakage with canary strings, report Recall@5, citation correctness, refusal accuracy and latency, compare keyword, vector and hybrid search, and choose the refusal threshold by measurement (ADR 028 and 030 had set a provisional 0.03).

## Decision
- **Corpus:** 36 extra synthetic documents (`app/eval/corpus.py`) make 48 with the 12 from Phase 3: 8 departments, sensitivity 0 to 4, a unique canary in every document of sensitivity 2 or higher, access rules in the same compact form as the demo seed. They go into the development database through the real upload and ingestion (`load_eval_corpus`) and into the test database directly with real local embeddings.
- **62 cases** (`app/eval/cases.py`) in the blueprint's categories: authorized 20, unauthorized 10 (5 prompt-injection), missing information 5, exact keyword 5, paraphrase 8, scenarios 14.
- **Canary scanner** (`app/eval/scanner.py`): for each question, the set of documents the person may NOT read (from an independent plain-Python oracle, `app/eval/oracle.py`, not the SQL resolver) gives canaries, ids and titles. The API answers, the search results, the model prompt, the audit rows and the logs are scanned; the person's own question is removed first; the question text appearing in a log is a leak too. One hit fails the run.
- **Runner** (`app/eval/runner.py`): asks every case through the real HTTP application in-process, replacing only the sign-in check, so the real resolver, retrieval, answer engine, audit trail and logs are exercised. Scenarios change the database (revoke, remove from a group, expire, delete, switch a version, change clearance, country or status) and always undo it. Results hold ids, code words, numbers and the synthetic question, never an answer or document text.
- **Metrics:** leakage, Recall@5 and MRR of hybrid plus reranker, citation correctness, appropriate refusal accuracy, scenarios, P95 search and answer latency, and a table comparing keyword, vector, hybrid and hybrid plus reranker.
- **Fake model by default:** free, repeatable, usable in CI; a live run needs `--live --yes` (or `confirm_cost` in the API), a key and the estimated cost is shown first.
- **API** (`/evaluation/runs`, system administrator only): a run is a child process (`app.scripts.run_eval`), because replacing the sign-in check inside the running server would hijack real requests. One run at a time; not in production.
- **Tables** (migration `0007`): `eval_cases`, `eval_runs`, `eval_results`.
- **Refusal threshold 0.30** (was 0.03). Chosen on the 48 answer-or-refuse cases: it is the middle of the plateau where the most decisions are right (44 of 48); see `docs/evaluation-report.md`. Trade-off accepted: paraphrased questions whose best reranker score is below 0.30 get the uniform refusal although the right document is found.

## How it is proven
- 56 tests in `tests/test_eval.py` and `tests/test_eval_api.py` (corpus integrity, case integrity, scanner and metrics, a complete run in a test world with zero leakage and every change undone, planted leaks in each place the scanner covers, roles and limits of the API, saved runs, the command line).
- Mutation check: 14 deliberate mistakes (a scanned place dropped, the oracle ignoring deny or clearance, a scenario not undoing its change, recall computed wrongly, security staff or confirmation or concurrency or production guards removed); 13 caught, 1 equivalent (the API already guarantees what the refusal check also tests).
- A live pass on the development database with the real models: 62 of 62, 0 leaks.

## Consequences
- The leakage promise is now tested continuously: a change that lets forbidden text into any place breaks the test suite.
- The threshold change makes the product more cautious. Backlog 34 tracks improving the answer rate on paraphrases.
- The evaluation corpus lives in the development database as normal documents (49 with the owner's own upload); it can be removed from the Admin screen.
