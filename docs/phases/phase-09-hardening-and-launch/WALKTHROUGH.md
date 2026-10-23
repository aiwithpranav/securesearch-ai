# Phase 9 Walkthrough

## Layer 9A: quality gates and CI

### 1. What we built
An automatic checker that runs on every pull request. It is the project's "quality guard": style, types, tests, the leak test, known-vulnerability scans and a secret scan. If anything is wrong, the pull request shows a red check and must not be merged.

### 2. How it works, step by step
1. **You open a pull request** on GitHub. GitHub starts the workflow `.github/workflows/ci.yml` on a fresh machine.
2. **In parallel:** backend lint (ruff), frontend (ESLint, TypeScript, tests, build), a scan of the whole git history for secrets (gitleaks), a scan of packages for known vulnerabilities (pip-audit, npm audit).
3. **The backend job** builds the image (with the two models, cached), starts the same services as on your laptop, builds the database from nothing with the migrations, checks the database matches the models, runs the type check, runs the **leak gate** first (canary scan, access oracle, 62-case evaluation: any leak fails the build), then all tests with coverage, then a gate that needs at least 80 % coverage of the security-critical code.
4. **Dependabot** opens a weekly pull request when a package has a newer version; each one goes through the same checks.
5. The first scans already paid off: the PDF reader `pypdf` had 8 known vulnerabilities and was upgraded; no secret was ever committed (43 commits scanned).

### 3. Important files
`.github/workflows/ci.yml`, `.github/dependabot.yml`, `.github/pull_request_template.md`, `backend/pyproject.toml` (ruff, mypy, coverage), `frontend/eslint.config.mjs`, `scripts/setup_env.sh`, `.pre-commit-config.yaml`, `LICENSE`, `CONTRIBUTING.md`, `docs/ci.md`, `docs/adr/036-ci-and-quality-gates.md`.

### 4. Tools: why we chose them
ruff (fast Python linter), mypy (types), ESLint (the Next.js standard), pytest-cov (coverage), gitleaks (secret scan of history), pip-audit and npm audit (known vulnerabilities), Docker Buildx cache (the 1 GB models are not downloaded on every run).

### 5. How to run it
Everything runs by itself on a pull request. To run the same checks on your laptop, see `docs/ci.md` (one command per gate).

### 6. How to test it
Open a pull request and look at the **Checks** section. All five jobs should turn green.

### 7. Actual results (checked by me)
- Locally, exactly as the workflow runs them: ruff clean, mypy clean (111 files), ESLint 0 errors, TypeScript clean, 123 frontend tests, production build, 697 backend tests (83 % coverage overall, higher on the security modules), gitleaks (no leaks in the whole history), pip-audit (clean after the pypdf upgrade), npm audit (clean).
- The first run on GitHub found a real problem (a fresh database was never migrated before `alembic check`). Fixed, and every step was re-run on a second, empty copy of the stack: all green (697 tests, 94 % coverage of the security code).

### 8. Limitations and open issues
- The first CI run is slow (no cache yet).
- 21 advisory warnings from Next.js 16's React Compiler rules are tolerated with a ceiling (backlog 44).
- Lighthouse and axe checks arrive in 9C.
- See `docs/CHALLENGES.md` entries 128 to 134.

## Layer 9B: operations (retention, status, backup and restore)

### 1. What we built
The things that keep a running system healthy and recoverable: audit records that expire on schedule, a status page anyone can open, a few service numbers for the administrator, a nightly tidy-up of old passages, and backup and restore scripts with a restore that was actually tested.

### 2. How it works, step by step
1. **Audit retention:** audit records older than 365 days (setting `AUDIT_RETENTION_DAYS`; 0 keeps everything; never below 30) are removed every night. The audit tables stay append-only: only a special database function can remove rows, only rows older than 30 days, and each purge is recorded with counts only. The Overview says how many records are past the limit.
2. **Status page** (`/status`, no sign-in): "All systems operational", "Some features are slow or unavailable" (the worker is down) or "The service is down", with a line for the database, Redis, the file storage and the background worker. It tells nothing private (no address, version or error). If the page cannot reach the server it says so.
3. **Service numbers:** the Overview shows requests, server errors and "too many requests" for the last 24 hours (numbers only).
4. **Tidy-up:** every night the passages of document versions older than the newest three are removed (never the ones searches use, never the original files).
5. **Backup:** `bash scripts/backup.sh` writes the database, the uploaded files, a counts file and checksums into `backups/<date>/` (private, never committed). Secrets are not included.
6. **Restore:** `bash scripts/restore.sh backups/<date> --yes` checks the backup, rebuilds everything and compares the counts. `docs/runbook.md` explains it step by step, including recovery on a brand-new machine.

### 3. Important files
`backend/app/audit/retention.py`, migration `0009`, `backend/app/core/status.py`, `backend/app/core/metrics.py`, `backend/app/ingest/cleanup.py`, `backend/app/scripts/{maintenance,storage_archive}.py`, `scripts/{backup,restore}.sh`, `docs/runbook.md`, `docs/adr/037-operations.md`, `frontend/app/status/`, `frontend/lib/status.ts`. Tests: `backend/tests/test_ops.py`.

