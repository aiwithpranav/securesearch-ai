# ADR 034: The sync engine (Phase 8B)

## Status
Accepted (2026-10-23). Part of the Phase 8 plan the owner approved ("plan ok", "do what you think right"). Needs CR-004 (two tables, a unique rule, six routes). The owner can reverse any item.

## Context
Blueprint FR-15, FR-16 and FR-20: re-sync processes only changed files, a permission-only change updates the rules without re-embedding, deleted items leave search, and one real connector mirrors source permissions. Phase 8A added new versions and restore. 8C adds the GitHub connector; the engine must not depend on it.

## Decision
- **Connector interface** (`app/sync/base.py`): `list_items()`, `read(item)` and `members()`. A connector knows nothing about the database or access rules. It returns, for each item, the names of the teams that may read it, and for each team the e-mail addresses of its members. Secrets are read from the environment by the connector, never from saved settings; settings with keys such as `token` or `password` are refused.
- **Per item** (`app/sync/engine.py`): new item, upload (version 1) then grant the teams; same content and same readers, skip; same content and other readers, change the rules only (no job, no embedding); changed content, a new version (8A) then the new readers; gone from the source, soft delete; back in the source, restore. The content check is the SHA-256 of the file (the source's own revision is not trusted). Always reading the file is a cost accepted for correctness; a cheaper "unchanged" hint is backlog 40.
- **Permission hash:** a fingerprint of the sorted team names, stored on the newest version (`document_versions.permission_hash`) only AFTER the rules are in place, so a crash between the two steps repeats the rule update at the next run instead of skipping it.
- **Teams:** created as `<kind>:<source name>:<team>`. Members follow the source at every run, so a person removed from a team loses access at the next query without any document changing. A team that vanished from the source ends up empty and its rules are removed. People the source names but who have no account are ignored and counted.
- **What is managed:** only `ALLOW READ` rules for groups with the source's prefix. DENY rules, rules for users, roles, departments, the company and groups of other names are never read or changed. The group screens refuse to edit a managed team by hand.
- **Guards:** an unreachable source changes nothing; an empty listing, or a listing that would delete more than half of at least 4 documents, stops the whole run before anything changes (switchable per source with `allow_mass_delete`); a repeated item id is refused; one bad item is counted with a code word and the run ends `PARTIAL`; one run per source (database rule); a run still `RUNNING` after 30 minutes is stale; a worker restart closes interrupted runs as `INTERRUPTED`.
- **Scheduling:** the worker runs with the Celery scheduler (`-B`); a task every minute starts a run for each enabled source that is due (its last run is older than its interval, default 15 minutes) and has no run going. Manual runs use the same path. The engine runs inside the worker with its own short-lived database engine, because each task starts a new event loop.
- **Audit:** `admin.sync_source_created`, `admin.sync_source_updated`, `admin.sync_run_started`, `admin.sync_run_finished`, with ids only. A run row holds counts, code words and the source's item ids, never document text.
- **Known edge:** an item that is deleted here, changed in the source and then returns is restored with its old file first; the new file is picked up by the next run.

## How it is proven
46 tests in `tests/test_sync.py` with a fake source; 18 mutation checks, all caught; a real worker and scheduler check (a source of an unknown kind was started by the scheduler on its own and closed with `UNKNOWN_KIND`).

## Consequences
- Audit rows of sync runs are ordinary append-only rows.
- 8C adds the GitHub connector, its settings check and the Sources screen without changing the engine.
