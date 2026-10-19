# Phase 2C Walkthrough: Login UI (frontend)

This file grows with each 2C layer. Layer status: **2C-1 built (waiting for owner review)**, 2C-2 not started, 2C-3 (optional) not started.

## Layer 2C-1: API client, session, login page, minimal home

### 1. What we built
- A login page at `/login` that follows blueprint section 19.2 (messages, shake, Caps Lock hint, spinner).
- A small API client and a "session store" that keeps the access token in memory only.
- A simple `/home` page that shows who is signed in (name, department, roles) and a Sign out button.
- A guard: `/home` sends signed-out visitors to `/login`; `/login` sends signed-in users to `/home`.

### 2. How it works, step by step
1. You type email and password and press Enter (or click Sign in).
2. The browser checks the fields first (empty email, wrong email shape, empty password). If something is wrong: red border + icon + text, the card shakes for 400 ms, and focus moves to the first problem field.
3. If the fields look fine, `POST /api/v1/auth/login` is called. The button shows a spinner and is disabled so you cannot double-submit.
4. On success the server returns a short-lived **access token** (kept only in JavaScript memory) and sets a **refresh cookie** that JavaScript cannot read (`httpOnly`).
5. You are redirected to `/home`.
6. If you reload the page, the access token is gone, so the app calls `/auth/refresh` (the cookie is sent automatically) and gets a new one. This is how you stay signed in.
7. Sign out calls `/auth/logout`, forgets everything, and returns to `/login`.

Important rule: the server treats a refresh cookie used twice as theft. So `refreshSession()` is "single-flight": if two parts of the page ask at the same time, they share one request.

Login messages (exact wording from the blueprint):
| Situation | Message |
|---|---|
| Email empty | Please enter your email. |
| Email shape wrong | Enter a valid email address, like name@company.com. |
| Password empty | Please enter your password. |
| Wrong email or password, or deactivated account | Email or password is incorrect. |
| Too many attempts | Too many attempts. Try again in N minutes. (text comes from the server) |
| Server unreachable | Can't reach the server. Check your connection and try again. |

### 3. Important files
| File | Job |
|---|---|
| `frontend/lib/api.ts` | `fetch` wrapper: cookies on, Problem Details to `ApiError`, 15 s timeout |
| `frontend/lib/session.ts` | In-memory session store, login, logout, single-flight refresh, `authedApi()` for later phases |
| `frontend/lib/validation.ts` | Browser-side checks and the exact messages |
| `frontend/lib/validation.test.ts` | 5 unit tests for the checks |
| `frontend/app/(portal)/layout.tsx` | Groups login/home/profile so they share one session. The landing page stays outside, so visitors never call the API |
| `frontend/app/(portal)/_auth/AuthProvider.tsx` | Restores the session once; `useSession()` hook |
| `frontend/app/(portal)/_auth/RequireAuth.tsx` | Client-side guard for protected pages |
| `frontend/app/(portal)/login/` | Login page and form |
| `frontend/app/(portal)/home/` | Minimal home (expanded in 2C-2) |
| `frontend/app/globals.css` | Added the `shake` animation (design tokens unchanged) |

### 4. Tools: why we chose them
- We used **plain React + Tailwind** (same as Phase 1). We did not add shadcn/ui because three forms do not justify a new dependency.
- We used **`useSyncExternalStore`** with a tiny store instead of a state library, because the session is one small object. We did not add Redux/Zustand for that.
- We used **Vitest** (dev-only) for pure logic tests. We did not choose Playwright now because browser flows were checked by hand in the browser pane, and a full end-to-end suite fits Phase 9 (CI).
- No new runtime dependency was added. One dev dependency: `vitest@5.0.3` (needs Node 22 or newer to run tests).

### 5. How to run it
Backend must be running and seeded (see root README). Then, in PowerShell:
```powershell
cd D:\AI\RAG\Secure_Search_AI\frontend
npm install
npm run dev
```
Open http://localhost:3000/login . Stop with Ctrl+C in that terminal.
The API address defaults to `http://localhost:8000`. To change it, set `NEXT_PUBLIC_API_URL` (a public URL, not a secret).

### 6. How to test it
```powershell
cd D:\AI\RAG\Secure_Search_AI\frontend
npm test            # 5 unit tests
npm run typecheck   # TypeScript
npm run build       # production build
```

### 7. Actual results
Verified by me in the browser pane (dev server + real backend), using a temporary test user that I deleted afterwards:
- Empty submit: both errors shown, focus on email, screen-reader alert text set.
- Bad email shape: format message shown.
- Wrong credentials: generic message, password field cleared, focus back on email.
- Correct login: redirected to `/home`; name, department, roles, clearance, country shown correctly. No cookie visible to JavaScript, nothing in localStorage or sessionStorage.
- Page reload on `/home`: still signed in. Sign out: back on `/login`; opening `/home` again redirects to `/login`.
- Signed-in user opening `/login` is sent to `/home`.
- Lockout: after 5 wrong passwords the message "Too many attempts. Try again in 15 minutes." appears.
- Backend stopped: "Can't reach the server..." appears and the button is enabled again.
- 360 px width: no horizontal scroll, form usable.
- `npm test` 5 passed, `tsc` clean, `npm run build` OK.

Not verified by me (owner to check): Caps Lock hint, the browser's "Save password?" prompt, screen reader behaviour, Remember me cookie lifetime in the browser, the shake animation by eye, Lighthouse accessibility score.

### 8. Limitations and open issues
- `Forgot password?` leads to the 404 page until layer 2C-2.
- Route protection is client-side only (the access token is in memory, so the Next.js server cannot see it). Pages contain no private data; the API checks every request.
- `/home` is a plain shell: no tour, guide or profile yet (2C-2).
- Running tests needs Node 22 or newer; the app needs Node 20.9 or newer.
- See `docs/CHALLENGES.md` entries 19 to 23.
