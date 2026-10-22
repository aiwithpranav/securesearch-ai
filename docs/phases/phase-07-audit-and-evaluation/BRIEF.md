# Phase 7 Brief: Audit and evaluation

**Goal:** prove the product works and is safe. An append-only audit trail shows who asked what and what happened; an evaluation runs 60+ questions and reports leakage (must be 0%), Recall@5, citation correctness, refusal accuracy and speed, and compares keyword, vector and hybrid search.

**Requirement IDs:** FR-13 (audit log), FR-14 (evaluation runner), FR-19 (audit export), FR-31 (admin overview), FR-32 (knowledge gaps), NFR-01.

## Layers (each needs the owner's approval)
| Layer | Content | Status |
|---|---|---|
| **7A** Audit | Migration `0006`, append-only audit tables, audit routes and CSV export, security events saved, ADR 031 | Merged (PR #23) |
| **7B** Evaluation | About 48 synthetic documents with canary strings, 60+ cases, canary scanner, runner, metrics, mode comparison, report, threshold tuning | Done, merged (PR #24) |
| **7C** Dashboards | Audit screen, admin overview, knowledge gaps, evaluation dashboard, employee home | Done, merged (PR #25) |

## Security rules that apply
- The audit holds the question, ids, counts and code words. Never answer text, never document text.
- Append-only in the database; no audit means no answer.
- Only `security_admin` and `auditor` read it. The `system_admin` cannot ("admin is not auditor").
- An export is recorded before any data is sent; CSV cells cannot run as spreadsheet formulas.

## Out of scope
Incremental sync and permission-hash logic (Phase 8), final hardening, privacy text and security report (Phase 9).

## Estimate
Blueprint: 8 to 11 days. Plan: 7A about 3, 7B about 4, 7C about 3.
