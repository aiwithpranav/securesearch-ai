# Architecture Overview

This document outlines the high-level architecture of SecureSearch AI.

## Current State (Phase 2A)

The current architecture consists of a standalone Next.js frontend (landing page) and a foundational backend infrastructure running via Docker Compose. The backend provides basic health checks but does not yet serve frontend requests.

```mermaid
flowchart TD
    subgraph Frontend [Frontend (Next.js)]
        LP[Landing Page & Interactive Demo]
    end

    subgraph Backend_Infrastructure [Backend Infrastructure (Docker Compose)]
        API[FastAPI Backend]
        DB[(PostgreSQL 17 + pgvector)]
        Cache[(Redis 7.4.2)]
        Mail[Mailpit]
    end

    User((User)) --> LP
    User -->|API Requests (future)| API

    API -->|Reads/Writes| DB
    API -->|Caches| Cache
    API -.->|Sends Emails| Mail

    classDef network fill:#f9f9f9,stroke:#333,stroke-width:1px;
    class Backend_Infrastructure network;
```

## Planned Architecture

Future phases will introduce:
* **Authentication & Authorization**: User management, roles, and ACL integration.
* **Document Processing Pipeline**: Ingestion, chunking, and embedding generation.
* **Vector Search Engine**: Semantic search capabilities using pgvector.
* **RAG Generation**: Integration with LLMs for answering queries based on retrieved documents.
* **Sync & Audit**: Background jobs for synchronizing data sources and comprehensive audit logging.
