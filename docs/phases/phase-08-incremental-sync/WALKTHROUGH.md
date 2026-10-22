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
