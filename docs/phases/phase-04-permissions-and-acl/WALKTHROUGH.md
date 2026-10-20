# Phase 4 Walkthrough

Grows with each layer. Layer status: **4A built and merged**, **4B built (waiting for owner review)**, 4C not started.

## Layer 4A: access tables and the access resolver

### 1. What we built
- **Four new tables:** `groups`, `user_groups` (who is in which group), `document_acl` (the access rules) and `permission_change_events` (history of rule changes).
- **The access resolver:** one piece of code that answers "may this user READ / DOWNLOAD / MANAGE this document?" using the blueprint rules.
- A very thorough set of tests for it, because a mistake here would leak documents.
There is still no screen or API for rules (4B and 4C). The resolver is what search (Phase 5) will use.

### 2. How it works, step by step
A rule says: *who* (a user, a role, a group, a department, or everybody = COMPANY), *gets or loses* (ALLOW or DENY), *which permission* (READ, DOWNLOAD, MANAGE), *until when* (optional).

To READ a document, ALL of these must be true:
1. The user exists and is active.
2. The document is not deleted and its status is READY.
3. **No** matching DENY rule exists (a DENY always wins).
4. A matching ALLOW rule exists that has not expired. **No rule = no access** (deny by default).
5. The user's clearance level is at least the document's sensitivity.
6. The document's country list is empty, or contains the user's country.

The database answers this in one SQL statement, **every time**, from the data as it is right now. Nothing is cached and nothing comes from the login token, so removing someone from a group takes effect on their next request.

- **DOWNLOAD** also needs READ, plus its own ALLOW DOWNLOAD rule (there is no download feature yet).
- **MANAGE** (edit the document and its rules) does not give READ. An administrator (`system_admin`) can always manage, even if a DENY exists, so rules can always be repaired, but the role **never** gives READ.
- The resolver can also **explain** a "no" with a code such as `NO_ALLOW_RULE` or `CLEARANCE_TOO_LOW` (for administrators; users will only ever see one uniform refusal).

Terms: **ACL** = access control list (the rules); **principal** = who a rule is about; **clearance** = how secret a user may see (0 to 4); **sensitivity** = how secret a document is (0 PUBLIC to 4 HIGHLY_RESTRICTED); **allow-list** = the list of documents a user may read.

### 3. Important files
| File | Job |
|---|---|
| `backend/migrations/versions/..._0003_access_tables.py` | Creates the four tables with safety constraints |
| `backend/app/models/access.py` | Table definitions |
| `backend/app/access/resolver.py` | The rules, the allow-list, single checks, explanations |
| `backend/tests/access_world.py` | Helper that builds small test worlds (users, groups, documents, rules) |
| `backend/tests/test_access_resolver.py` | Table-driven tests of every rule |
| `backend/tests/test_access_oracle.py` | Random-world comparison with an independent Python version, and database constraint tests |
| `docs/adr/027-access-decision-design.md` | The decisions behind the rules |

### 4. Tools: why we chose them
- We used **plain SQL through SQLAlchemy** for the rules, because the database can answer "who may read what" in one query, close to the data. We did not filter in Python after fetching, because that is how data leaks (a forgotten filter) and it does not scale.
- We used a **second independent implementation (an oracle) plus random worlds** to test, because two different programs agreeing on thousands of cases is much stronger proof than hand-picked examples alone.
- We used **mutation checking** (breaking a rule on purpose and checking that a test fails) because a test that never fails proves nothing.
- We used **database constraints** (allowed words, COMPANY has no principal, no duplicate rules) so even a buggy API cannot store a malformed rule.
- No new packages.

### 5. How to run it
Stack running as before. In PowerShell, from `D:\AI\RAG\Secure_Search_AI`:
```powershell
docker compose up --build -d
docker compose exec backend alembic upgrade head      # creates the four tables (migration 0003)
```

