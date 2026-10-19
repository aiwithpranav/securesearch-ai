# Phase 2B Walkthrough: Authentication backend

## 1. What we built
The server side of login. A person with an email and password gets a short "access pass" (15 minutes) and a long-lived "renewal pass" kept in a safe browser cookie. Admins can create, change and switch off accounts. Nothing visual yet: the login screens are Phase 2C.

## 2. How it works, step by step
1. **Login** (`POST /api/v1/auth/login`): the server checks the password against an Argon2id hash. Wrong email and wrong password give the **same** message, so attackers cannot learn which emails exist. After 5 wrong tries the email is locked for 15 minutes.
2. **Passes:** the access pass is a JWT (a signed text token) holding only the user id and times. It does **not** contain roles. On every request the server looks up the user's roles in the database. So a role change or a deactivation works on the very next request.
3. **Renewal** (`POST /auth/refresh`): the browser sends the cookie; the server swaps it for a new one (rotation). If an *old* cookie is sent again, someone probably copied it, so the whole session is ended.
4. **Logout / logout-all:** ends this browser or every device.
5. **Forgot password:** always answers "if that account exists, a link was sent". The email goes to Mailpit (a fake inbox) after the answer is sent. The link works once and expires. Using it signs out all devices.
6. **Admin endpoints** (`/users`, `/roles`, `/departments`): only for role `system_admin`, checked on the server from the database.

Terms: **Argon2id** = a deliberately slow password hash. **JWT** = signed token. **Rotation** = a new renewal pass every time. **Lockout** = temporary block after repeated failures.

## 3. Important files
| File | Job |
|---|---|
| `backend/app/core/security.py` | Argon2id hashing, token hashing, JWT create/verify |
| `backend/app/core/rate_limit.py`, `redis.py` | Redis counters for lockout and rate limits |
| `backend/app/core/mailer.py` | Sends reset and invite emails (SMTP to Mailpit) |
| `backend/app/core/errors.py` | Problem Details errors; never echoes passwords |
| `backend/app/models/` | Database tables (users, roles, departments, auth_tokens) |
| `backend/migrations/versions/..._auth_tables.py` | Creates the tables |
| `backend/app/services/auth_service.py` | Login, refresh, logout, reset, change password |
| `backend/app/services/user_service.py` | Admin operations |
| `backend/app/api/deps.py` | "Who is calling?" and "is an admin?" checks |
| `backend/app/api/v1/auth.py`, `users.py` | The HTTP endpoints |
| `backend/app/scripts/seed_users.py` | Creates the 8 demo users |
| `backend/tests/` | 57 tests (real Postgres, Redis, Mailpit) |
| `scripts/setup_env.ps1` | Creates `.env` with random secrets |
| `docs/adr/023-auth-implementation-details.md` | Decisions and items for owner check |

## 4. Tools: why we chose them
- We used **argon2-cffi (Argon2id)** because OWASP recommends it for passwords. We did not choose bcrypt because Argon2id resists GPU cracking better and the blueprint already fixed it.
- We used **PyJWT** for the access pass because it is small and we control the checks (fixed algorithm list). We did not choose server-side sessions for access because the blueprint (ADR-018) picked JWT, which also suits future API clients.
- We used **Redis counters** for lockout because Redis is already in the stack and expires keys by itself. We did not add a rate-limit library because the logic is about 40 lines and easy to read.
- We used **Python's built-in smtplib** for email because Mailpit accepts plain SMTP. We did not add an email library: no new dependency needed.
- One new dependency was needed: **greenlet** (SQLAlchemy's async engine requires it). See ADR 022.

## 5. How to run it
Open a terminal (PowerShell) in the repo root `D:\AI\RAG\Secure_Search_AI`, with Docker Desktop running.
```powershell
powershell -ExecutionPolicy Bypass -File scripts/setup_env.ps1   # only if .env does not exist
docker compose up --build -d
docker compose exec backend alembic upgrade head                  # creates the tables
docker compose exec backend python -m app.scripts.seed_users      # creates the demo users
```
URLs: API docs http://localhost:8000/api/docs , health http://localhost:8000/api/v1/health , Mailpit inbox http://localhost:8025 .
Stop: `docker compose down` (keeps data). `docker compose down -v` also deletes the database volume.

## 6. How to test it
```powershell
docker compose cp backend/tests/. backend:/app/tests/   # only needed after you edit tests
docker compose exec backend pytest -q
```
The tests create their own database `securesearch_test`, so your dev data is untouched.

## 7. Actual results
- Verified by me: 57 tests pass in the container; migration `0001` applies; seed creates 9 users and is safe to run twice; all 8 active demo users get HTTP 200 on login and the deactivated one gets 401; `/ready` shows postgres and redis ok.
- Mutation check: I temporarily disabled refresh-reuse detection and the lockout in the container; 3 tests failed as they should. I then restored the code and all 57 passed again.
- Not verified by me: reading the reset email in the Mailpit web page by eye, the Swagger UI, and everything in section 8 below.

## 8. Limitations and open issues
- No login screens yet (2C). Admin-initiated reset is not built (needs a Change Request, ADR 023).
- Lockout is per email, so a stranger can annoy a user for 15 minutes. Forgot password clears it.
- Access passes issued in the same second as a "sign out everywhere" can survive up to 1 second.
- Expired tokens stay in the database (purge job planned later).
- Client IP is the direct connection address; revisit behind a proxy in Phase 9.
- The Starlette `httpx` deprecation warning from 2A remains in test output.
- Tests are copied into the running container with `docker compose cp` (the image does not mount the folder).
