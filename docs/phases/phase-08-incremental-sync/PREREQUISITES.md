# Phase 8 Prerequisites

| Item | Why | How to check |
|---|---|---|
| Docker Desktop running, stack up | The tests use the real database | `docker compose ps` shows the services running |
| (8C only) A private GitHub repository with synthetic `.md` files | The connector needs something to import | Claude gives the sample files |
| (8C only) A read-only fine-grained GitHub token in your local `.env` | Lets the connector read that one repository | Claude only checks that it is set, never prints it |
| Delete the token when the check is done | Keeps the token short-lived | GitHub settings |

Cost: 0. 8A and 8B need nothing from you.

## The live GitHub check (after the 8C merge): make a short-lived read-only token
1. GitHub, top right picture, **Settings**. Left menu, bottom, **Developer settings**.
2. **Personal access tokens**, then **Fine-grained tokens**, then **Generate new token**.
3. Name `securesearch-sync`. Expiration: **7 days**.
4. Repository access: **Only select repositories**, choose `securesearch-ai`.
5. Repository permissions: **Contents: Read-only**, **Metadata: Read-only**, **Administration: Read-only** (this one lets it list collaborators).
6. **Generate token**, copy it once. Put it in your local `.env` as `GITHUB_TOKEN=...` (never in chat, never in a file that is committed).
7. `docker compose up -d` so the worker picks it up. When the check is done, delete the token on GitHub.
