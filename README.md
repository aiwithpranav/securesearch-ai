# SecureSearch AI
*Permission-aware enterprise knowledge search (RAG) built for security-first organizations.*

> **Status:** In development. Done and signed off: Phase 1 (landing page, tag `v0.1`), Phase 2 (authentication and user flow, tag `v0.2`) and Phase 3 (documents and ingestion, tag `v0.3`) and Phase 4 (permissions and ACL, tag `v0.4`) and Phase 5 (hybrid retrieval, tag `v0.5`). Next: Phase 6 (answers and citations).

## Problem & Solution
**Problem:** Generic RAG tools lack enterprise-grade security and permissions, risking data leakage of sensitive internal documents to unauthorized users.
**Solution:** SecureSearch AI provides a modular search system where every query and retrieved chunk strictly respects existing Access Control Lists (ACL), ensuring users only see what they are allowed to see.

## Current Features
* **Landing Page (Phase 1):** Dark premium design, interactive demos, and high accessibility standards.
* **Backend Foundation (Phase 2A):** Dockerized backend with FastAPI, Postgres (pgvector), Redis, and Mailpit. Includes structural validations, JSON logging, and error handling.

* **Phase 3A infrastructure (implemented):** a private S3-style file store (`storage`), a background worker (`worker`) and a local embedding model baked into the image.
* **Phase 3B ingestion (implemented):** admins can upload PDF, DOCX, TXT or MD files through the API; the worker turns them into text chunks with 384-number vectors, safely (a failed job never damages the previous version) and with notifications on failure. No endpoint returns document text (admin is not reader).
* **Phase 6C Ask screen (implemented, awaiting owner review):** sign in and use **Ask** in the menu: get a short answer with sources, open the passage behind a source, rate the answer, and see your recent questions. Live answers need an OpenAI key in your local `.env`.
* **Phase 6B answer API (done, merged):** ask a question and get a short cited answer or one uniform refusal, see the passage behind a citation, keep a private search history and give thumbs up or down. 
* **Phase 6A answer engine (done, merged):** turns a question into a short answer with citations written only from documents the person may read, or one uniform refusal. Needs an OpenAI key in `.env` for live answers (optional). 
* **Design refresh (implemented, awaiting owner review):** new purple palette across the whole app and an animated dots sphere on the landing page and sign-in pages. After sign-in the app stays calm and stable. No behaviour changed.
* **Phase 5C search screen (done, merged):** sign in and use **Search** in the menu: type a question, see the best passages from the documents you may read with a relevance bar. Written answers with sources are Phase 6.
* **Phase 5B search API (done, merged):** `POST /api/v1/search` returns the best passages for a question from the documents the caller may read (rate limited; the question text is never logged). 
* **Phase 5A search engine (done, merged):** finds the best passages for a question using full-text and meaning-based (vector) search, merges them and reorders them with a local reranker model, always only inside the documents the person may read. Details: [Phase 5 walkthrough](docs/phases/phase-05-hybrid-retrieval/WALKTHROUGH.md).
* **Phase 4C admin screens (done, merged):** administrators manage people (invite, edit, roles, deactivate), groups and members, and the access rules of each document (allow or deny a person, role, group, department or everyone, with optional expiry), see the history of rule changes and ask "who can read this?" with a plain-English reason. Nobody can read document content yet (search is Phase 5).
* **Phase 4B rules API (implemented, merged):** administrators create groups and put people in them, add ALLOW or DENY rules to a document, see the history of rule changes, and ask the access preview why a person can or cannot read a document. Demo groups and rules for the 12 demo documents: `docker compose exec backend python -m app.scripts.seed_access`. Nobody can read document content yet (search is Phase 5).
* **Phase 4A access rules engine (done, merged):** the database tables for groups and document access rules, and one resolver that decides who may read, download or manage a document (deny by default, deny beats allow, admin is not reader, nothing cached). There is **no screen or API for the rules yet** (4B, 4C), so every document is still invisible to everybody except as metadata for administrators. Details: [Phase 4 walkthrough](docs/phases/phase-04-permissions-and-acl/WALKTHROUGH.md).
* **Phase 3C admin screens (implemented):** administrators get a Documents menu: a list with status and filters, an upload page, a document page (edit, re-index, delete, processing history) and a notification bell for failed processing. Normal users see none of it. There is **no search or answer yet**. Details: [Phase 3 walkthrough](docs/phases/phase-03-documents-and-ingestion/WALKTHROUGH.md). Details: [Phase 3 walkthrough](docs/phases/phase-03-documents-and-ingestion/WALKTHROUGH.md).
* **Auth backend (Phase 2B, implemented):** email + password login (Argon2id), 15-minute access token, rotating refresh cookie with theft detection, lockout, forgot/reset/change password (emails go to Mailpit), admin endpoints for users, roles and departments, 8 seeded demo users. Details: [Phase 2 docs](docs/phases/phase-02-auth-user-flow/WALKTHROUGH.md).

