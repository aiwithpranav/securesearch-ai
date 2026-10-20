# CR-002: Add two notification endpoints to the API contract

Follows the blueprint Change Request process (section 2). Status: **Treated as approved on 2026-10-20**: the 3B plan listed it as decision 4 and the owner answered "Merged ... keep working the same way". The owner can reverse it.

## 1. What must change and why
Requirement FR-33 says admins get in-app notifications when ingestion fails. The data model has a `notifications` table ("Notifications power failed-ingestion alerts"), but the frozen API contract (section 10.4) lists no endpoint to read or acknowledge them, so the alerts could never be shown.

## 2. What it touches
Only the API contract, by adding. Nothing existing is edited.

## 3. Additive solution
- `GET /api/v1/notifications` (signed in): the caller's own notifications, newest first. Query: `limit` (1 to 100), `unread_only`.
- `POST /api/v1/notifications/{id}/read` (signed in): marks one of the caller's own notifications as read. Someone else's notification answers 404.

Security: both need a valid token; a person can only see and change their own rows; payloads contain IDs and a fixed error code, never document text.

## 4. Decision
Add the two endpoints (implemented in Phase 3B). The UI that shows them arrives in 3C.

## 5. Consequences
The contract grows by two routes. No existing client is affected.
