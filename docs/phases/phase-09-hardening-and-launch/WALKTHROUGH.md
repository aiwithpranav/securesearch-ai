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
