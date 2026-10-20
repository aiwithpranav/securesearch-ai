# CR-003: Add three read endpoints for groups, rule history and access preview

Follows the blueprint Change Request process (section 2). Status: **Treated as approved on 2026-10-20**: the Phase 4 plan listed it as decision 4 and the owner answered "Approve". The owner can reverse it.

## 1. What must change and why
The frozen API contract (section 10.4) lists groups (`GET/POST /groups`, `POST/DELETE /groups/{id}/members`) and rules (`GET/POST /documents/{id}/acl`, `PATCH/DELETE /documents/{id}/acl/{acl_id}`), but nothing to:
- see WHO is in a group (without it an administrator cannot review membership),
- read the history of rule changes that `permission_change_events` records (blueprint 10.1), or
- understand an access decision ("why can or can't this person read this document?").

## 2. What it touches
Only the API contract, by adding. Nothing existing is edited. (Separately, `PATCH /documents/{id}` now needs MANAGE on the document instead of the admin role; this follows blueprint 9.4 and decision 1 of the Phase 4 plan.)

## 3. Additive solution
- `GET /api/v1/groups/{id}`: the group and its members (system_admin only).
- `GET /api/v1/documents/{id}/acl/history`: the rule changes of one document, newest first, with the full rule list before and after, who and when (needs MANAGE on the document).
- `GET /api/v1/documents/{id}/access-preview?user_id=`: whether that user can READ, DOWNLOAD and MANAGE the document, a stable reason code for each answer, and the live rules that match (needs MANAGE on the document).

Security: none of them returns document text. A caller without MANAGE gets the same 404 "Document not found" as for a missing document, so existence is not revealed. The preview shows user attributes (role, department, clearance, country); it is available only to people who already manage the document.

## 4. Decision
Add the three endpoints (implemented in Phase 4B).

## 5. Consequences
The contract grows by three routes. No existing client is affected, except that a non-admin who merely holds MANAGE on a document can now edit that document's metadata.
