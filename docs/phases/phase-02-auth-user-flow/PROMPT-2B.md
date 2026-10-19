# Phase 2B prompt (summary of the approved mission)

Mission: Phase 2, layer 2B, the authentication BACKEND of SecureSearch AI. Backend only; the login UI is 2C.

Source of truth: Pre-Code Blueprint v1.2 FINAL (frozen). Requirements: FR-02, FR-03, FR-04 (basic), FR-25, FR-26, FR-35, NFR-02, NFR-03 (login), NFR-06.

Build: users/roles/departments/tokens tables (Alembic), login, refresh rotation with reuse detection, logout, logout-all, forgot/reset/change password with Mailpit emails, `/auth/me`, admin endpoints for users/roles/departments, seed of the 8 demo users, tests (including negative authorization tests).

Exclude: frontend, documents, groups, ACL, admin-initiated reset (not in the frozen API; see ADR 023).

Rules: no secrets in Git; synthetic data only; deny by default; server decides; no roles in tokens; work on branch `feat/auth-backend`; do not push unfinished work; owner approves before merge and tag.
