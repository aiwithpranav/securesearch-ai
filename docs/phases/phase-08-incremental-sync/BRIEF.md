# Phase 8 Brief: Incremental sync

**Goal:** keep the index in step with the documents without redoing everything. Changed files are processed again, unchanged files are skipped, a permission-only change updates the access rules without new embeddings, deleted documents leave search and citations, and one real connector (GitHub) mirrors its source permissions into the access rules.

**Requirement IDs:** FR-15 (re-sync processes only changed files), FR-16 (soft delete), FR-17 (versions, latest preferred, version date shown), FR-20 (one real connector).

## Layers (each needs the owner's approval)
| Layer | Content | Status |
|---|---|---|
| **8A** Versions | Upload a new version, same content is skipped, restore a deleted document, version date on passages, admin screens | Done, merged (PR #28) |
| **8B** Sync engine | Source interface, diff (new, changed, unchanged, deleted), permission-only update, scheduled sync, sync runs | Built, waiting for owner review |
| **8C** GitHub connector | Import `.md` and `.txt` from a repository, mirror collaborators and teams into groups and rules, Sources screen | Not started |

## Security rules that apply
- Deny by default, DENY wins, admin is not reader: a new version, a sync or a restore never widens access.
- A restored document comes back with the rules it had, and is not searchable until it is indexed again.
- Source-managed rules are only those of groups the connector created (names start with `github:`); rules an administrator added by hand are never touched.
- Tokens only in `.env`, read-only, never logged.

## Out of scope
OCR, SSO, multi-tenant, a second connector, real-time webhooks (a scheduled sync is enough).

## Estimate
Blueprint: 5 to 7 days. Plan: 8A about 2, 8B about 2, 8C about 3.
