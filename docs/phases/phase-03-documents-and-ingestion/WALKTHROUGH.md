# Phase 3 Walkthrough

Grows with each layer. Layer status: **3A built and merged**, **3B built (waiting for owner review)**, 3C not started.

## Layer 3A: storage, worker and local embeddings

### 1. What we built
Three building blocks that later layers use:
- **Object storage** (`storage` service): a private S3-style file store for the original uploaded files.
- **Background worker** (`worker` service): a separate process that runs long jobs (ingestion, from 3B), so uploads do not block the website.
- **Local embeddings**: a small AI model that turns a piece of text into 384 numbers (a "vector"). Texts with similar meaning get similar vectors; this is how search will work in Phase 5.

### 2. How it works, step by step
1. `docker compose up` now starts 6 services. `storage`, `worker`, `postgres`, `redis` and `mailpit` are on the **private** network; only `backend` also touches the public one.
2. The backend and worker both talk to storage through our own `ObjectStorage` interface (`app/storage`). The code behind it uses `boto3`, the standard S3 client.
3. Files are stored under keys made of IDs and a SHA-256 hash (`documents/<id>/v1/<hash>`), never the user's file name.
4. The worker listens to a queue in Redis (database 1). Jobs are acknowledged only AFTER they finish (`acks_late`), and a job whose worker dies goes back to the queue. So jobs must be safe to run twice (idempotent); 3B tests this.
5. The embedding model files are copied into the Docker image while it is built (the only time internet is needed). At run time `HF_HUB_OFFLINE=1`, and the worker has no internet at all. No document text can leave your machine.
6. The first time the worker embeds something it loads the model (a few seconds). After that it reuses it.

Terms: **S3** = a common API for file storage in the cloud; **embedding** = text turned into numbers; **Celery** = a Python job queue; **idempotent** = running twice gives the same result.

### 3. Important files
| File | Job |
|---|---|
| `docker-compose.yml` | Adds `storage` and `worker`; shares one image between backend and worker |
| `backend/Dockerfile` | CPU-only PyTorch, packages, and the model download pinned to an exact commit |
| `backend/app/storage/base.py`, `s3.py`, `keys.py` | Storage interface, boto3 implementation, key builder |
| `backend/app/embeddings.py` | Loads the model once; `embed_documents()` and `embed_query()` |
| `backend/app/worker/celery_app.py`, `tasks.py` | Celery setup; two test jobs: `system.ping`, `system.embed_check` |
| `backend/app/scripts/storage_check.py` | Writes, reads and deletes a test object; lists stored keys (no content) |
| `backend/app/core/config.py`, `env_doctor.py` | New settings; startup check of the storage settings |
| `scripts/setup_env.ps1` | Now also adds missing keys to an existing `.env` |
| `docs/change-requests/CR-001-object-storage.md`, ADR 024, ADR 025 | Why SeaweedFS and which versions |

