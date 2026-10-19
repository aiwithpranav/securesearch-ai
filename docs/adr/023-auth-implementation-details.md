# ADR 023: Authentication implementation details (Phase 2B)

## Status
Accepted for implementation. Items marked **OWNER CHECK** need the owner's confirmation at Phase 2 sign-off.

## Context
ADR-018 fixes the approach (JWT access + rotating refresh, Argon2id, no roles in the token). It does not fix the small details a working implementation needs. This ADR records them so they are not hidden in code. Nothing here changes a frozen rule.

## Decision
- **Access token:** HS256 JWT, 15 minutes, claims `sub`, `jti`, `type`, `iat`, `exp` only. Roles, department and clearance are read from the database on every request.
- **Refresh token:** random 384-bit value in an `httpOnly`, `SameSite=Lax` cookie scoped to `/api/v1/auth` (`Secure` when `APP_ENV=production`). Only its SHA-256 hash is stored. Rotated on every use. Reuse of a used token revokes the whole session "family".
- **Remember me:** unchecked = browser-session cookie, server cap 24 h. Checked = 7 days (setting, max 30). Rotation keeps the original end time (absolute cap, not sliding).
- **Sign out everywhere / password change / deactivation:** revoke refresh tokens and set `users.auth_valid_after`; older access tokens are rejected (whole-second precision).
- **Lockout:** 5 wrong passwords per email (also for unknown emails) lock that email for 15 minutes (Redis). Plus 30 login attempts per minute per IP. Known trade-off: someone can lock a victim's login for 15 minutes; the real user can still use "Forgot password", which clears the lock.
- **Reset and invite links:** `RESET` tokens, single use, 30 min (reset) / 72 h (invite). Link format `{FRONTEND_ORIGIN}/reset-password#token=...` (the part after `#` is never sent to servers or logs). A newer link cancels older ones.
- **Password rule:** 12 to 128 characters. **OWNER CHECK:** the blueprint gives no number; 12 is a conservative choice.
- **Email check:** shape check only (`x@y`), because demo users are `swara@demo` (no `.com`).
- **Admin = role `system_admin`** (Dev). Meera (`security_admin`) and Nina (`auditor`) cannot manage users.
- **CSRF:** SameSite=Lax cookie plus an `Origin` check on the cookie endpoints (`/auth/refresh`, `/auth/logout`).

## Deviations to confirm (**OWNER CHECK**)
1. **Extra columns** beyond the blueprint sketch: `users.full_name`, `users.auth_valid_after`, `users.last_login_at`, `users.created_at/updated_at`; `auth_tokens.family_id`, `auth_tokens.remember_me`, `auth_tokens.created_at`. Additive only. The table is named `auth_tokens` (type `REFRESH` or `RESET`).
2. **`POST /users/{id}/roles`** replaces the user's whole role list (the contract does not say add or replace, and has no remove endpoint).
3. **Admin-initiated password reset (part of FR-25) is NOT built.** The frozen API contract has no endpoint for it. It needs a Change Request (suggested: `POST /users/{id}/reset-password`) or acceptance that invite + forgot-password cover it. Everything else in FR-25 is built.
4. **Persona departments:** the blueprint's persona table uses Executive / IT / Compliance, but the department seed list has 8 other names. Mapping used: Vikram to Company-wide, Dev to Engineering, Nina to Legal.
5. **FR-27 (welcome tour) and the login UI (FR-23/24)** are Phase 2C (frontend), not 2B.

## Consequences
- Frontend (2C) must keep the access token in memory only, call `/auth/refresh` with `credentials: "include"`, and refresh only once at a time (a double refresh looks like token theft and ends the session).
- Expired tokens are not purged yet (backlog: purge job with the Phase 9 retention work).
- Behind a proxy (Phase 9) client IP handling must be revisited; today the direct peer address is used.
