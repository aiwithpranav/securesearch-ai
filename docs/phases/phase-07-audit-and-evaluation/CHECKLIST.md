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
- [x] Owner manual checks and approval (merged, PR #23)

## 7B Evaluation (merged, PR #24)
- [x] 36 extra synthetic documents (48 total), canaries in all 23 restricted ones, access rules
- [x] 62 cases in the blueprint categories (5 prompt-injection, 14 scenarios)
- [x] Canary scanner over answers, search results, prompt, audit rows and logs; independent oracle
- [x] Runner, metrics, keyword / vector / hybrid / hybrid + reranker comparison, saved runs, API and command line
- [x] Refusal threshold tuned by measurement (0.03 to 0.30); `docs/evaluation-report.md`, ADR 032
- [x] 46 new tests (572 total), 14 mutations (13 caught, 1 equivalent), real-stack run 62 of 62 with 0 leaks
- [x] Owner manual checks and approval (merged, PR #24)

## 7C Dashboards (built, waiting for owner review)
- [x] Backend: admin overview, knowledge gaps (masked, no names), suggested questions; 20 tests
- [x] Manage menu by role; Audit, Overview, Knowledge gaps, Evaluation screens; employee Home
- [x] Weak-match note aligned to 0.30
- [x] 96 frontend tests, build passes, 6 mutations caught, real-browser check with temporary people, 360 px
- [ ] Owner manual checks and approval

## Phase 7 close
- [ ] Owner approval, PRs merged, tag `v0.7`