### 6. How to test it
```powershell
docker compose exec backend pytest -q                 # 261 tests
docker compose exec backend pytest -q tests/test_access_resolver.py tests/test_access_oracle.py   # only the access tests (92)
```
(After editing tests, copy them in first: `docker compose cp backend/tests/. backend:/app/tests/`.)

### 7. Actual results (checked by me)
- `alembic check` clean; 261 backend tests pass (92 new).
- Every rule, every principal type, all 25 deny-beats-allow combinations, expiry (live and expired, ALLOW and DENY), clearance edges, country lists (including an empty list), document states, deactivated and unknown users, revocation by group, department, rule, user and document, MANAGE and DOWNLOAD are covered.
- 8 random worlds (7 users, 14 documents, up to 70 rules): the allow-list, the single check, the explanation and the independent Python oracle agree on all 2,352 combinations (294 per world).
- **Mutation check:** I broke the resolver 8 different ways (deny ignored, `<` instead of `<=`, country gate removed, expiry ignored, admin may read, document status ignored, inactive user allowed, any group matches). The tests caught all 8. The resolver was restored and verified identical.
- The database refuses malformed and duplicate rules.

Not verified yet: the rules through the API and screens (4B, 4C); speed with thousands of documents.

### 8. Limitations and open issues
- No API or UI for rules yet. Existing documents have no rules, so they are invisible to everybody (correct by design).
- The allow-list is a SQL query, fine for the planned size; very large corpora are a known blueprint limitation.
- See `docs/CHALLENGES.md` entries 54 to 56.

## Layer 4B: groups, rules, history, preview and demo data (API)

### 1. What we built
The API around the 4A engine:
- **Groups:** create groups, add and remove members, see who is in a group.
- **Access rules on a document:** list, add, edit and delete rules (who gets or loses READ, DOWNLOAD or MANAGE, optionally until a date).
- **History:** every change to a document's rules is recorded with the full list before and after, who did it and when.
- **Access preview:** "can this person read this document, and why (or why not)?" for administrators, with a stable reason code and the rules that matched.
- **Demo data:** 6 groups, members and rules for the 12 demo documents that follow the blueprint personas.
Still no screens (4C), and still no way to read a document (search comes in Phase 5).

### 2. How it works, step by step
1. **Who may call:** groups are for `system_admin` only. Rules, history, preview and editing a document's metadata need **MANAGE on that document** (a `system_admin`, or someone with an ALLOW MANAGE rule and no DENY MANAGE). Everyone else gets "Document not found" (404), exactly like a missing document, so nobody can learn which documents exist.
2. **Adding a rule:** the server checks that the person, role, group or department really exists (the database has no link for it), that COMPANY has no principal, and that an expiry lies in the future. A rule that already exists answers 409.
3. **Saved together:** the rule and its history row are written in ONE transaction. If the history cannot be written, the rule is not saved either (tested).
4. **Instant effect:** nothing is cached. The preview and (from Phase 5) search read the rules and group memberships as they are at that moment, so removing someone from a group changes the next answer immediately.
5. **Preview:** it runs the same checks as the real decision, one by one, and returns the first one that fails: `NO_ALLOW_RULE`, `DENIED_BY_RULE`, `CLEARANCE_TOO_LOW`, `COUNTRY_NOT_ALLOWED`, `DOCUMENT_UNAVAILABLE`, `USER_INACTIVE`.
6. **MANAGE is not READ:** a person who can manage a document's rules still cannot read it unless a READ rule also allows them. The system administrator can always manage (so rules can be repaired) but is never a reader because of the role.

### 3. The demo rules (who reads what)
Company-wide documents are open to everyone (subject to clearance). The HR salary bands go to the HR Team and HR managers; the CEO is allowed by role but denied by name ("everything except one"). The finance forecast goes to the Finance Managers group and executives, but the finance analyst's clearance (2) is below its sensitivity (3), so the clearance gate stops him. Engineering and support documents are tied to the engineer role and the SRE group, not to a whole department, so the system administrator (who sits in Engineering) cannot read them. The auditor reads only company-wide documents.

