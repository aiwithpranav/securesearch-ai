# Architecture Overview

This document outlines the high-level architecture of SecureSearch AI.

## Current State (end of Phase 2)

Two parts run side by side:
* **Frontend (Next.js, port 3000):** the public landing page and legal pages, plus the signed-in portal: login, forgot/reset password, home (your details, guide, welcome tour) and profile (change password, sign out of all devices).
* **Backend (FastAPI, port 8000) with Postgres, Redis and Mailpit** in Docker Compose: login and session API, user, role and department admin API, health checks. There are no documents and no search yet.

```mermaid
flowchart TD
    subgraph Frontend [Frontend (Next.js, localhost:3000)]
        LP[Landing page and legal pages]
        Portal[Login, reset, home, profile]
    end

    subgraph Backend_Infrastructure [Backend (Docker Compose)]
        API[FastAPI backend /api/v1]
        DB[(PostgreSQL 17 + pgvector: users, roles, departments, auth_tokens)]
        Cache[(Redis: lockout and rate limits)]
        Mail[Mailpit: fake inbox for reset and invite emails]
    end

    User((User)) --> LP
    User --> Portal
    Portal -->|JSON + httpOnly refresh cookie| API

    API -->|Reads/Writes| DB
    API -->|Counters| Cache
    API -.->|Sends emails| Mail

    classDef network fill:#f9f9f9,stroke:#333,stroke-width:1px;
    class Backend_Infrastructure network;
```

### How sign-in works (Phase 2)
1. `POST /auth/login` checks the password (Argon2id) and returns a 15-minute **access token** (kept only in browser memory) plus a **refresh cookie** (`httpOnly`, cannot be read by JavaScript).
2. The access token holds only the user id. **Roles are read from the database on every request.**
3. After a page reload the portal calls `/auth/refresh`. The server rotates the cookie. Using an old cookie twice ends the whole session (theft detection).
4. Details and decisions: [ADR 023](adr/023-auth-implementation-details.md), [Phase 2 walkthroughs](phases/phase-02-auth-user-flow/).

## Planned Architecture (blueprint phases)

* **Phase 3:** Documents and ingestion (upload, parse, chunk, embed).
* **Phase 4:** Permissions and ACL (groups, allow/deny rules, admin users and groups screen).
* **Phase 5:** Hybrid retrieval (full-text + vector search, rerank).
* **Phase 6:** Answers and citations (LLM, citation validation, refusals, chat UI).
* **Phase 7:** Audit and evaluation (audit logs, 60+ test cases, dashboards).
* **Phase 8:** Incremental sync and one real connector.
* **Phase 9:** Hardening and launch (CI/CD, rate limits, backups, deployment).
