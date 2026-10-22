# Phase 8 Prerequisites

| Item | Why | How to check |
|---|---|---|
| Docker Desktop running, stack up | The tests use the real database | `docker compose ps` shows the services running |
| (8C only) A private GitHub repository with synthetic `.md` files | The connector needs something to import | Claude gives the sample files |
| (8C only) A read-only fine-grained GitHub token in your local `.env` | Lets the connector read that one repository | Claude only checks that it is set, never prints it |
| Delete the token when the check is done | Keeps the token short-lived | GitHub settings |

Cost: 0. 8A and 8B need nothing from you.
