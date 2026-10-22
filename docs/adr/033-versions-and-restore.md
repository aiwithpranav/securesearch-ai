# ADR 033: New versions, restore and the version date (Phase 8A)

## Status
Accepted (2026-10-23). Part of the Phase 8 plan the owner approved ("do what you think right"). The owner can reverse any item.

## Context
Blueprint FR-15 to FR-17: unchanged files are skipped, deleted documents leave search, versions are kept, the latest active version is preferred and its date is shown. Phase 3 already stores versions and swaps passages in one transaction; there was no way to add a version or to undo a delete.

## Decision
- **New version:** `POST /documents/{id}/versions`. Same fingerprint as the newest version: `200 UNCHANGED`, nothing stored. Otherwise version N+1 and one job; the document stays `READY` and keeps answering from the old passages until the new ones are complete (the existing single-transaction swap).
- **Guards:** a document that another live document already holds (same fingerprint) is a conflict; a document with an unfinished job is a conflict; the row is locked while the version is added; a failed database step removes the stored file.
- **Rules are untouched.** A new version never changes access rules, title, department, sensitivity or countries.
- **Restore:** `POST /documents/{id}/restore` clears the deletion and queues one job for the newest version. Passages are rebuilt from the stored file rather than switched back on, so the index always matches the file. Rules were kept by the soft delete, so the document returns with them. Refused if its content now exists in another live document.
- **Deleted list:** `GET /documents?deleted=true`.
- **Version date:** the date shown with a passage (`document_updated_at` in citations and in the evidence panel) is the creation date of the passage's version. The field name stays because the API contract is frozen; the value is more accurate than the last change of the document row (which also changes when only the title is edited).

## How it is proven
14 tests in `tests/test_versions.py`; 11 mutation checks, all caught; a real-browser check with the real worker.

## Consequences
- Old passages accumulate as inactive rows (backlog 38).
- Phase 8B reuses the same entry points: a sync that finds a changed file calls the same new-version logic; one that finds a removed file uses the same soft delete.
