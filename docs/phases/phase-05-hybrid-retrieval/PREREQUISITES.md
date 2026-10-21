# Phase 5 Prerequisites

| Item | Why | How to check |
|---|---|---|
| Docker Desktop running, stack up | The search tests use the real database | `docker compose ps` shows 6 services `(healthy)` |
| Internet during the image build (once) | Downloads the reranker model (about 1.1 GB, public, no key) | `docker compose build backend` finishes |
| About 2 GB free disk | New model and image layers | Docker Desktop, Settings, Resources |
| Frontend on port 3000 (from 5C) | The backend allows only that address | `npm run dev` in `frontend/` |

Cost: 0. No new accounts or keys. After the build the containers stay offline.
