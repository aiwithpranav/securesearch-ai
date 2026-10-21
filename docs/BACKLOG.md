# Backlog

Ideas and loose ends that are NOT in the current phase. Nothing here is promised. Items move into a phase only through that phase's brief (and a Change Request if a frozen decision is touched).

| # | Item | Why / source | Planned for | Needs Change Request? |
|---|---|---|---|---|
| 1 | Admin users page (list, invite, deactivate, edit, roles) | Owner moved it out of Phase 2 (2C-3). The API already exists from 2B. Build it together with groups. | Phase 4 | No |
| 2 | Admin-initiated password reset (FR-25 part) | The frozen API contract has no endpoint. Invite and forgot-password cover the need today. | Owner decides | Yes (suggested `POST /users/{id}/reset-password`) |
| 3 | Server-side "welcome tour seen" flag | Tour is remembered per browser only. | Later, if wanted | Yes (new column and endpoint) |
| 4 | Purge job for expired or used tokens | `auth_tokens` grows forever. | Phase 9 (retention work) | No |
| 5 | Client IP handling behind a proxy | Rate limits use the direct connection address. | Phase 9 | No |
| 6 | Replace the demo accounts and name-based passwords before any real hosting | Demo passwords are guessable by design (challenge 32). | Phase 9 | No |
| 7 | Change `CONTACT_EMAIL` in `frontend/lib/site.ts` | Placeholder `you@example.com` on the landing page. | Owner, any time | No |
| 8 | Mount the backend source into the container (or use `docker compose watch`) | Edits are not visible in the container without a rebuild or copy (challenges 10, 19, 30). | Phase 9 (CI/CD polish) | No |
| 9 | ESLint and CI pipeline | Blueprint 14.3. | Phase 9 | No |
| 10 | Playwright end-to-end tests for login, reset and profile flows | Browser flows were checked by hand so far. | Phase 9 | No |
| 11 | Remove the Starlette `httpx` deprecation warning in backend tests | Harmless warning from Phase 2A. | Any time | No |
| 12 | Self-hosted font with licence check | Landing page uses the system font stack. | Optional | No |
| 13 | Run the storage container as a non-root user | It runs as root (needed to write its generated login file). Private network only. | Phase 9 | No |
| 14 | Optional dev-only storage web UI on 127.0.0.1 | CR-001: there is no console; `storage_check` lists keys. A UI could expose original files, which conflicts with "admin is not reader", so only if the owner wants it. | Owner decides | No |
| 15 | Lighter API image without PyTorch | Backend image is 2.7 GB (challenge 38). | Phase 9 | Yes (blueprint says same image) |
| 16 | Clean up original files in storage after a document is deleted | Soft delete keeps the stored original (ADR 026). Needs a safe cleanup job. | Phase 9 | No |
| 17 | Upload a NEW version of an existing document (version 2, 3...) | 3B only has re-index of version 1. | Phase 8 (FR-15 to FR-17) | No |
| 18 | OCR for scanned PDFs | Scanned files fail with `NO_TEXT`; OCR is out of scope in the blueprint. | Owner decides | Yes |
| 19 | GIN full-text index and HNSW vector index on `document_chunks` | Belong to Phase 5. | Phase 5 | No |
| 21 | Upload progress bar | Upload shows a spinner only; 50 MB files feel slow. | Later | No |
| 22 | Faster alerts in the notification bell | The bell polls every 30 s; instant alerts need shorter polling or server-sent events. | Later | No |
| 23 | Rename and delete groups | Not in the API contract; groups can only be created and filled. | Later | Yes |
| 24 | Screen for non-admin MANAGE holders | The API honours MANAGE for non-admins, but they have no way to find their documents in the UI. | Phase 6 or later | No |
| 25 | Audit view of group membership changes | They go to the security log only; `permission_change_events` covers document rules. | Phase 7 | No |
| 20 | Heartbeat for running jobs | After a worker restart, a still-running duplicate could process a job twice; harmless (idempotent) but wasteful. | Phase 9 | No |
| 26 | Rule history stores ids only | The screen resolves names from current lists, so a renamed group shows its new name in old entries. Storing names in the snapshot needs a backend change. | Later | No |
| 27 | Admin-initiated password reset and user hard delete | Out of 4C scope (owner decision); people reset their own passwords. | Later | No |
| 28 | Reranker speed | About 0.5 to 2 s per search on CPU for 20 candidates, up to 9 s when 6 people search at once. Lower the candidate count or cache if Phase 7 shows the P95 over 5 s. | Phase 7 | No |
| 29 | Refusal threshold | 0.03 is provisional (tiny question set); tune on the 60+ questions. | Phase 7 | Yes |
