# ADR 031: Audit trail (Phase 7A)

## Status
Accepted (2026-10-22). The owner approved the Phase 7 plan ("do what you think right, start 7A") with six proposed decisions. The owner can reverse any item.

## Context
Blueprint FR-13 and FR-19, threat T7 and section 3.4: an audit log records user, query, filters, chunk ids, status and latency, with no raw document text; auditors can export it; the log itself must not leak.

## Decision
- **Three append-only tables** (migration `0006`): `query_audit_logs` (one row per search or answer: person, kind SEARCH or CHAT, the question, filters such as the mode, how many documents the person could read, retrieved passage ids, outcome, latency, request id), `answer_audit_logs` (one row per answer or refusal: cited passage ids, model, a short fingerprint of the system prompt, calls, tokens, answer LENGTH, a refusal code word) and `access_events` (sign-ins, failures, lockouts, token reuse, password changes, and every change an administrator makes to people, groups, documents and rules, with ids only).
- **Append-only in the database itself:** a trigger refuses UPDATE and DELETE on all three tables, whoever connects. `user_id` has no foreign key, so the trail survives anything that happens to an account. Deleting a history item or a person never touches the trail.
- **What is stored:** the question text (auditors need it; only the audit roles read it) and ids, counts and code words. **Never the answer text and never document text.** The log therefore cannot leak what an answer said and never outlives the permission an answer was built on.
- **No audit, no answer:** the audit rows are written in the same request, in the same transaction as the person's history. If they cannot be saved the request fails and nothing is returned (also on the stream). A question the model could not answer is audited with status `UNAVAILABLE`. When no key is set the route answers 503 before anything is asked, so there is nothing to audit.
- **Security events** are written from the one place that already logs them (`security_event`): every event whose name starts with `auth.`, `admin.` or `audit.` is saved with ids and a short list of fixed fields (changed field names, role names, rule type, effect, permission). Free text, emails and passwords are dropped. A failed write is logged and never breaks the action; the query trail is the part that fails closed.
- **Who may read:** only `security_admin` and `auditor`. The `system_admin` may not ("admin is not auditor", like "admin is not reader"): administrators manage the system, they do not audit themselves.
- **API:** `GET /audit/queries` (filters: person, kind, status, dates, text; paged, at most 200), `GET /audit/answers`, `GET /audit/access-events`, `GET /audit/export` (CSV, at most 10,000 rows, formula-safe cells). An export is itself recorded (who, when) BEFORE any data is sent.

## How it is proven
- 42 tests in `tests/test_audit.py`: one row per search and per answer with the right ids and counts; no answer or document text in any column; refusals and model failures audited; the stream audited; history deletion leaves the trail alone; UPDATE and DELETE refused by the database; no audit means no answer (search, chat and stream); roles (system_admin, employee, anonymous refused); filters, paging, the page cap, wildcard characters treated as text; events with ids only, an unknown sign-in address never stored; administrator changes with who and to whom; a failing event write never breaks an action; the CSV is safe and the export is recorded first; forbidden text never reaches any audit table; no answer or text field in the schemas.
- Mutation check: 14 deliberate mistakes (system_admin allowed, export not recorded, no page cap, formulas not defused, events keep every field, admin events dropped, a filter ignored, wildcard not escaped, wrong refusal reason, search not audited, document count lost, retrieved ids lost, model failures not audited, deleting allowed) are all caught.
- Live, through the running API with temporary people (removed afterwards): the security_admin saw the searches with who, allowed documents, retrieved passages and latency; an employee and a system_admin were refused; sign-ins appeared as events; the CSV export had the rows and no answer text.

## Consequences
- Every search and answer costs one extra insert (negligible next to the model and the reranker).
- The question text sits in the audit table for as long as the trail is kept; a retention rule can be added later (backlog).
- In a production database the application user should also lack UPDATE and DELETE privileges on these tables; the trigger is the guarantee that works even without that.