| Person | Reads |
|---|---|
| swara (engineer, SRE) | company-wide 4 + payments runbook, support escalation, team note = 7 |
| pranav (finance analyst) | company-wide 4 (forecast blocked by clearance) |
| dhanashree (HR) | company-wide 4 + salary bands = 5 |
| akshay (sales) | company-wide 4 + pricing playbook = 5 (clearance raised to 2 for this) |
| sanjana (security) | company-wide 4 + incident report = 5 |
| shivam (CEO) | company-wide 4 + forecast, pricing, incident report, vendor contract = 8 (not the salary bands) |
| prashant (administrator) | company-wide 4 only |
| karunesh (auditor) | company-wide 4 only |
| former (deactivated) | nothing |

### 4. Important files
| File | Job |
|---|---|
| `backend/app/services/access_service.py` | Rule, group, history and preview logic |
| `backend/app/api/v1/access.py` | The endpoints and the MANAGE check |
| `backend/app/schemas/access.py` | Request and response shapes (no text fields) |
| `backend/app/scripts/seed_access.py` | Demo groups and rules (safe to run twice) |
| `backend/tests/test_groups_acl_api.py` | API tests: who may call, validation, history, preview, revocation |
| `backend/tests/test_access_seed.py` | The persona matrix |
| `docs/change-requests/CR-003-access-endpoints.md` | The three extra endpoints |

### 5. Tools: why we chose them
- We used **plain REST routes with one shared "may manage this document" check**, so no route can forget it. We did not check inside each route by hand.
- We answer **404 instead of 403** when you cannot manage a document, because 403 would reveal that the document exists.
- We store the **full rule list before and after** each change (JSON) instead of tiny diffs, because an auditor can read it without replaying anything.
- No new packages.

### 6. How to run it
In PowerShell, from `D:\AI\RAG\Secure_Search_AI` (stack running, demo users and documents loaded):
```powershell
docker compose up --build -d
docker compose exec backend alembic upgrade head
docker compose exec backend python -m app.scripts.seed_access     # creates the demo groups and rules
```
Try it in the API docs (http://localhost:8000/api/docs): log in as `prashant@demo`, click Authorize, then call `GET /groups`, `GET /documents/{id}/acl` and `GET /documents/{id}/access-preview?user_id=...` (ids come from `GET /documents` and `GET /users`).

### 7. How to test it
```powershell
docker compose exec backend pytest -q        # 283 tests
```

### 8. Actual results (checked by me)
- `alembic check` clean; 283 backend tests pass (22 new).
- Tests: every route needs the right caller (401, 403, 404); rules for every principal type; bad principals, bad expiry, duplicates refused and leave no history; edit and delete; history before/after; rule and history saved together or not at all (a forced failure left no rule); MANAGE holder works only on its own document and cannot read; DENY MANAGE stops a manager but never the administrator; preview reasons; instant revocation; no document text anywhere; the persona matrix above.
- **Live on the running system:** I ran the seed twice (second run added nothing) and asked the access preview API for 9 people by 13 documents (117 answers). Every person's readable set matched the table exactly, with the denial reasons `NO_ALLOW_RULE` (60), `USER_INACTIVE` (13), `CLEARANCE_TOO_LOW` (1) and `DENIED_BY_RULE` (1). Removing Swara from the SRE group changed her access to the support guide to "no" at once; adding her back restored it.

Not verified: the screens (4C); speed with thousands of documents.

### 9. Limitations and open issues
- No screens yet (4C). Groups cannot be renamed or deleted yet (not in the API contract; backlog).
- Group membership changes are written to the security log, not to `permission_change_events` (that table is for document rules); a full audit view comes in Phase 7.
- See `docs/CHALLENGES.md` entries 57 to 60.
