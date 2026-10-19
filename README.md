# SecureSearch AI
*Permission-aware enterprise knowledge search (RAG) built for security-first organizations.*

> **Status:** In development. Done: Phase 1 (landing page), 2A (backend foundation). Built and awaiting owner review: 2B (auth backend). Next: 2C (login screens).

## Problem & Solution
**Problem:** Generic RAG tools lack enterprise-grade security and permissions, risking data leakage of sensitive internal documents to unauthorized users.
**Solution:** SecureSearch AI provides a modular search system where every query and retrieved chunk strictly respects existing Access Control Lists (ACL), ensuring users only see what they are allowed to see.

## Current Features
* **Landing Page (Phase 1):** Dark premium design, interactive demos, and high accessibility standards.
* **Backend Foundation (Phase 2A):** Dockerized backend with FastAPI, Postgres (pgvector), Redis, and Mailpit. Includes structural validations, JSON logging, and error handling.

* **Auth backend (Phase 2B, implemented, awaiting owner review):** email + password login (Argon2id), 15-minute access token, rotating refresh cookie with theft detection, lockout, forgot/reset/change password (emails go to Mailpit), admin endpoints for users, roles and departments, 8 seeded demo users. API only: there is **no login screen yet** (Phase 2C). Details: [Phase 2 docs](docs/phases/phase-02-auth-user-flow/WALKTHROUGH.md).

* **Login UI, layer 2C-1 (implemented, awaiting owner review):** `/login` page with validation, shake, Caps Lock hint, Remember me and all error states, plus a minimal `/home` that shows the signed-in user. Forgot/reset pages, profile and tour are **planned** (2C-2). Details: [2C walkthrough](docs/phases/phase-02-auth-user-flow/WALKTHROUGH-2C.md).

## Architecture Overview
The system follows a modular monolith architecture, separating the Next.js frontend from the FastAPI Python backend. Data is persisted in PostgreSQL with pgvector for semantic search, cached in Redis. 

[Read the full Architecture Overview](docs/architecture.md)

Problems met while building, and how they were handled: [docs/CHALLENGES.md](docs/CHALLENGES.md).

## Security Model (Design Goals)
These are design goals and have not yet been proven in production:
- **0-Trust Queries:** Every search validates permissions.
- **Data Segregation:** No cross-tenant or cross-role data leaks.
- **Auditability:** Every search and access is logged.

## Quick Start

### Frontend (Landing Page)
Ensure you have Node.js 20.9.0+ installed.

```bash
cd frontend
npm install
npm run dev
```
Open [http://localhost:3000](http://localhost:3000). Sign-in page: [http://localhost:3000/login](http://localhost:3000/login) (needs the backend below, with demo users seeded). The API address defaults to `http://localhost:8000`; override with `NEXT_PUBLIC_API_URL` (a public URL, not a secret).

Frontend checks (from `frontend/`): `npm test` (5 unit tests, needs Node 22+), `npm run typecheck`, `npm run build`. Stop the dev server with Ctrl+C.

### Backend (Docker Compose)
Ensure you have Docker Desktop running.

Run all commands in PowerShell from the repository root.

1. Create `.env` with random secrets (git-ignored; never overwrites an existing `.env`; shows no secrets):
```powershell
powershell -ExecutionPolicy Bypass -File scripts/setup_env.ps1
```
Environment variable names (placeholders only, see `.env.example`): `APP_ENV`, `APP_SECRET_KEY`, `JWT_SECRET_KEY`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `DATABASE_URL`, `REDIS_URL`, `SMTP_HOST`, `SMTP_PORT`, `FRONTEND_ORIGIN`, `SEED_USER_PASSWORD`. Never commit `.env`.
2. Start the services:
```powershell
docker compose up --build -d
```
3. Create the tables, then the demo users:
```powershell
docker compose exec backend alembic upgrade head
docker compose exec backend python -m app.scripts.seed_users
```
4. Verify:
- Health: [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health) should show `{"status":"ok"}`
- Ready: [http://localhost:8000/api/v1/ready](http://localhost:8000/api/v1/ready) should show postgres and redis `ok`
- API docs (try login there): [http://localhost:8000/api/docs](http://localhost:8000/api/docs)
- Mailpit inbox (reset and invite emails): [http://localhost:8025](http://localhost:8025)

Demo users (synthetic): `aisha@demo`, `rahul@demo`, `priya@demo`, `arjun@demo`, `meera@demo`, `vikram@demo`, `dev@demo` (admin), `nina@demo`. `gone@demo` is deactivated on purpose. All share the password stored as `SEED_USER_PASSWORD` in your local `.env`.

Stop: `docker compose down` (data kept). `docker compose down -v` also deletes the database.

## Running Tests
```powershell
docker compose exec backend pytest -q
```
Tests use their own database (`<POSTGRES_DB>_test`) and need the services above running. If you edit test files, copy them in first: `docker compose cp backend/tests/. backend:/app/tests/`. Last run by Claude: 57 passed.

## Tech Stack
* **Frontend:** Next.js `16.4.0`, React `19.3.0`, TailwindCSS `4.3.3`, Motion `^14.0.0`, TypeScript `~5.9.3`
* **Backend:** FastAPI `0.143.0`, Python 3.12, Uvicorn `0.54.0`, SQLAlchemy `2.1.4`, Alembic `1.20.0`, Pydantic `2.14.0`
* **Infrastructure:** Postgres 17 with pgvector `0.8.0`, Redis `7.4.2`, Mailpit `v1.22.0`

## Folder Structure
```text
.
├── backend/          # FastAPI Python application and API routes
├── docs/             # Project documentation and architectural decisions
│   ├── adr/          # Architecture Decision Records
│   ├── phases/       # Progress tracking per phase
│   └── architecture.md # System architecture details
├── frontend/         # Next.js web application
├── .env.example      # Environment variable template
├── docker-compose.yml # Docker infrastructure configuration
└── README.md         # Project entrypoint
```

## Roadmap
* **Phase 2C (in progress):** 2C-1 login (built), 2C-2 forgot/reset, profile, tour (next), 2C-3 admin users page (optional)
* **Phase 3:** Document Ingestion & Storage
* **Phase 4:** Search & Retrieval
* **Phase 5:** LLM Generation (RAG)
* **Phase 6:** Audit Logging
* **Phase 7:** Evaluation & Optimization
* **Phase 8-9:** Syncing and CI/CD enhancements

## Evaluation
Not measured yet. Targets are in the blueprint; results will be published after Phase 7.
*Note: Lighthouse numbers for the frontend were measured locally by the owner on 9 Oct 2026 as Performance 99, Accessibility 96.*

## Known Limitations
* The login page works, but "Forgot password?" still shows the 404 page until layer 2C-2. Route protection is client-side only; the API enforces access.
* Admin-initiated password reset is not built (needs a Change Request, see ADR 023).
* No documents can be ingested or searched yet.
* Document permissions (ACL) are not implemented yet; only account-level roles exist.
* Not yet tested by a human end to end; automated tests only.
* Legal pages are drafts and do not constitute legal advice.

## License / Contact
*Placeholder for license and contact details.*