### 4. Tools: why we chose them
`pg_dump` and `pg_restore` (PostgreSQL's own, proven tools), a tar stream with a manifest for the files (no extra service), Celery beat (already running) for the nightly jobs, Redis for the heartbeat and counters.

### 5. How to run it
`docker compose build backend && docker compose up -d` (the migration is `docker compose exec backend alembic upgrade head`). Open http://localhost:3000/status. Make a backup with `bash scripts/backup.sh`.

### 6. How to test it
`docker compose exec backend python -m pytest tests/test_ops.py -q` (35 tests); `cd frontend; npx vitest run` (132 tests).

### 7. Actual results (checked by me)
- 732 backend tests and 132 frontend tests pass; ruff, mypy, ESLint, type check and build are clean.
- 15 deliberate mistakes (retention off-switch, the cleanup touching active or deleted documents, an off-by-one in the kept versions, the status rules, a swallowed failure, counting health checks, the 24-hour window, caching, the rate limit, the archive checks, paging, the Overview number) were all caught.
- **A real restore:** a backup of the development system (50 documents, 51 files, 9 people, 80 rules, 548 audit questions) was restored into a second, completely empty stack with new secrets. All six counts matched; a search as one person found the leave policy; a search as another person for a restricted topic did not return the restricted document; all 51 original files matched their fingerprints; the audit tables were still append-only; the status page said operational.
- In a real browser: the status page with everything working and with the file storage stopped (it said "The service is down" and "Not working" for that line), the Overview cards, no sideways scrolling at 360 px. The temporary administrator was deleted.

### 8. Limitations and open issues
- Backups are run by hand (the runbook describes scheduling them).
- The audit purge flag is an accident guard, not a defence against someone who controls the database login (ADR 037).
- See `docs/CHALLENGES.md` entries 135 to 139.

## Layer 9C: privacy and security documents, API reference, accessibility

### 1. What we built
The honest paperwork of the project, and checks that keep it honest: public Privacy, Terms and Security pages that describe what the software really does, a security policy, a security document that ties every threat to the test that proves it (and lists what the project does not do), an API reference that is generated from the code, and speed and accessibility checks.

### 2. How it works, step by step
1. **Privacy page:** no cookies on the public pages; one httpOnly sign-in cookie after you sign in; what is kept (account, your question history without answers, the audit trail without answers or document text, 365 days by default); exactly what leaves the server (your question and a few passages you may read go to the AI provider when an answer is written; a connected source is read with a read-only key). It no longer says "no cookies" falsely.
2. **Terms page:** a demo with invented data, answers can be wrong, no warranty, MIT licence.
3. **Security page and `SECURITY.md`:** the rules, six walls, the measured result with its limits, and how to report a weakness privately.
4. **`docs/security.md`:** rules, walls (with the file that enforces each), 16 threats each tied to tests, the OWASP Top 10 for LLM Applications (2025) with evidence, secrets, what leaves the machine, **what the project does not do**, and the limits of the evidence.
5. **`docs/api.md`:** every route with who may call it and what it does. Generated by `python -m app.scripts.gen_api_docs`; CI fails if the committed page is out of date.
6. **Lighthouse job in CI:** the six public pages must keep performance 75 (CI runner; 97 to 100 locally), accessibility 95, best practices 90, SEO 90.
7. **axe audit (by hand):** 14 signed-in and public pages checked against WCAG 2 A and AA, 2.1, 2.2 and best-practice rules; three real findings fixed.

### 3. Important files
`frontend/app/{privacy,terms,security}/page.tsx`, `SECURITY.md`, `docs/security.md`, `docs/api.md`, `backend/app/scripts/gen_api_docs.py`, `backend/tests/test_api_docs.py`, `frontend/scripts/lighthouse-check.mjs`, `.github/workflows/ci.yml`, `docs/adr/038-privacy-security-docs-and-accessibility.md`.

### 4. Tools: why we chose them
Lighthouse (the standard speed and accessibility audit, free, runs in CI), axe-core (the engine behind most accessibility checkers), FastAPI's own route information (so the API page cannot disagree with the code).

### 5. How to run it
Open http://localhost:3000/privacy, /terms and /security. Regenerate the API page with `docker compose exec -T backend python -m app.scripts.gen_api_docs > docs/api.md`.

### 6. How to test it
`docker compose exec backend python -m pytest tests/test_api_docs.py -q` (4 tests). The CI Checks show the Lighthouse and API-reference steps.

### 7. Actual results (checked by me)
- Lighthouse on a production build: landing 98 / 100 / 100 / 100 (performance, accessibility, best practices, SEO); sign-in, status, privacy, terms, security 97 to 100 performance, 100 accessibility, 96 to 100 best practices, 100 SEO.
- axe-core on 14 pages (home, Ask, documents, a document, upload, users, groups, sources, overview, evaluation, audit, knowledge gaps, profile, privacy): after fixing three findings (two empty table-header cells, one skipped heading level) every page reported zero violations.
- The three public pages were read in a real browser. 736 backend and 132 frontend tests pass; ruff, mypy, ESLint, type check and build are clean; the API page is in sync.

### 8. Limitations and open issues
- The axe audit of signed-in screens is manual (backlog 48); a person using a screen reader still has to try them.
- Privacy and Terms are plain-language texts, not legal advice.
- See `docs/CHALLENGES.md` entries 140 to 146.

