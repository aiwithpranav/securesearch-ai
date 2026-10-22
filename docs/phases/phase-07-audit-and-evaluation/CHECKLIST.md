# Phase 7 Checklist

## 7A Audit (built, waiting for owner review)
- [x] Migration `0006`: query, answer and access-event tables, append-only triggers; `alembic check` clean
- [x] Every search and answer audited (ids, counts, code words; no answer or document text)
- [x] No audit, no answer (search, chat and stream); model failures audited
- [x] Security events saved from `security_event` (ids only)
- [x] `GET /audit/queries`, `/audit/answers`, `/audit/access-events`, `/audit/export` for security_admin and auditor only
- [x] Formula-safe CSV, export recorded first, filters, paging, page cap
- [x] 42 new tests (526 backend tests in total), 14 mutations all caught, live check through the API
- [x] ADR 031, docs, challenges 95 to 99
- [ ] Owner manual checks and approval

## 7B Evaluation (not started)
- [ ] About 48 synthetic documents with canaries, 60+ cases, canary scanner, runner, metrics, report

## 7C Dashboards (not started)
- [ ] Audit, admin overview, knowledge gaps, evaluation, employee home

## Phase 7 close
- [ ] Owner approval, PRs merged, tag `v0.7`
