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

