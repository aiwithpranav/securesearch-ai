# ADR 022: Pinned Versions for Phase 2A

## Status
Accepted

## Context
We need to ensure consistent behavior across environments by pinning exact versions for all images and dependencies in the backend skeleton.

## Decision
- **PostgreSQL**: `pgvector/pgvector:0.8.0-pg17` (Verified via `docker pull` that this exact tag exists and pulls successfully).
- **Redis**: `redis:7.4.2-alpine` (Verified on Docker Hub as a valid stable alpine tag).
- **Mailpit**: `axllent/mailpit:v1.22.0` (Verified on Docker Hub).
- **Python Image**: `python:3.12-slim`
- **Python Dependencies**: Pinned exactly as requested (fastapi 0.143.0, uvicorn 0.54.0, sqlalchemy 2.1.4, alembic 1.20.0, pydantic 2.14.0, pydantic-settings 2.15.0, psycopg[binary] 3.3.6, argon2-cffi 25.1.0, PyJWT 2.15.1, redis 8.1.0, pytest 9.1.1, httpx 0.28.1).
- **Added in Phase 2B**: `greenlet==3.5.6`. SQLAlchemy's async engine needs it; it was missing and only showed up when the first real database call was made. The version comes from `pip index versions greenlet` run in the `python:3.12-slim` image.

*Notes:*
- `redis 8.1.0` was pinned in Python requirements as requested, though it may refer to future versions or an external package versioning scheme. The Docker image uses `7.4.2-alpine`.

## Consequences
- Guaranteed reproducibility of environments for Phase 2.
- The user will need to update `.env` via Quick Start instructions.
