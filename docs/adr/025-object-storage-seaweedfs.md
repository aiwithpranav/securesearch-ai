# ADR 025: SeaweedFS as object storage (supersedes the MinIO choice)

## Status
Accepted (2026-10-20). Supersedes the "Object storage: MinIO (S3 API)" row of blueprint section 12.1. See `docs/change-requests/CR-001-object-storage.md`.

## Context
MinIO's open-source repository is archived and no longer maintained, and no official Docker Hub image exists. We still need a local S3-compatible store for original uploaded files.

## Decision
- Run **SeaweedFS 4.48** (`weed server -s3`) as the `storage` service in Docker Compose, on the **private network only** (no published ports).
- The application talks to it only through the `ObjectStorage` interface (`app/storage/base.py`) implemented with `boto3` (S3 API, path-style addressing, bounded retries and timeouts).
- Object keys contain only IDs and the file hash: `documents/<document_id>/v<version>/<sha256>`. No file names.
- The S3 login (`S3_ACCESS_KEY`, `S3_SECRET_KEY`) comes from `.env`; the service writes its login file at start-up, so no secret is in Git.

## Consequences
- Same S3 API as cloud S3, so moving to the cloud later is a settings change.
- Data lives in the named volume `storage_data`.
- No web console is published. Use `python -m app.scripts.storage_check`.
- Healthcheck must use the container address (`storage`), because the server listens on `-ip=storage`, not on localhost.
