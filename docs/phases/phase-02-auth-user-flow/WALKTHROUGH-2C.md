# Phase 2C Walkthrough: Login UI (frontend)

This file grows with each 2C layer. Layer status: **2C-1 built and pushed**, **2C-2 built (waiting for owner review)**, 2C-3 (optional) not started.

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
- (Fixed in 2C-2) `Forgot password?` used to lead to the 404 page.
- Route protection is client-side only (the access token is in memory, so the Next.js server cannot see it). Pages contain no private data; the API checks every request.
- `/home` is a plain shell: no tour, guide or profile yet (2C-2).
- Running tests needs Node 22 or newer; the app needs Node 20.9 or newer.
- See `docs/CHALLENGES.md` entries 19 to 23.

## Layer 2C-2: forgot/reset, profile, welcome tour, first-2-minutes guide

### 1. What we built
- `/forgot-password`: enter your email, always get the same answer ("If that account exists, a reset link has been sent").
- `/reset-password`: opened from the email link; set a new password (12 to 128 characters, typed twice, Show/Hide).
- `/profile`: your details, **Change password**, and **Sign out of all devices** (with a confirm step).
- A shared header (Home, Profile, Sign out) for every signed-in page.
- **Welcome tour**: 3 steps (ask, check sources, rate), skippable, opens once on first sign-in; a "Take the tour again" button on Home.
- **First-2-minutes guide** on Home: employee steps for everyone, administrator steps for `system_admin`. Steps that need later phases are labelled "Coming in Phase N" (nothing is faked).
- The login page now shows a green notice after a password reset, a password change, or sign out everywhere.

### 2. How it works, step by step
1. **Forgot:** the page calls `POST /auth/forgot-password`. The server sends the email to Mailpit (a fake inbox) after answering, so the answer never reveals whether the account exists.
2. **Reset link:** it looks like `/reset-password#token=...`. The part after `#` is never sent to any server. The page reads the token, **removes it from the address bar**, and sends it with the new password to `POST /auth/reset-password`. A token works once and expires in 30 minutes. A used, expired or missing token shows "This link is invalid or has expired."
3. After a reset the server ends all sessions; this browser forgets its own session too.
4. **Change password:** needs the current password (a wrong one shows an error on that field; the server rate-limits repeated wrong tries). On success every session ends and you sign in again.
5. **Sign out of all devices:** asks once ("Sign out everywhere, including here?"), then ends every session.
6. **Tour:** the "seen" flag is stored in this browser's `localStorage` per user id (the server has no field for it and the API contract is frozen). On another browser or device the tour shows once again. Esc, Skip and Done all count as "seen".

### 3. Important files
| File | Job |
|---|---|
| `frontend/lib/authApi.ts` | Public calls: forgot and reset password |
| `frontend/lib/session.ts` | Added `changePassword`, `logoutAll`, one-time login notice |
| `frontend/lib/tour.ts` | "Tour seen" flag in localStorage (never breaks if storage is blocked) |
| `frontend/lib/validation.ts` | New-password rules, confirm check, `tokenFromHash`, notice texts |
| `frontend/app/(portal)/_auth/ui.tsx` | Shared form pieces: fields with Show/Hide, error and notice boxes, spinner |
| `frontend/app/(portal)/forgot-password/`, `reset-password/` | The two public pages |
| `frontend/app/(portal)/(app)/layout.tsx` | Guard + header + tour for all signed-in pages |
| `frontend/app/(portal)/(app)/home/`, `profile/` | Home with guide, Profile and security |
| `frontend/app/(portal)/(app)/WelcomeTour.tsx` | Native `<dialog>` tour |

### 4. Tools: why we chose them
- We used the browser's native **`<dialog>`** for the tour because it already traps focus and closes with Esc. We did not reuse the animated Phase 1 dialog: it needed extra code to avoid a stuck backdrop, and the tour does not need animation.
- We used **`localStorage`** for the tour flag because the API contract is frozen. We did not ask for a new server field (that would need a Change Request).
- No new dependencies in this layer.

### 5. How to run it
Same as 2C-1: backend running and seeded, then `npm run dev` in `frontend/`, open http://localhost:3000. Keep the frontend on port 3000: the backend only accepts that exact address.
To get a reset email: open http://localhost:3000/forgot-password, enter a demo email such as `aisha@demo`, then open Mailpit at http://localhost:8025 and click the link in the email.

### 6. How to test it
```powershell
cd D:\AI\RAG\Secure_Search_AI\frontend
npm test            # 10 unit tests
npm run typecheck
npm run build
```
The backend rules for reset, change password and logout-all are covered by the 57 backend tests from 2B.

### 7. Actual results
Verified by me in the browser pane against the live backend, with two temporary test users that I deleted afterwards:
- Forgot password: empty and valid submit; the "Check your email" screen; the email reached Mailpit.
- Reset page: no token shows "Link not valid"; a valid link shows the form and the token is removed from the address; too-short password, mismatched passwords, then success; "Go to sign in" shows the green notice; login with the new password works.
- First sign-in opened the tour automatically; Next, Back and Done work; the flag is saved per user; a reload does not reopen it.
- The employee guide is shown to everyone, the administrator guide only for `system_admin`.
- Profile: a wrong current password shows the error on that field; a correct change signs out and shows the notice on `/login`.
- Sign out of all devices: confirm step, then signed out with the notice; opening `/home` afterwards goes to `/login`.
- 360 px width: forgot and reset pages have no horizontal scroll.
- `npm test` 10 passed, `tsc` clean, `npm run build` OK.

Not verified by me (owner to check): Esc closing the tour, keyboard-only use of every page, screen reader output, the browser's "Save password?" / "Update password?" prompts on the reset and change forms, the profile page at 360 px, using the same reset link a second time in the browser (the backend tests cover it).

### 8. Limitations and open issues
- The tour shows again on a new browser or device (localStorage only).
- Admin-initiated password reset is still not built (needs a Change Request; ADR 023).
- Guide steps for search, documents and access rules are labelled "Coming in Phase N".
- Route protection is client-side only (see 2C-1).
- See `docs/CHALLENGES.md` entries 24 to 29.
