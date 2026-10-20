# Phase 4 Walkthrough

Grows with each layer. Layer status: **4A built (waiting for owner review)**, 4B not started, 4C not started.

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
