# ADR 027: Access decision design (Phase 4)

## Status
Accepted (2026-10-20). The owner approved the Phase 4 plan with its 8 decisions ("Approve"). The owner can reverse any item.

## Context
Blueprint section 9.2 gives the five access rules (A to E) and section 9.4 the three permissions. It leaves some details open (what a DENY with an expiry does, how MANAGE and DOWNLOAD relate to READ, how an admin can fix rules on a document nobody may manage). This ADR fixes them so the code and the tests agree.

## Decision
- **One resolver, one place:** `app/access/resolver.py` is the only code that decides access. It builds SQL; the database does the work. Everything is read at request time from the database. Nothing is cached, and nothing is read from the login token (the token holds only the user id), so a revocation works on the very next request.
- **READ** needs all of: the user exists and is active; the document is not deleted and its status is `READY` (the blueprint's `PUBLISHED` sketch is replaced by `READY`, ADR 026); no matching DENY; a matching unexpired ALLOW; clearance at least the sensitivity; the country list empty or containing the user's country. No rule means no access (deny by default).
- **A rule matches** when its principal is the user, one of their roles, one of their groups, their department, or COMPANY (everybody).
- **Expiry applies to both effects:** an expired ALLOW grants nothing and an expired DENY blocks nothing.
- **DOWNLOAD** = everything READ needs, plus an unexpired ALLOW DOWNLOAD rule and no matching DENY DOWNLOAD. There is no download endpoint yet (the API contract has none), so this is stored and tested only.
- **MANAGE** (edit metadata and rules) does not imply READ and is not limited by clearance or country. It needs a not-deleted document (any status, so failed uploads can be fixed) and either the **system_admin** role or an ALLOW MANAGE rule with no matching DENY MANAGE. The admin's implicit MANAGE **cannot be blocked by a DENY**, so someone can always repair the rules. `system_admin` never gives READ.
- **Rule storage:** `document_acl` with `principal_type` (USER, ROLE, GROUP, DEPARTMENT, COMPANY), `principal_id` as text (no foreign key, blueprint 10.1; the service must check that the principal exists), `effect`, `permission` (READ, DOWNLOAD, MANAGE; SEARCH was dropped in the blueprint), `expires_at`. The database enforces the allowed words, that COMPANY has no principal and the others have one, and that the same rule cannot exist twice.
- **History:** `permission_change_events` keeps the full rule list before and after every change (never document text). It is written by the API layer in 4B in the same transaction as the change.
- **Explanations:** `decision_steps` runs the same rule pieces one by one and returns a stable code (`NO_ALLOW_RULE`, `DENIED_BY_RULE`, `CLEARANCE_TOO_LOW`...). It is for administrators (access preview, 4B); users only ever see the uniform refusal in Phase 6.

## How it is proven
- Table-driven tests for every rule, every principal type, deny-beats-allow for all 25 combinations, expiry, clearance edges, country lists, document and user state, revocation (group, department, rule, user, document), MANAGE and DOWNLOAD.
- A second, independent Python "oracle" follows the same rules and is compared with the SQL in 8 random worlds (294 user, document and permission combinations per world, 2,352 in total): allow-list, single check and explanation must all agree with it.
- Mutation check: 8 deliberate mistakes in the resolver (deny removed, `<` instead of `<=`, country gate removed, expiry ignored, admin reads, status ignored, inactive user allowed, any-group match) were each caught by the tests.

## Consequences
- Phase 5 retrieval must call the allow-list (`readable_ids_stmt`) inside its SQL, never filter afterwards.
- The allow-list is a `SELECT`, so it scales with the database; very large corpora may need the materialised approach named in the blueprint's known limitations.
- A DENY MANAGE for the admin is ignored on purpose; this is the only case where DENY does not win.
