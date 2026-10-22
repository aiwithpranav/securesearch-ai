# Phase 8 Walkthrough

## Layer 8A: versions, "nothing to do" and restore

### 1. What we built
A document can now get a newer file without losing anything. Sending the same file again does nothing. A deleted document can be brought back. The date next to a cited passage is the date of the version it came from.

### 2. How it works, step by step
1. **New version** (`POST /documents/{id}/versions`, system administrator): the file is checked like any upload. If its fingerprint (SHA-256) equals the newest version, the answer is `UNCHANGED` and nothing is stored or queued. If it equals another live document, the answer is a conflict. If the document is still being processed, also a conflict.
2. Otherwise the file is stored as version N+1 and one indexing job is queued. The document stays `READY` and the old passages keep answering.
3. When the job finishes, the swap is one transaction: old passages off, new passages on, current version updated. A search sees the complete old version or the complete new one, never a mix.
4. Access rules, title, department and sensitivity are not touched.
5. **Delete** (soft, as before) keeps the rules. **Restore** (`POST /documents/{id}/restore`) clears the deletion and queues one indexing job from the newest stored version; the document is searchable again when it is `READY`. A restore is refused if its content now exists in another live document.
6. `GET /documents?deleted=true` lists deleted documents (for the Restore button).
7. **Dates:** a cited passage and the evidence panel show the date of the version the passage belongs to.
8. **Screens:** the document page has "Upload a new version" and marks the version in use; the list has Active and Deleted tabs with a Restore button.

### 3. Important files
`backend/app/services/document_service.py` (`upload_new_version`, `restore_document`), `backend/app/api/v1/documents.py`, `backend/app/retrieval/search.py` and `backend/app/api/v1/chat.py` (version date), `frontend/lib/documents.ts`, `frontend/app/(portal)/(app)/admin/documents/`. Tests: `backend/tests/test_versions.py`. ADR 033.

### 4. Tools: why we chose them
Nothing new. The ingestion pipeline already swapped passages in one transaction (Phase 3B); 8A only adds the entry points and the rules around them.

### 5. How to run it
`docker compose build backend && docker compose up -d`, then `cd frontend; npm run dev`. Sign in as `prashant@demo`, open a document, use "Upload a new version".

### 6. How to test it
`docker compose exec backend python -m pytest tests/test_versions.py -q` (14 tests); `cd frontend; npx vitest run` (101 tests).

### 7. Actual results (checked by me)
- 606 backend tests and 101 frontend tests pass; type check and production build clean.
- 11 deliberate mistakes (unchanged check removed, duplicate check wrong, busy check removed, restore not clearing the deletion, restore without the duplicate check, status reset on every upload, orphan file left behind, deleted list wrong, deleted documents accepted, version date lost in search and in the evidence panel) were all caught.
- In a real browser with a temporary administrator (deleted afterwards): a document became Ready, a new version was uploaded and indexed by the real worker, the same file again said "Nothing was changed", the document was deleted, listed under Deleted, restored and became Ready again; no page scrolled sideways at 360 px.

### 8. Limitations and open issues
- Passages of old versions stay in the database as inactive rows (backlog 38).
- There is no "make version 2 current again" button; send the old file as a new version.

## Layer 8B: the sync engine (backend only)

### 1. What we built
The machinery that keeps the documents of one source in step with that source, doing only what changed. There is no screen yet and no real connector yet (8C); the engine is proven with a fake source.

### 2. How it works, step by step
1. A **source** (`POST /sync/sources`, system administrator) has a kind, non-secret settings (department, document type and sensitivity for new documents) and an interval (default 15 minutes). A settings key such as `token` or `password` is refused: tokens stay in `.env`.
2. A **run** (`POST /sync/sources/{id}/run`, or the scheduler every minute for sources that are due) lists the source's items and its teams with their members.
3. **Teams and members:** teams are created as `<kind>:<source name>:<team>` and their members are made to match the source (people with no account are ignored and counted). A person removed from a team loses access at the next query, even if no document changed.
4. **Per item:** new item, upload and give the teams read access. Same file and same readers, skipped. Same file, other readers, only the rules change (no re-indexing). Changed file, a new version (the old one keeps answering until the new one is ready). Gone from the source, soft deleted. Back again, restored.
5. **Only the source's own rules:** the engine writes `ALLOW READ` for its own teams and nothing else. Rules an administrator added by hand (users, roles, DENY, other groups) are never touched, and the group screens refuse to edit a managed team.
6. **Safety guards:** an unreachable source changes nothing; an empty listing, or one that would delete more than half of the documents, stops the run before anything changes; one bad file is counted and the run ends `PARTIAL`; one run per source at a time; a run stuck for 30 minutes counts as stale.
7. Every run is saved with counts, code words and the source's item ids. Never document text.

### 3. Important files
`backend/app/sync/base.py` (connector interface, secret check, permission hash), `backend/app/sync/engine.py`, `backend/app/api/v1/sync.py`, `backend/app/models/sync.py`, migration `0008`, `backend/app/worker/tasks.py` and `celery_app.py` (scheduler), `docker-compose.yml` (worker runs with `-B`). Tests: `backend/tests/test_sync.py`. `docs/change-requests/CR-004-sync-sources.md`, ADR 034.

### 4. Tools: why we chose them
Celery beat (already part of Celery) for the schedule, so no new container. A fake in-memory source for the tests, so the engine is proven before any network is involved.

### 5. How to run it
`docker compose build backend && docker compose up -d` (the worker now also runs the scheduler), then `docker compose exec backend alembic upgrade head`. Open `/api/docs` as `prashant@demo` to see the `sync` routes. A real source arrives in 8C.

### 6. How to test it
`docker compose exec backend python -m pytest tests/test_sync.py -q` (46 tests).

### 7. Actual results (checked by me)
- 652 backend tests pass; `alembic check` clean after migration `0008`.
- 18 deliberate mistakes (the hash checks, rule removal, a rule filter that would touch other teams, member removal, the empty and mass-delete guards, deletion, restore, error isolation, the repeated-id check, stale cleanup, the enabled flag, the permission mark, the team prefix, unknown members, the manual-edit refusal, granting every team) were all caught.
- Real worker and scheduler: a source of an unknown kind was started by the scheduler on its own within a minute and closed with `UNKNOWN_KIND` (then deleted).

### 8. Limitations and open issues
- No real connector and no screen yet (8C).
- Every run reads each file again to compare its fingerprint (backlog 40).
- An item deleted here, changed in the source and then restored is restored with the old file first; the next run picks up the new one.
- See `docs/CHALLENGES.md` entries 118 to 122.

