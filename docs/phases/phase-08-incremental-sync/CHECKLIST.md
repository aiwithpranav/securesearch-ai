# Phase 8 Checklist

## 8A Versions (merged, PR #28)
- [x] `POST /documents/{id}/versions`: stored and queued; same content as the newest version answers UNCHANGED and does nothing
- [x] The old version keeps answering until the new one is complete; the swap is one transaction
- [x] Access rules and details are not touched by a new version
- [x] `POST /documents/{id}/restore` and `GET /documents?deleted=true`; restored with the same rules, searchable after re-indexing
- [x] The date shown with a passage is the date of its version
- [x] Screens: upload a new version, "In use" on the current version, Deleted tab with Restore
- [x] 14 new backend tests (606 total), 5 new frontend tests (101 total), 11 mutations all caught, real-browser check with real worker, 360 px
- [x] Owner manual checks and approval (merged, PR #28)

## 8B Sync engine (merged, PR #29)
- [x] CR-004, migration `0008` (`sync_sources`, `sync_runs`, one document per source item), ADR 034
- [x] Connector interface, diff (new, changed, unchanged, permission-only, deleted, restored), teams and members follow the source
- [x] Guards: unreachable, empty listing, too many deletes, repeated ids, bad items, one run per source, stale runs
- [x] Scheduler (worker with `-B`, tick every minute), `POST /sync/sources/{id}/run`, runs and sources routes
- [x] 46 new backend tests (652 total), 18 mutations all caught, real worker and scheduler check
- [x] Owner approval (merged, PR #29)

## 8C GitHub connector (merged, PR #30)
- [x] Connector (folder, file types, `access.json` longest-prefix teams, `users.json`, repository collaborators), token worker-only, failure codes; ADR 035
- [x] Sources screen (add a GitHub source, Sync now, automatic sync, interval, last and recent runs), Sources link in the Manage menu
- [x] `demo-docs/` (six invented documents and the access files)
- [x] 45 new backend tests (697 total), 16 mutations all caught, 22 new frontend tests (123 total), real-browser check with the real worker, 360 px
- [x] Owner manual checks and approval (merged, PR #30)
- [ ] Live check with the real repository (optional, with a short-lived read-only token; backlog 43)

## Phase 8 close
- [x] Owner approval, PRs merged
- [ ] Tag `v0.8` (after this docs PR is merged)
