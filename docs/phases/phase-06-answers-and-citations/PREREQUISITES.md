# Phase 6 Prerequisites

| Item | Why | How to check |
|---|---|---|
| Docker Desktop running, stack up | The tests use the real database | `docker compose ps` shows 6 services `(healthy)` |
| OpenAI API key in your local `.env` as `OPENAI_API_KEY=...` | Only for live answers (the live check and your own runs). All tests use a fake model | `docker compose up -d` after adding it; Claude only checks that it is set, never reads it |
| A spend limit at OpenAI (for example $5 a month) and a project key | If a key ever leaks the damage stays small | OpenAI dashboard |
| Delete or revoke the key when the work needs no live check | Keeps the key short-lived | OpenAI dashboard, API keys |

Cost: about $0.0005 for 8 questions with GPT-4o mini. The key is never committed (`.env` is git-ignored) and is given to the backend container only.
