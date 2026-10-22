// The audit trail screens (Phase 7C): filters, pages, security events and the CSV export. For security_admin and auditor only.
import { ApiError } from "./api";
import { authedApi, authedFetch } from "./session";

export type Person = { id: string; full_name: string | null; email: string | null };
export type QueryRow = {
  id: string; created_at: string; user: Person; kind: "SEARCH" | "CHAT"; query_text: string; filters: Record<string, unknown>;
  allowed_doc_count: number; retrieved_chunk_ids: string[]; response_status: string; latency_ms: number; request_id: string | null;
};
export type EventRow = { id: string; created_at: string; event: string; actor: Person | null; subject: Person | null; detail: Record<string, unknown>; request_id: string | null };
export type Page<T> = { items: T[]; total: number; limit: number; offset: number };
export type QueryFilters = { kind?: string; status?: string; q?: string; since?: string; until?: string };

export const PAGE_SIZE = 25;

/** Builds "?a=1&b=2" from the filters that are filled in. Empty ones are left out. */
export function queryString(params: Record<string, string | number | undefined | null>): string {
  const sp = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) if (v !== undefined && v !== null && String(v).trim() !== "") sp.set(k, String(v).trim());
  const s = sp.toString();
  return s ? `?${s}` : "";
}

/** A date typed as "2026-10-22" becomes the start of that day (UTC); an "until" date includes the whole day. */
export const dayStart = (d: string): string | undefined => (d ? `${d}T00:00:00Z` : undefined);
export const dayEndExclusive = (d: string): string | undefined => {
  if (!d) return undefined;
  const next = new Date(`${d}T00:00:00Z`);
  next.setUTCDate(next.getUTCDate() + 1);
  return next.toISOString();
};

const filterParams = (f: QueryFilters) => ({ kind: f.kind, status: f.status, q: f.q, since: f.since, until: f.until });

export const listQueries = (f: QueryFilters, offset: number) =>
  authedApi<Page<QueryRow>>(`/audit/queries${queryString({ ...filterParams(f), limit: PAGE_SIZE, offset })}`);
export const listEvents = (event: string, offset: number) =>
  authedApi<Page<EventRow>>(`/audit/access-events${queryString({ event, limit: PAGE_SIZE, offset })}`);

/** Downloads the CSV through the signed-in request (the token is never put in a web address). */
export async function downloadQueryCsv(f: QueryFilters): Promise<void> {
  const res = await authedFetch(`/audit/export${queryString(filterParams(f))}`, { method: "GET" });
  const blob = await res.blob();
  if (typeof document === "undefined") throw new ApiError(0, "Not available", "Download is not available here.");
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "query-audit.csv";
  a.click();
  URL.revokeObjectURL(url);
}

const STATUS_TEXT: Record<string, string> = {
  OK: "Results", NO_RESULTS: "No results", ANSWERED: "Answered", UNAVAILABLE: "Unavailable",
  REFUSED_LOW_CONFIDENCE: "Refused: weak evidence", REFUSED_NO_ACCESS_EVIDENCE: "Refused: nothing readable",
};
export const statusLabel = (s: string): string => STATUS_TEXT[s] ?? s;

/** "Name" or, when the account no longer exists, a short id. Never blank. */
export const personLabel = (p: Person | null | undefined): string => (!p ? "–" : p.full_name || p.email || `Former user (${p.id.slice(0, 8)})`);

export const pageRange = (offset: number, shown: number, total: number): string =>
  total === 0 ? "No records" : `${offset + 1}–${offset + shown} of ${total}`;