### 4. Tools: why we chose them
- We used **SeaweedFS** because MinIO's open-source repository is archived and has no official image any more. We did not choose Garage (needs an extra cluster setup step for one node) or an unverified free edition. Details: CR-001.
- We used **boto3 behind our own interface** because it is the standard S3 client and keeps us free to change the storage service. We did not call SeaweedFS's own API because that would lock us in.
- We used **Celery + Redis** because jobs survive restarts and can be retried (NFR-05). We did not choose FastAPI background tasks because they are lost on restart.
- We used **BAAI/bge-small-en-v1.5** via **sentence-transformers** because it is free, small, local, MIT-licensed and gives 384 numbers (the blueprint's size). We did not choose hosted embeddings because of cost and because the text would leave the machine.
- We used **CPU-only PyTorch** because the default Linux download adds about 2 GB of GPU libraries we cannot use.

### 5. How to run it
In PowerShell, from `D:\AI\RAG\Secure_Search_AI`:
```powershell
powershell -ExecutionPolicy Bypass -File scripts/setup_env.ps1   # adds the 4 new S3 keys to .env (no values shown)
docker compose up --build -d                                      # first build takes several minutes
docker compose ps                                                 # all 6 services should say (healthy)
docker compose exec backend python -m app.scripts.storage_check
```
Stop with `docker compose down` (keeps data; `-v` deletes it).

### 6. How to test it
```powershell
docker compose exec backend pytest -q
```
If you edit test files first copy them in: `docker compose cp backend/tests/. backend:/app/tests/`.

### 7. Actual results (checked by me)
- 6 services healthy. `storage_check`: bucket created, write/read/delete OK.
- 82 backend tests pass (65 before + 17 new): storage round trip of 1 MB random data with matching hash, missing object, idempotent delete, wrong secret rejected without leaking it, dead storage gives a clean error; embeddings 384 numbers with length 1, similar text scores higher, query prefix works, model label correct and offline; worker answers a ping and embeds inside the worker; env doctor reports missing and unreachable storage.
- The worker has **no internet** (a request to huggingface.co fails), and the storage port is **not reachable from the host**.
- Versions actually installed: see ADR 024. Backend image size 2.67 GB.

Not verified yet: a worker killed in the middle of a real job gets the job again (needs a real job; tested in 3B). Storage data surviving a `docker compose down` and `up` (expected from the named volume, not tested).

### 8. Limitations and open issues
- The storage container runs as root inside the private network (backlog: non-root in Phase 9).
- No web console for storage; use `storage_check`.
- The API image carries PyTorch and the model although only the worker needs them (accepted, blueprint 8.6).
- First build needs internet and can fail on a flaky connection; run it again.
- See `docs/CHALLENGES.md` entries 35 to 40.

## Layer 3B: ingestion pipeline and admin API

### 1. What we built
Everything between "an admin uploads a file" and "its text is stored as searchable chunks with vectors":
- **Upload checks** that reject wrong, fake, empty, oversize and booby-trapped files before anything is stored.
- A **pipeline** run by the worker: read the original, extract text, cut it into chunks, turn each chunk into 384 numbers, and publish.
- An **admin API** (upload, list, edit, soft delete, re-index, jobs) and a small **notifications API** for failed jobs.
- **Synthetic demo documents** (12 files, four types) and broken-file test fixtures.
There is still **no screen** for this (3C). You can try it in the API docs page.

### 2. How it works, step by step
1. `POST /api/v1/documents/upload` (admin only, multipart form: the file plus department, type, sensitivity, optional title and countries).
2. **Checks:** only `.pdf .docx .txt .md` (the LAST extension counts); the real bytes must match (PDF starts with `%PDF-`, DOCX is a real zip with `word/document.xml`, text must be UTF-8 with no binary bytes); not empty; at most 50 MB (reading stops early); DOCX zip bombs are refused; the file name is cleaned and is only ever displayed. Identical content already uploaded gives 409.
3. The original goes to object storage under `documents/<id>/v1/<sha256>` (no file name in the key). One database commit saves the document, version 1 and a `QUEUED` job. Then the job is sent to the worker (HTTP 202).
4. The **worker** claims the job (`PROCESSING`), reads the file, checks its SHA-256 still matches, extracts text (PDF per page, DOCX headings as sections, MD `#` headings, TXT paragraphs), and cuts chunks of about 450 tokens with 50 tokens of overlap, never across a page or heading.
5. It embeds all chunks (outside any database transaction), then **publishes in ONE transaction**: old chunks off, new chunks on, document `READY`, job `READY`. A search sees the whole old set or the whole new set, never a mix.
6. **If anything fails** the job becomes `FAILED` with a fixed code (for example `NO_TEXT` for a scanned PDF); the old chunks stay active; every admin gets a notification. Storage or embedding problems are retried up to 3 times first.
7. **Safe to run twice:** a `READY` job is skipped; a job that died midway deletes its own leftovers and starts again. The database allows only one unfinished job per document. When the worker starts it re-sends unfinished jobs.

Terms: **chunk** = a piece of a document's text; **idempotent** = running twice gives the same result; **soft delete** = marked deleted but the row stays; **magic bytes** = the first bytes that show what a file really is.

### 3. Important files
| File | Job |
|---|---|
| `backend/migrations/versions/..._0002_documents_tables.py` | Creates the tables and enables `vector` |
| `backend/app/models/document.py` | Table definitions and status words |
| `backend/app/ingest/validation.py` | Upload checks |
| `backend/app/ingest/parsers.py` | PDF, DOCX, TXT, MD to text blocks |
| `backend/app/ingest/chunker.py`, `tokenizer.py` | Chunking with the model's own tokenizer |
| `backend/app/ingest/pipeline.py` | The pipeline, atomic publish, failures, retries |
| `backend/app/ingest/errors.py` | Fixed error codes and texts (never file content) |
| `backend/app/worker/tasks.py` | The Celery task and the start-up re-send |
| `backend/app/services/document_service.py` | Admin operations |
| `backend/app/api/v1/documents.py`, `notifications.py` | The endpoints |
| `backend/app/schemas/documents.py` | Response shapes (no text fields) |
| `backend/app/scripts/synthetic_docs.py`, `load_synthetic_docs.py` | Demo documents and a loader |
| `sample-data/synthetic/` | The 12 demo files (made-up company, no real data) |
| `docs/adr/026-ingestion-design.md`, `docs/change-requests/CR-002-notifications-endpoints.md` | Decisions |

### 4. Tools: why we chose them
- We used **pypdf** and **python-docx** because they are small, pure Python and need no system programs. We did not choose heavier suites (for example Apache Tika) because they need Java and add more to attack.
- We used the **embedding model's own tokenizer** to count tokens because it matches exactly what the model reads. We did not add `tiktoken` because that counts for OpenAI models, not ours.
- We used **sentence-based chunks with overlap** because a boundary never cuts a sentence and an answer on a boundary appears whole in one chunk. We did not choose fixed character slices because they cut words and sentences.
- We used **one database transaction to publish** because it is the simplest way to guarantee "complete old or complete new". We did not use a separate "inactive then flip" step because the single transaction needs no cleanup after a crash.
- We used a plain **SQL partial unique index** to allow one unfinished job per document, because the database enforces it even if two requests race.
- Dev-only: **reportlab** (BSD) creates the synthetic PDFs. New runtime packages: `pgvector` (Python helper for the vector column).

### 5. How to run it
Stack running as in 3A. In PowerShell, from `D:\AI\RAG\Secure_Search_AI`:
```powershell
docker compose up --build -d
docker compose exec backend alembic upgrade head
docker compose exec backend python -m app.scripts.load_synthetic_docs   # optional: queues 12 demo documents
```
To try an upload by hand: open http://localhost:8000/api/docs, run `POST /api/v1/auth/login` with an admin user (`prashant@demo`), copy the `access_token`, click **Authorize**, then use `POST /documents/upload`. List with `GET /documents`. Failed jobs show in `GET /ingestion/jobs?status=FAILED` and `GET /notifications`.
Demo files to upload yourself are in `sample-data/synthetic/` (see `manifest.json` for suggested metadata).

### 6. How to test it
```powershell
docker compose exec backend pytest -q
```
(After editing tests: `docker compose cp backend/tests/. backend:/app/tests/` first.)

### 7. Actual results (checked by me)
- `alembic check`: model and migration agree. 168 backend tests pass (86 new): validation (wrong types, fake files, zip bomb, hostile names, oversize), parsers (page numbers, sections, tables, bad files), chunker (size limits, overlap, no crossing of pages or sections, real tokenizer), API (401 and 403 for every route, upload rules, duplicates, rate limit, edit, soft delete, notifications are private), pipeline (all 12 demo files become chunks with 384-number vectors, failures keep the old index, atomic swap, safe retry, one unfinished job per document, logs and errors never hold document text).
- **Real worker kill test:** 12 demo documents queued, worker killed after 5 finished, restarted: all 12 `READY`, exactly one chunk set each, no leftovers, no duplicates; only the interrupted job had a second attempt.
- The API schema has no field that could hold document text, and no route returns chunks, previews or the original file.
- 12 demo documents are now loaded in your development database.

Not verified: very large real PDFs (hundreds of pages) for speed; many uploads at once; text quality of unusual PDF layouts (pypdf extracts what the PDF contains).

### 8. Limitations and open issues
- No screen yet (3C). Scanned PDFs fail with `NO_TEXT` (no OCR). Only version 1 exists; re-upload as a new version is Phase 8.
- Original files stay in storage after a soft delete until a cleanup job exists (backlog).
- Admin can see metadata and counts only, by design (admin is not reader).
- See `docs/CHALLENGES.md` entries 41 to 47.
