# ADR 037: Operations: retention, status, counters, cleanup, backup and restore (Phase 9B)

## Status
Accepted (2026-10-24). Part of the Phase 9 plan the owner approved ("9B plan ok"). The owner can reverse any item.

## Context
Blueprint FR-36 (audit retention with a safe purge), FR-37 (health and a status page), FR-38 (backup and restore runbook with one tested restore), NFR-06 (metrics), NFR-16 (recoverability), plus backlog 38 (old passages pile up).

## Decision
- **Audit retention:** `AUDIT_RETENTION_DAYS` (default 365, `0` keeps everything, otherwise at least 30; the settings refuse other values). The audit tables stay append-only. Migration `0009` changes the trigger so a delete is accepted only when a flag set by the database function `audit_purge()` is on AND the row is older than 30 days (a floor no setting can lower), and adds `audit_purge(retention_days, dry_run)`. The function removes answer rows, then question rows, then security events, and writes one `audit.purge` event with counts only. A nightly worker job (03:30 UTC) and `maintenance audit-purge [--dry-run]` call it. The administrator Overview shows how many rows are past retention. Honest limit: the flag is not a security boundary against someone who already controls the application's database login (they could set it); it stops accidents, the ORM, and any bug, and the 30-day floor limits what even a deliberate purge can reach.
- **Health and status:** `/health` and `/ready` are unchanged (frozen contract). A new public `GET /status` runs real checks (a database query, a Redis PING, a storage listing, the worker's heartbeat) with a timeout each and returns only names, up or down, one overall word (`operational`, `degraded` when only the worker is down, `down` when the database, Redis or storage is down) and a time. It never contains a host, a version, a count or an error text; it is rate limited per address (60 a minute) and never cached. The worker writes a heartbeat to Redis every minute (expires after 3 minutes). A public page `/status` shows it and refreshes every 30 seconds; if the page cannot reach the server it says so.
- **Counters:** a small middleware counts requests, 5xx answers and 429 answers per hour in Redis (kept 48 hours; numbers only, no path, user or address; health and status calls are not counted; any failure is ignored). The Overview shows the last 24 hours.
- **Cleanup of old passages:** a nightly job (04:00 UTC) removes the inactive passages of versions older than the newest `KEEP_VERSIONS` (default 3, at least 1) of every live document. Active passages, deleted documents, original files and version records are never touched.
- **Backup and restore:** `scripts/backup.sh` writes the database (`pg_dump` custom format), the uploaded files (a tar stream with a manifest of SHA-256 fingerprints, `app.scripts.storage_archive`), `manifest.txt` (counts) and `SHA256SUMS`. `scripts/restore.sh` checks the sums, stops the app, rebuilds the database, upgrades the schema, imports the files (verified against the manifest), starts everything and compares the counts. Secrets (`.env`) are deliberately not in the backup. The scripts need Bash (Git Bash on Windows) and the running stack; passwords are read inside the containers and never printed.
- **Object storage listing** now pages through results (the store returns at most 1000 keys at a time); a backup of more than 1000 files would otherwise have been silently incomplete.

## How it is proven
35 new tests (`tests/test_ops.py`) and 9 new frontend tests; 15 mutation checks, all caught. A real restore: a backup of the development system restored into a second, completely empty stack with new secrets; all counts matched, a permission-checked search worked, 51 of 51 original files matched their fingerprints, the audit tables were still append-only and the status page said operational (logged in `docs/runbook.md`).

## Consequences
- The audit trail has an end: after the retention period old rows are gone. Anyone who needs longer must raise the setting or export first (CSV export exists since 7A).
- Scheduling runs inside the worker (Celery beat); if the worker is down, nightly jobs wait.
- Backups contain documents: they must be handled like the documents themselves.
