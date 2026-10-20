# Architecture Overview

This document outlines the high-level architecture of SecureSearch AI.

## Current State (end of Phase 3)

Six services run in Docker Compose, plus the Next.js frontend on the host:
* **Frontend (Next.js, port 3000):** landing page, sign-in portal, and the administrator's Documents screens (list, upload, document page, notification bell).
* **backend (FastAPI, port 8000):** sign-in and session API, user/role/department admin API, documents and ingestion API, notifications API.
* **worker (Celery):** runs ingestion jobs in the background. Same image as the backend. It has **no internet access**; the embedding model is baked into the image.
* **postgres (with pgvector):** users, roles, departments, tokens, documents, versions, jobs, notifications, and the text chunks with 384-number vectors.
* **redis:** job queue and rate limit counters. **storage (SeaweedFS, S3 API):** the original uploaded files. **mailpit:** fake inbox for dev emails.

There is still **no search and no answers**, and no access rules for documents yet, so administrators see document metadata only and nobody can read document content.

```mermaid
flowchart TD
    subgraph Frontend [Frontend (Next.js, localhost:3000)]
        LP[Landing page]
        Portal[Sign-in portal]
        Admin[Admin: documents screens]
    end

    subgraph Private [Docker Compose, private network]
        API[FastAPI backend /api/v1]
        W[Celery worker + local embedding model]
        DB[(PostgreSQL + pgvector)]
        Q[(Redis: queue, rate limits)]
        S3[(SeaweedFS: original files)]
        Mail[Mailpit]
    end

    User((User)) --> LP
    User --> Portal
    Portal --> Admin
    Admin -->|JSON + file upload| API
    API -->|metadata, chunks| DB
    API -->|store original| S3
    API -->|queue job| Q
    Q --> W
    W -->|read original| S3
    W -->|chunks + vectors| DB
    API -.->|emails| Mail
```

### How a document becomes searchable data (Phase 3)
1. An administrator uploads a file. The API checks it (type, real content, size, zip bombs), stores the original under a key made of IDs and a hash, saves a `QUEUED` job and answers at once.
2. The worker reads the original, extracts text (PDF per page, DOCX and MD headings as sections), cuts it into chunks of about 450 tokens, and turns each chunk into a 384-number vector.
3. It publishes the new chunks and switches off the old ones in **one database transaction**, so a reader sees the complete old set or the complete new set.
4. If anything fails, the old chunks stay in use, the job records a fixed error code, and every administrator gets a notification.
5. Nothing in the API, the screens or the logs contains document text (admin is not reader).

Details: [ADR 026](adr/026-ingestion-design.md), [ADR 025](adr/025-object-storage-seaweedfs.md), [Phase 3 walkthrough](phases/phase-03-documents-and-ingestion/WALKTHROUGH.md).

### How sign-in works (Phase 2)
1. `POST /auth/login` checks the password (Argon2id) and returns a 15-minute **access token** (kept only in browser memory) plus a **refresh cookie** (`httpOnly`).
2. The access token holds only the user id. **Roles are read from the database on every request.**
3. After a reload the portal calls `/auth/refresh`; the server rotates the cookie, and reuse of an old cookie ends the whole session.

Details: [ADR 023](adr/023-auth-implementation-details.md).

## Planned Architecture (blueprint phases)

* **Phase 4:** Permissions and ACL (groups, allow/deny rules, admin users and groups screen).
* **Phase 5:** Hybrid retrieval (full-text + vector search, rerank).
* **Phase 6:** Answers and citations (LLM, citation validation, refusals, chat UI).
* **Phase 7:** Audit and evaluation (audit logs, 60+ test cases, dashboards).
* **Phase 8:** Incremental sync and one real connector.
* **Phase 9:** Hardening and launch (CI/CD, rate limits, backups, deployment).
