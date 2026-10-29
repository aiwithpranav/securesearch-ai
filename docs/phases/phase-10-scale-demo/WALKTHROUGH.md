# Phase 10 Walkthrough

## Layer 10A: scale demo

### 1. What we built
A way to run the system on a large body of real documents and many people, and to prove two things with numbers: search stays fast enough, and nothing leaks. It runs as a second, separate copy of the system, so the normal demo is never touched, and it can be deleted when the space is needed. The scripts and the results record stay in the repository; the data does not.

### 2. How it works, step by step
1. **Download** (`scripts/big/download.sh`): a shallow, sparse Git clone of three public documentation sources; only the Markdown pages are copied to a folder outside the repository (`BIG_DATA_DIR`).
2. **Second stack** (`docker-compose.big.yml` with `-p securesearch-big`): own database, file store and ports (API 18000, mailbox 18025); the folder is mounted read-only; the worker runs three processes.
3. **Load** (`app.scripts.big_load`):
   - creates the synthetic people (`big0001@demo` ...): a department, roles, a clearance level and a country each, all with the demo password (hashed once);
   - cleans every page (front matter, site-generator shortcodes and comments removed; very short pages skipped), places it by its path (for example GitLab `people-group` is HR, sensitivity 2; `security` is Security, sensitivity 3; Kubernetes and Docker are Engineering, sensitivity 1);
   - adds a canary marker to every restricted page and to about one in twenty others;
   - uploads each page through the real upload service, then adds access rules (the owning team by role, executives too for restricted pages).
   The worker then parses, chunks and embeds the pages in the background.
4. **Check** (`app.scripts.big_check`): `--status` follows the indexing. The full check measures search time per mode (keyword, vector, hybrid, hybrid with reranker) on natural questions, then searches for the marker of documents that a sampled person must NOT read. An independent oracle decides who may read what; every hit of every query is checked against it. One violation fails the run (exit code 1).
5. **Clean up**: `docker compose -p securesearch-big -f docker-compose.yml -f docker-compose.big.yml down -v` removes the database and file store of the big stack. The normal stack is not affected.

### 3. Important files
`docker-compose.big.yml`, `scripts/big/download.sh`, `backend/app/scale/` (`corpus.py`, `people.py`, `oracle.py`), `backend/app/scripts/big_load.py`, `big_check.py`, `backend/tests/test_scale.py`, `docs/adr/039-scale-demo.md`, `docs/phases/phase-10-scale-demo/RESULTS.md`.

### 4. Tools: why we chose them
Shallow sparse Git clones (only the needed folder, no history); the existing upload and ingestion path (the real pipeline is what is being measured); canary markers and an independent oracle (the same method as the evaluation, now at volume); a separate Compose project name (separate volumes and a one-command delete).

### 5. How to run it
See `RESULTS.md` ("How to recreate this run"). Short form: `bash scripts/big/download.sh`, set `BIG_DATA_DIR`, start the big stack, `alembic upgrade head`, `seed_users`, `big_load`, wait, `big_check`.

### 6. How to test it
`docker compose exec backend python -m pytest tests/test_scale.py -q` (27 tests: placement, cleaning, canaries, people, and the fast oracle against the SQL resolver in random worlds).

### 7. Actual results (checked by me)
- Trial in a throw-away stack: 30 files, 200 people, 60 passages, 41 rules. Indexing finished; `big_check`: 93 queries checked against the oracle, 0 violations; the marker of an allowed document was found for 15 of 15 searches.
- A deliberate mistake in the resolver (the clearance check always true) was injected: `big_check` reported 33 violations. The check can fail.
- **Full run (2026-10-29):** 5,850 real documents, 90,956 passages, 1,000 people, 6,479 rules; indexing about 1 h 50 min; database 507 MB; 1,040 queries checked against the oracle: **0 violations**. Search without the reranker: P95 under half a second. Default search with the reranker: median 4.6 s, P95 5.4 s (above the 5 s target on this laptop). Exact-identifier search is weak at this size (25 of 100). Details and causes: `RESULTS.md`.

### 8. Limitations and open issues
- It found three weaknesses that are recorded, not fixed (backlog 55, 56, 57): exact-identifier search, search time with the reranker, and answers with command lines refused by the validator.
- It is a laptop test: it shows behaviour at volume on one machine, not high availability or cloud scale (`docs/scale-and-limits.md`).
- Natural-question latency uses page titles as questions; it measures speed, not answer quality.
- The marker search is a leak test, not a relevance test.
- Documents are public, English, Markdown only; scanned and table-heavy PDFs are not part of this run.
