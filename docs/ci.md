# Continuous integration

Every pull request into `main`, and every push to `main`, runs the gates below (`.github/workflows/ci.yml`). A red check means the change must not be merged. The gates are the blueprint's section 14.3, adapted to what this project uses.

| Gate | What it protects | Run it yourself |
|---|---|---|
| **Backend lint** (ruff) | Mistakes and style in Python | `cd backend && ruff check .` |
| **Frontend** (ESLint, TypeScript, Vitest, build) | The screens | `cd frontend && npm run lint && npm run typecheck && npm test && npm run build` |
| **Secret scan** (gitleaks, whole history) | No key or password was ever committed | `docker run --rm -v "$PWD:/repo" zricethezav/gitleaks:v8.30.0 git /repo --redact` |
| **Dependency scan** (pip-audit, npm audit) | Known vulnerabilities in packages | `pip-audit -r backend/requirements.txt --no-deps --disable-pip` and `cd frontend && npm audit --omit=dev --audit-level=high` |
| **Database check** (`alembic upgrade head`, then `alembic check`) | The migrations build a database from nothing, and the models and the migrations agree | `docker compose exec backend alembic upgrade head && docker compose exec backend alembic check` |
| **Type check** (mypy) | Wrong types in the backend | `docker compose exec backend mypy` |
| **Leak gate** | The product's central promise: nobody sees what they may not. The canary scan, the independent access oracle and the 62-case evaluation. **Any leak fails the build.** | `docker compose exec backend python -m pytest tests/test_eval.py tests/test_eval_api.py tests/test_access_oracle.py` |
| **All tests** with coverage | Everything else (700 tests) | `docker compose exec backend python -m pytest --cov` |
| **Coverage gate** | At least 80 % of the security-critical code is exercised: access rules, passwords and tokens, rate limits, the audit trail, answers and citations, sync, sign-in checks | `docker compose exec backend coverage report --fail-under=80 --include="app/access/*,app/core/security.py,app/core/rate_limit.py,app/audit/*,app/answers/*,app/sync/*,app/api/deps.py"` |
| **API reference** (`docs/api.md`) | The page is generated from the application; CI fails if the committed copy is out of date | `docker compose exec -T backend python -m app.scripts.gen_api_docs > docs/api.md` |
| **Lighthouse** (six public pages) | Speed and accessibility stay high: performance 75 (a CI runner is slow; local 97 to 100; the landing page is measured three times and the middle score counts), accessibility 95, best practices 90, SEO 90 | `cd frontend && npm run build && npx next start -p 3100`, then `npx lighthouse http://localhost:3100/` and `node scripts/lighthouse-check.mjs <folder of reports>` |
| **Image build** | The backend image (with the two models) builds from scratch | `docker compose build backend` |

## Notes
- The tests run inside the backend container, exactly as on a developer machine, against real PostgreSQL (pgvector), Redis, Mailpit and object storage. A fake model writes the answers, so CI needs no OpenAI key and costs nothing.
- The image build is cached between runs (the two models are about 1 GB). The Dockerfile downloads the models before it installs the other packages, so changing a package does not download them again.
- ESLint has a ceiling for warnings (`--max-warnings` in `frontend/package.json`): the number may fall but never grow.
- Dependabot opens a weekly pull request for each package ecosystem; each one runs these same gates.
- Optional local checks before every commit: `pip install pre-commit && pre-commit install` (see `.pre-commit-config.yaml`).
- Lighthouse covers the public pages. The signed-in screens were audited by hand with axe-core (zero violations on 14 pages; see ADR 038).
