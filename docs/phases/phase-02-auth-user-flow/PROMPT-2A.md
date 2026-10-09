ROLE: Senior backend engineer. Mission: Phase 2, LAYER 2A (backend foundation) of SecureSearch AI. Do ONLY this mission.

ENVIRONMENT: Windows 11 host, Docker Desktop 4.94.0 (Engine 29.8.2, Compose v5.5.1) on WSL 2, 24 GB RAM, Node 24, Git 2.55. I run commands in Windows PowerShell. Do not use the obsolete top-level "version:" key in docker-compose.yml. Make sure files use LF line endings where Linux containers read them (add a .gitattributes rule if needed).

CONTEXT
- Repo root has frontend/ (Phase 1, finished and tagged v0.1, DO NOT TOUCH), docs/, scripts/. The current git branch is feat/backend-skeleton.
- The project blueprint rules are FROZEN: modular monolith, FastAPI backend in backend/, PostgreSQL 16+ with pgvector 0.8+, Redis, Mailpit for dev email, no secrets in Git, an "env doctor" with plain-English errors, API base path /api/v1, errors use Problem Details JSON (type, title, status, detail, request_id). Add only; never edit finished work.
- No auth, no users table, no login in this layer. No database tables at all yet.

STEP 0: Save this entire prompt text unchanged to docs/phases/phase-02-auth-user-flow/PROMPT-2A.md.
STEP 1: Write a short implementation plan (files, services, pinned versions, how you will verify each tag) and WAIT for my approval before writing code.

VERSIONS (verified on PyPI; pin exactly in backend/requirements.txt with ==): fastapi 0.143.0, uvicorn 0.54.0, sqlalchemy 2.1.4, alembic 1.20.0, pydantic 2.14.0, pydantic-settings 2.15.0, psycopg[binary] 3.3.6, argon2-cffi 25.1.0, PyJWT 2.15.1, redis 8.1.0. backend/requirements-dev.txt: pytest 9.1.1, httpx 0.28.1. Use Python 3.12 (python:3.12-slim). Look up and pin exact image tags for Postgres (a pgvector image on Postgres 17, e.g. pgvector/pgvector:0.8.x-pg17; run `docker pull` to confirm the tag exists and confirm pgvector is 0.8 or newer), Redis, and Mailpit. Never use :latest. Record what you verified and what you could not verify in docs/adr/022-pinned-versions.md (Title, Status, Context, Decision, Consequences).

TASKS
1. docker-compose.yml at repo root with services: postgres, redis, mailpit, backend. Healthchecks on all. Named volume for Postgres data. Two networks: "private" (postgres, redis, mailpit, backend) and "public" (backend only). Do NOT publish postgres or redis ports. Publish only the backend on 127.0.0.1:8000 and the Mailpit web UI on 127.0.0.1:8025. The backend waits for healthy postgres and redis.
2. backend/Dockerfile (python:3.12-slim, non-root user, installs pinned requirements) and a .dockerignore.
3. .env.example at repo root with FAKE placeholders only (CHANGE_ME) for: APP_ENV, APP_SECRET_KEY, JWT_SECRET_KEY, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB, DATABASE_URL, REDIS_URL, SMTP_HOST, SMTP_PORT, FRONTEND_ORIGIN (http://localhost:3000). List OPENAI_API_KEY commented out ("needed from Phase 6"). NEVER create a real .env and never put real secrets anywhere. Confirm .env is in .gitignore.
4. backend/app/ structure: main.py, core/config.py (pydantic-settings), core/env_doctor.py, core/logging.py (structured JSON logs, never log secrets), core/errors.py (Problem Details handlers), core/middleware.py (X-Request-ID on every request and response), api/v1/health.py, db/session.py. Clear small modules so later phases only add files.
5. Env doctor: runs at startup and also via `python -m app.core.env_doctor`. Checks: every required variable is set; none still equals a placeholder (CHANGE_ME); APP_SECRET_KEY and JWT_SECRET_KEY are at least 32 characters and different from each other; Postgres and Redis are reachable. On failure print plain English naming the exact variable and what to do (example: "JWT_SECRET_KEY is missing. Add it to .env, then restart."), print ALL problems at once, never print secret values, and exit non-zero so the app does not start. OPENAI_API_KEY is NOT required in this phase.
6. Endpoints: GET /api/v1/health (liveness, no dependencies, returns {"status":"ok"}) and GET /api/v1/ready (checks Postgres and Redis, returns per-service status, HTTP 503 with Problem Details if any is down). CORS: allow ONLY the exact FRONTEND_ORIGIN.
7. Alembic initialised (backend/alembic.ini, migrations/) with env.py reading DATABASE_URL. No tables, no empty fake migrations.
8. Tests (pytest): health returns ok; ready; request id header present; env doctor reports a missing variable, a placeholder, and a short secret in plain English. Tell me the exact PowerShell command to run them inside the container.
9. Add a short "Quick start (backend)" section to the root README.md: copy .env.example to .env, generate two secrets with node -e "console.log(require('crypto').randomBytes(48).toString('base64url'))", then docker compose up --build.
10. Create docs/phases/phase-02-auth-user-flow/STATUS.md (done, in progress, next step, open issues).

RULES
- No secrets in any file or log. Typed code (mypy-friendly), small modules, comments in plain English for a first-time builder.
- Do not touch frontend/. Do not add endpoints beyond the two above.
- Do not create or edit .env.
- Do not claim something works unless you ran it. Say clearly what you could not run or verify.

DONE WHEN
- `docker compose up --build` starts all four services healthy.
- http://localhost:8000/api/v1/health returns {"status":"ok"}; /api/v1/ready reports postgres and redis ok; http://localhost:8025 shows Mailpit.
- pytest passes.
- DO NOT run git commit or git push. Stop and report: files created, exact PowerShell commands for me to run, what I should check, and what you could not verify.
