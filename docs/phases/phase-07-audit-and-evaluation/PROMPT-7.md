# Phase 7 prompt (summary of the approved mission)

Mission: Phase 7 of SecureSearch AI (audit and evaluation), in three layers: 7A audit trail (backend), 7B evaluation (backend, bigger synthetic data, 60+ cases, canary scanner, report), 7C dashboards (audit, admin overview, knowledge gaps, evaluation, employee home). One layer at a time, each needs the owner's approval.

Source of truth: Pre-Code Blueprint v1.2 FINAL (frozen), sections 3.4, 9.5, 13 and the Phase 7 row. Requirements: FR-13, FR-14, FR-19, FR-31, FR-32, NFR-01.

Approved on 2026-10-22 ("do what you think right, start 7A") with six proposed decisions: three layers; the audit keeps the question but never the answer text; the system_admin cannot read the audit; no audit means no answer; the evaluation runs on a fake model by default and on the real model only with the owner's key and a cost estimate; hybrid stays the default only if the measurements support it.

Rules: the audit holds ids, counts, code words and the question only; append-only; authorize before everything; secrets never in Git; synthetic data only; log every challenge in `docs/CHALLENGES.md`.
