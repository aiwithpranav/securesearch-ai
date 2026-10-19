// Session store (no React inside, so it is easy to test and share).
//
// Where things live:
// - Access token: ONLY in this module's memory. Never localStorage, never a cookie.
//   (A page reload loses it; we get a new one from the refresh cookie.)
// - Refresh token: an httpOnly cookie set by the server. JavaScript cannot read it.
//
// Important: the server rotates the refresh cookie on every use, and treats a second
// use of the old cookie as theft. So we must NEVER call /auth/refresh twice at the same
// time. refreshSession() is "single-flight": concurrent callers share one request.
import { api, ApiError, type TokenResponse, type User } from "./api";

export type SessionState = { status: "loading" | "signed-out" | "signed-in"; user: User | null };

const SERVER_STATE: SessionState = { status: "loading", user: null };
let state: SessionState = SERVER_STATE;
let accessToken: string | null = null;
let expiresAtMs = 0;
let inflightRefresh: Promise<boolean> | null = null;
let bootstrapped = false;
const listeners = new Set<() => void>();

function setState(next: SessionState) {
  state = next;
  listeners.forEach((l) => l());
}

function applyTokens(res: TokenResponse) {
  accessToken = res.access_token;
  expiresAtMs = Date.now() + res.expires_in * 1000;
  setState({ status: "signed-in", user: res.user });
}

function clearSession() {
  accessToken = null;
  expiresAtMs = 0;
  setState({ status: "signed-out", user: null });
}

export function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}
export const getSnapshot = (): SessionState => state;
export const getServerSnapshot = (): SessionState => SERVER_STATE;

/** Ask the server for a fresh access token using the refresh cookie. Returns true if signed in. */
export function refreshSession(): Promise<boolean> {
  if (inflightRefresh) return inflightRefresh;
  inflightRefresh = (async () => {
    try {
      applyTokens(await api<TokenResponse>("/auth/refresh", { method: "POST" }));
      return true;
    } catch {
      // 401 = no valid session (normal for visitors). A network error also ends up here.
      clearSession();
      return false;
    } finally {
      inflightRefresh = null;
    }
  })();
  return inflightRefresh;
}

/** Called once when the app opens: restores the session after a page reload. */
export function bootstrapSession(): void {
  if (bootstrapped) return;
  bootstrapped = true;
  void refreshSession();
}

export async function login(email: string, password: string, rememberMe: boolean): Promise<void> {
  const res = await api<TokenResponse>("/auth/login", {
    method: "POST",
    body: { email, password, remember_me: rememberMe },
  });
  applyTokens(res);
}

export async function logout(): Promise<void> {
  try {
    await api<void>("/auth/logout", { method: "POST" });
  } catch {
    // Even if the server cannot be reached, forget everything locally.
  }
  clearSession();
}

// A one-time message for the login page ("Your password was changed...").
// It lives here, not in the URL, so it survives the automatic redirect to /login.
let pendingNotice: string | null = null;
export function takeNotice(): string | null {
  const n = pendingNotice;
  pendingNotice = null;
  return n;
}

/** Change password. The server ends ALL sessions, so we forget ours too. */
export async function changePassword(currentPassword: string, newPassword: string): Promise<void> {
  await authedApi<void>("/auth/change-password", {
    method: "POST",
    body: { current_password: currentPassword, new_password: newPassword },
  });
  pendingNotice = "password-changed";
  clearSession();
}

/** Sign out on every device (and this one). */
export async function logoutAll(): Promise<void> {
  await authedApi<void>("/auth/logout-all", { method: "POST" });
  pendingNotice = "signed-out-everywhere";
  clearSession();
}

/** Call a protected API endpoint. Refreshes the token first if it is about to expire,
 *  and retries once if the server says 401. */
export async function authedApi<T>(path: string, opts: { method?: string; body?: unknown } = {}): Promise<T> {
  if (!accessToken || Date.now() > expiresAtMs - 30_000) {
    if (!(await refreshSession())) throw new ApiError(401, "Session expired", "Please sign in again.");
  }
  try {
    return await api<T>(path, { ...opts, token: accessToken });
  } catch (e) {
    if (e instanceof ApiError && e.status === 401) {
      if (await refreshSession()) return api<T>(path, { ...opts, token: accessToken });
    }
    throw e;
  }
}
