# Phase 7 Prerequisites

| Item | Why | How to check |
|---|---|---|
| Docker Desktop running, stack up | The tests use the real database | `docker compose ps` shows 6 services `(healthy)` |
| OpenAI key in your local `.env` (only for a LIVE evaluation run in 7B) | A live run asks the real model about 60+ questions (about $0.05 with GPT-4o mini). All tests and the default evaluation use a fake model | Claude only checks that it is set and shows the cost estimate before a live run |
| Delete the key at OpenAI when the live run is done | Keeps the key short-lived | OpenAI dashboard |

Cost: 0 for 7A and 7C. About $0.05 per full live evaluation in 7B. No new accounts.
