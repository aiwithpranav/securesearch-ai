# Phase 2 Prerequisites

| Item | Why | How to check |
|---|---|---|
| Docker Desktop running | Runs Postgres, Redis, Mailpit, backend | `docker version` prints a Server version |
| `.env` file | Secrets live only here (git-ignored) | Run `powershell -ExecutionPolicy Bypass -File scripts/setup_env.ps1` from the repo root. It creates `.env` with random secrets and never overwrites an existing one |
| Node 20.9+ (only for 2C / frontend) | Next.js | `node -v` |

No paid services and no API keys are needed in Phase 2. Cost: 0.

The demo-user password is `SEED_USER_PASSWORD` in your `.env`. Open the file locally to read it; do not paste it in chat.