* **Login UI (Phase 2C, implemented):** `/login` (validation, shake, Caps Lock hint, Remember me, all error states), `/forgot-password`, `/reset-password`, `/home` (your details, first-2-minutes guide, welcome tour), `/profile` (change password, sign out of all devices). Search and documents are **not built yet**; guide steps for them say "Coming in Phase N". Details: [2C walkthrough](docs/phases/phase-02-auth-user-flow/WALKTHROUGH-2C.md).

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

Frontend checks (from `frontend/`): `npm test` (20 unit tests, needs Node 22+), `npm run typecheck`, `npm run build`. Stop the dev server with Ctrl+C.

### Backend (Docker Compose)
Ensure you have Docker Desktop running.

Run all commands in PowerShell from the repository root.

1. Create `.env` with random secrets (git-ignored; never overwrites an existing `.env`; shows no secrets):
```powershell
powershell -ExecutionPolicy Bypass -File scripts/setup_env.ps1
```
Environment variable names (placeholders only, see `.env.example`): `APP_ENV`, `APP_SECRET_KEY`, `JWT_SECRET_KEY`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `DATABASE_URL`, `REDIS_URL`, `SMTP_HOST`, `SMTP_PORT`, `FRONTEND_ORIGIN`, `SEED_USER_PASSWORD`, and (Phase 3) `S3_ENDPOINT_URL`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `S3_BUCKET`. Never commit `.env`. If you already have a `.env`, the same command only adds the missing keys (no values shown).
2. Start the services (the first build downloads PyTorch and the embedding model and takes several minutes; if it fails with a network error, run it again):
```powershell
docker compose up --build -d
docker compose ps
```
`docker compose ps` should show 6 services, all `(healthy)`: postgres, redis, mailpit, storage, backend, worker.
3. Create the tables, then the demo users:
```powershell
docker compose exec backend alembic upgrade head
docker compose exec backend python -m app.scripts.seed_users
docker compose exec backend python -m app.scripts.load_synthetic_docs   # optional: 12 made-up demo documents
docker compose exec backend python -m app.scripts.seed_access            # optional: demo groups and access rules (after the two above)
```
4. Verify:
- Health: [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health) should show `{"status":"ok"}`
- Ready: [http://localhost:8000/api/v1/ready](http://localhost:8000/api/v1/ready) should show postgres and redis `ok`
- API docs (try login there): [http://localhost:8000/api/docs](http://localhost:8000/api/docs)
- Mailpit inbox (reset and invite emails): [http://localhost:8025](http://localhost:8025)
- Try the admin screens: sign in at http://localhost:3000/login as `prashant@demo`, then open **Documents** (list, upload, edit, re-index, delete). Or try the API: in the API docs log in with `POST /auth/login` as `prashant@demo`, click Authorize with the token, then `POST /documents/upload` (demo files are in `sample-data/synthetic/`). Check `GET /documents` and `GET /ingestion/jobs`.
- Object storage and worker (no web page, private network): `docker compose exec backend python -m app.scripts.storage_check` should print "Write, read and delete: OK".

Demo users (synthetic): `swara@demo`, `pranav@demo`, `dhanashree@demo`, `akshay@demo`, `sanjana@demo`, `shivam@demo`, `prashant@demo` (admin), `karunesh@demo`. `former@demo` is deactivated on purpose. A fresh seed gives every demo user the shared `SEED_USER_PASSWORD` from your local `.env`. For name-based passwords, keep a local file `demo-credentials.local.txt` (git-ignored, lines like `email: password`) and run `Get-Content demo-credentials.local.txt | docker compose exec -T backend python -m app.scripts.set_user_passwords` from the repository root. These passwords are easy to guess on purpose: use them on a developer machine only, never on a real server.

Stop: `docker compose down` (data kept). `docker compose down -v` also deletes the database.

## Running Tests
```powershell
docker compose exec backend pytest -q
```
Tests use their own database (`<POSTGRES_DB>_test`) and need the services above running. If you edit test files, copy them in first: `docker compose cp backend/tests/. backend:/app/tests/`. Last run by Claude: 283 passed. Frontend (from `frontend/`): `npm test` runs 20 unit tests.

## Tech Stack
* **Frontend:** Next.js `16.4.0`, React `19.3.0`, TailwindCSS `4.3.3`, Motion `^14.0.0`, TypeScript `~5.9.3`
* **Backend:** FastAPI `0.143.0`, Python 3.12, Uvicorn `0.54.0`, SQLAlchemy `2.1.4`, Alembic `1.20.0`, Pydantic `2.14.0`
* **Infrastructure:** Postgres 17 with pgvector `0.8.0`, Redis `7.4.2`, Mailpit `v1.22.0`, SeaweedFS `4.48` (S3 object storage, replaces archived MinIO, see CR-001)
* **Documents (Phase 3B):** pypdf `6.19.0`, python-docx `1.2.0`, python-multipart `0.0.32`, pgvector (Python) `0.5.0`; dev only: reportlab `5.0.1`.
* **Background jobs and AI (Phase 3A):** Celery `5.6.3`, boto3 `1.43.108`, sentence-transformers `6.1.0` with `BAAI/bge-small-en-v1.5` (384-dimension local embeddings, MIT licence), CPU-only PyTorch `2.14.1`. All versions: [ADR 024](docs/adr/024-phase-3-pinned-versions.md).

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
Phases follow the blueprint (v1.2). Done: Phases 1, 2 and 3.
* **Phase 3 (done):** Documents and ingestion (upload, parse, chunk, embed, admin screens)
* **Phase 4 (done, `v0.4`):** Permissions and ACL (groups, allow/deny rules, admin users and groups screen)
* **Phase 5 (done, `v0.5`):** Hybrid retrieval (full-text + vector search, rerank)
* **Phase 6:** Answers and citations (LLM, refusals, chat UI)
* **Phase 7:** Audit and evaluation
* **Phase 8:** Incremental sync and one real connector
* **Phase 9:** Hardening and launch

Loose ends and ideas: [docs/BACKLOG.md](docs/BACKLOG.md).

## Evaluation
Not measured yet. Targets are in the blueprint; results will be published after Phase 7.
*Note: Lighthouse numbers for the frontend were measured locally by the owner on 9 Oct 2026 as Performance 99, Accessibility 96.*

## Known Limitations
* Route protection in the UI is client-side only; the API enforces access. The welcome tour is remembered per browser (it shows again on a new browser). The frontend must run on port 3000 (the backend allows only that address).
* Admin-initiated password reset is not built (needs a Change Request, see ADR 023).
* No documents can be ingested or searched yet.
* Document permissions (ACL) are not implemented yet; only account-level roles exist.
* Screen-reader and full keyboard-only accessibility checks of the signed-in pages have not been done.
* Demo accounts have easy-to-guess passwords on purpose. Use them on a developer machine only.
* Legal pages are drafts and do not constitute legal advice.

## License / Contact
*Placeholder for license and contact details.*
