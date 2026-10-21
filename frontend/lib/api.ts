// Small fetch wrapper for the SecureSearch API.
// - Sends cookies (credentials: "include") so the httpOnly refresh cookie travels.
// - Turns Problem Details errors (and network failures) into one ApiError type.
// NEXT_PUBLIC_API_URL is a public setting (a URL), not a secret.
export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const API_BASE = `${API_URL}/api/v1`;

export type Department = { id: number; name: string };

export type User = {
  id: string;
  email: string;
  full_name: string;
  department: Department;
  clearance_level: number;
  country: string;
  employment_type: string;
  roles: string[];
  is_active: boolean;
  last_login_at: string | null;
};

export type TokenResponse = {
  access_token: string;
  token_type: "bearer";
  expires_in: number; // seconds
  user: User;
};

export class ApiError extends Error {
  status: number; // 0 means the server could not be reached
  title: string;
  requestId?: string;
  retryAfterSeconds?: number;
  errorCode?: string; // fixed code from the server, for example "TOO_LARGE" (upload errors)
  existingDocumentId?: string; // set on "already uploaded" (409)

  constructor(
    status: number,
    title: string,
    detail: string,
    requestId?: string,
    retryAfterSeconds?: number,
    extra: { errorCode?: string; existingDocumentId?: string } = {},
  ) {
    super(detail);
    this.status = status;
    this.title = title;
    this.requestId = requestId;
    this.retryAfterSeconds = retryAfterSeconds;
    this.errorCode = extra.errorCode;
    this.existingDocumentId = extra.existingDocumentId;
  }

  get isNetworkError(): boolean {
    return this.status === 0;
  }
}

type Options = { method?: string; body?: unknown; token?: string | null };

export async function api<T>(path: string, { method = "GET", body, token }: Options = {}): Promise<T> {
  const headers: Record<string, string> = {};
  const isForm = typeof FormData !== "undefined" && body instanceof FormData;
  // For a file upload the browser sets the Content-Type itself (it must include the multipart boundary).
  if (body !== undefined && !isForm) headers["Content-Type"] = "application/json";
  if (token) headers["Authorization"] = `Bearer ${token}`;

  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : isForm ? (body as FormData) : JSON.stringify(body),
      credentials: "include",
      // A hung server must not leave a button disabled forever. Uploads of big files get more time.
      signal: AbortSignal.timeout(isForm ? 180_000 : 15_000),
    });
  } catch {
    throw new ApiError(0, "Network error", "Can't reach the server. Check your connection and try again.");
  }

  if (res.status === 204) return undefined as T;

  let data: unknown = null;
  try {
    data = await res.json();
  } catch {
    // body was empty or not JSON
  }

  if (!res.ok) throw errorFromProblem(res.status, data);
  return data as T;
}

/** Turns a Problem Details body into an ApiError (shared by the JSON helper and the streaming helper). */
export function errorFromProblem(status: number, data: unknown): ApiError {
  const p = (data ?? {}) as {
    title?: string; detail?: unknown; request_id?: string; retry_after_seconds?: number;
    error_code?: string; existing_document_id?: string;
  };
  return new ApiError(
    status,
    p.title ?? "Request failed",
    typeof p.detail === "string" ? p.detail : "Something went wrong. Please try again.",
    p.request_id,
    p.retry_after_seconds,
    { errorCode: p.error_code, existingDocumentId: p.existing_document_id },
  );
}

export { API_BASE };
