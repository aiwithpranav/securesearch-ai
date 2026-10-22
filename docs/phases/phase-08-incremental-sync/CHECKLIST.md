# Phase 8 Checklist

## 8A Versions (built, waiting for owner review)
- [x] `POST /documents/{id}/versions`: stored and queued; same content as the newest version answers UNCHANGED and does nothing
- [x] The old version keeps answering until the new one is complete; the swap is one transaction
- [x] Access rules and details are not touched by a new version
- [x] `POST /documents/{id}/restore` and `GET /documents?deleted=true`; restored with the same rules, searchable after re-indexing
- [x] The date shown with a passage is the date of its version
- [x] Screens: upload a new version, "In use" on the current version, Deleted tab with Restore
- [x] 14 new backend tests (606 total), 5 new frontend tests (101 total), 11 mutations all caught, real-browser check with real worker, 360 px
- [ ] Owner manual checks and approval

## 8B Sync engine (not started)
- [ ] Source interface, diff, permission-only update, scheduled sync, sync runs

## 8C GitHub connector (not started)
- [ ] Connector, group and rule mirroring, Sources screen, scenario "group removal blocks the next query"

## Phase 8 close
- [ ] Owner approval, PRs merged, tag `v0.8`
