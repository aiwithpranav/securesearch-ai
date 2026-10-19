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
