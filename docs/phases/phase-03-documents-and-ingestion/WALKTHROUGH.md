# Phase 3 Walkthrough

Grows with each layer. Layer status: **3A built (waiting for owner review)**, 3B not started, 3C not started.

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
