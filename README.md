# SecureSearch AI
*Permission-aware enterprise knowledge search (RAG) built for security-first organizations.*

> **Status:** In development: Phase 1 and 2A done.

## Problem & Solution
**Problem:** Generic RAG tools lack enterprise-grade security and permissions, risking data leakage of sensitive internal documents to unauthorized users.
**Solution:** SecureSearch AI provides a modular search system where every query and retrieved chunk strictly respects existing Access Control Lists (ACL), ensuring users only see what they are allowed to see.

## Current Features
* **Landing Page (Phase 1):** Dark premium design, interactive demos, and high accessibility standards.
* **Backend Foundation (Phase 2A):** Dockerized backend with FastAPI, Postgres (pgvector), Redis, and Mailpit. Includes structural validations, JSON logging, and error handling.

## Architecture Overview
The system follows a modular monolith architecture, separating the Next.js frontend from the FastAPI Python backend. Data is persisted in PostgreSQL with pgvector for semantic search, cached in Redis. 

[Read the full Architecture Overview](docs/architecture.md)

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
Open [http://localhost:3000](http://localhost:3000)

### Backend (Docker Compose)
Ensure you have Docker Desktop running.

1. Copy the environment variables template:
```bash
cp .env.example .env
```
2. Generate secure secrets for `.env` (do NOT print them or use real production secrets locally).
3. Start the infrastructure:
```bash
docker compose up --build -d
```
4. Verify services:
- Health check: [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)
- Ready check: [http://localhost:8000/api/v1/ready](http://localhost:8000/api/v1/ready)
- Mailpit UI: [http://localhost:8025](http://localhost:8025)

## Running Tests
Run the backend test suite:
```bash
docker compose exec backend pytest -q
```

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
* **Phase 2B-2C:** Authentication & User Models
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
* Login and user management are not implemented yet.
* No documents can be ingested or searched yet.
* Permissions and ACLs are not enforced since there is no user data.
* Legal pages are drafts and do not constitute legal advice.

## License / Contact
*Placeholder for license and contact details.*
