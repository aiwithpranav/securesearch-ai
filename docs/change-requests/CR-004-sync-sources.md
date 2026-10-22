# CR-004: Sync sources and runs (two tables, a unique rule and six routes)

Follows the blueprint Change Request process (section 2). Status: **Treated as approved on 2026-10-23**: the Phase 8 plan listed it ("migration, tables `sources` and `sync_runs`") and the owner answered "plan ok" and "do what you think right". The owner can reverse it.

## 1. What must change and why
Blueprint Phase 8 ("hash and permission-hash logic, versioning, soft delete, scheduled sync, ONE real connector", FR-15, FR-16, FR-20) needs somewhere to keep the list of connected sources and the history of sync runs. The frozen data model (section 10.1) has `documents.external_source`, `documents.external_id` and `document_versions.permission_hash`, but no table for sources or runs, and nothing that stops two documents from claiming the same source item.

## 2. What it touches
The data model and the API contract, by adding only. Nothing existing is edited.

## 3. Additive solution
- **Tables** (migration `0008`): `sync_sources` (name, kind, non-secret config, enabled, interval, last run) and `sync_runs` (status, trigger, counts, first errors, times). One RUNNING run per source (partial unique index).
- **A unique rule** on `documents (external_source, external_id)` where `external_id` is set: one document per source item.
- **Routes** (system_admin only): `GET/POST /sync/sources`, `PATCH /sync/sources/{id}`, `POST /sync/sources/{id}/run`, `GET /sync/sources/{id}/runs`, `GET /sync/runs/{id}`.
- Source configuration holds no secrets: keys such as `token`, `secret` or `password` are refused. Tokens stay in `.env`.
- Groups created by a source are named `<kind>:<source name>:<team>`. Only the rules and members of groups with that prefix are managed by the sync; manual rules and manual groups are never touched, and the group screens refuse to edit a managed group by hand.

Security: a sync can only grant `ALLOW READ` to its own prefixed groups. It never writes DENY rules, never touches rules for other principals, and never reads document text outside the normal upload and indexing path.

## 4. Decision
Add the tables, the unique rule and the routes (implemented in Phase 8B).

## 5. Consequences
The contract grows by six routes and the model by two tables. No existing client is affected.
