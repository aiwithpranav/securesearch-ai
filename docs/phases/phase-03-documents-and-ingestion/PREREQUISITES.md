# Phase 3 Prerequisites

| Item | Why | How to check |
|---|---|---|
| Docker Desktop running | Runs 6 services now (postgres, redis, mailpit, storage, backend, worker) | `docker version` shows a Server version |
| Internet during the first build | Downloads PyTorch (CPU), Python packages and the embedding model (about 130 MB) once | `docker compose build` finishes. If `apt-get` or `pip` fails with a network error, run the build again |
| Free disk | Backend image about 2.7 GB, SeaweedFS image about 0.7 GB, plus storage data | `docker system df`. Blueprint asks for about 3 GB free |
| New `.env` keys | `S3_ENDPOINT_URL`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `S3_BUCKET` | Run `powershell -ExecutionPolicy Bypass -File scripts/setup_env.ps1` from the repo root. With an existing `.env` it only ADDS missing keys and shows no values |
| RAM | The embedding model needs well under 1 GB | Owner machine has 24 GB |

No paid service and no API key is needed. Cost: 0. No GPU is needed.
Sample data: synthetic documents are generated in 3B. Never use real company files.
