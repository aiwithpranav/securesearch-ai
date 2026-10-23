# Runbook: running, backing up and recovering SecureSearch AI

For whoever looks after a running copy (a laptop, a server). Everything is plain commands. All data in this project is synthetic, but write the habits as if it were real.

## What the system keeps
| What | Where | Backed up by |
|---|---|---|
| Documents, people, access rules, passages, audit trail, sync settings | PostgreSQL (`postgres` container) | `scripts/backup.sh` (`database.dump`) |
| The uploaded original files | Object storage (`storage` container) | `scripts/backup.sh` (`files.tar`) |
| Secrets (database password, signing keys, tokens) | The `.env` file | **You**, separately (a password manager). It is never in a backup and never in Git |
| The two models | Inside the backend image | Nothing to back up: `docker compose build backend` rebuilds them |

## Is it running? (FR-37)
- Open `http://localhost:3000/status` (no sign-in): one word and a line for each part. **Operational** is good; **degraded** means the background worker is down (searching and answers work, new documents wait); **down** means the database, Redis or the file store is down.
- `http://localhost:8000/api/v1/status` is the same data as JSON; `/api/v1/health` and `/api/v1/ready` are for automatic checks.
- The administrator **Overview** shows requests, server errors and "too many requests" for the last 24 hours.
- If a part is down: `docker compose ps` (which one?), `docker compose logs <name> --tail 100`, then `docker compose up -d` (this starts anything that stopped).

## Backing up
```bash
bash scripts/backup.sh
```
Writes `backups/<UTC date and time>/` with `database.dump`, `files.tar`, `manifest.txt` (counts) and `SHA256SUMS`. On Windows use Git Bash (it comes with Git). It needs the stack running.
- **How often:** before every upgrade, and daily for a real deployment (a scheduled task or cron). Keep at least the last 7 and one a month.
- **Where:** the backup holds the company's documents and all personal data. Keep it private and encrypted at rest (for example `7z a -p` or `age`), and copy it to a second place (another disk or a private bucket). `backups/` is git-ignored: never commit one.
- **Check it:** `cd backups/<folder> && sha256sum -c SHA256SUMS` must say OK for all three files.

## Restoring
```bash
bash scripts/restore.sh backups/<folder> --yes
```
This **replaces** the current database. It checks the backup is whole, stops the app, rebuilds the database from the dump, brings the schema up to date, puts the files back, starts everything and compares counts with `manifest.txt` (documents, versions, passages, people, rules, audit questions). `Restore finished: every count matches the backup.` means success.

Recovering on a brand-new machine:
1. Install Docker and Git; clone the repository.
2. `bash scripts/setup_env.sh` (new secrets are fine: passwords live in the database; only open sessions and unused reset links end). If you kept your old `.env`, put it back instead.
3. `docker compose build backend` then `docker compose up -d`.
4. Copy the backup folder over and run the restore command above.
5. Open `/status`, sign in, ask a question as two different people and confirm the answers follow their access.

## Restore test log (NFR-16)
| Date | Test | Result |
|---|---|---|
| 2026-10-23 | Backup of the development system (50 documents, 51 files, 9 people, 80 rules, 548 audit questions), restored into a second, completely empty stack with new secrets | All six counts matched. A search as one person found the leave policy; a search as another person for a restricted topic did not return the restricted document; all 51 original files matched their recorded fingerprints; the audit tables were still append-only; the status page said operational |

Repeat this test before you rely on backups, and after any change to the backup scripts.

## Retention and housekeeping (FR-36)
- **Audit trail:** rows older than `AUDIT_RETENTION_DAYS` (default 365; `0` keeps everything; otherwise at least 30) are removed every night at 03:30 UTC. Each purge is itself recorded (counts only). Even with the setting at 30 the database refuses to delete anything younger than 30 days. See how many rows are due: `docker compose exec backend python -m app.scripts.maintenance audit-purge --dry-run`.
- **Old passages:** the passages of document versions older than the newest `KEEP_VERSIONS` (default 3) are removed every night at 04:00 UTC. Originals and version records stay. Run by hand: `docker compose exec backend python -m app.scripts.maintenance cleanup`.
- **Deleted documents** can be restored from the Documents screen (Deleted tab) until you remove them from the database yourself.

## Common problems
| Sign | Likely cause | What to do |
|---|---|---|
| Status page says *degraded* | The worker is down or just started (the heartbeat is every minute) | `docker compose ps worker`; `docker compose up -d`; wait two minutes |
| A document stays *Queued* | The worker is down | Same as above |
| *down* with *File storage* not working | The `storage` container stopped | `docker compose up -d` |
| Answers say "not available right now" | No OpenAI key in `.env` (searching still works) | Add `OPENAI_API_KEY=...` to `.env`, `docker compose up -d` |
| A GitHub source says the token is missing or refused | `GITHUB_TOKEN` not set, or expired | See Sources screen message; put a new read-only token in `.env`, `docker compose up -d` |
| Restore says the backup is damaged | The checksums do not match | Use the previous backup; never edit a backup |
