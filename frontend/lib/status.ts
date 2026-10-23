// The public status page (Phase 9B). It shows a name and up or down for each part of the service and one overall word.
// It needs no sign-in and holds no secret, address, version or error text (the server never sends them).
import { API_BASE } from "./api";

export type Overall = "operational" | "degraded" | "down";
export type Component = { name: string; status: "up" | "down" };
export type ServiceStatus = { status: Overall; components: Component[]; checked_at: string };

/** "unreachable" is when this page itself cannot reach the server: that is also an outage, shown honestly. */
export type View = Overall | "unreachable";

export async function fetchStatus(signal?: AbortSignal): Promise<ServiceStatus | null> {
  try {
    const res = await fetch(`${API_BASE}/status`, { cache: "no-store", signal });
    if (!res.ok) return null;
    return (await res.json()) as ServiceStatus;
  } catch {
    return null;
  }
}

export const viewOf = (s: ServiceStatus | null): View => (s ? s.status : "unreachable");

export const HEADLINE: Record<View, string> = {
  operational: "All systems operational",
  degraded: "Some features are slow or unavailable",
  down: "The service is down",
  unreachable: "We can't reach the server",
};

/** One plain sentence of what a person can expect, so the colour is never the only message. */
export const EXPLAIN: Record<View, string> = {
  operational: "Searching, answers and uploads are working.",
  degraded: "Searching and answers work. New documents may wait to be processed.",
  down: "Searching and answers are not available right now. We are on it.",
  unreachable: "Check your connection. If it is fine, the service may be down.",
};

const WHAT: Record<string, string> = {
  Database: "Where documents, people and rules are kept",
  Redis: "Rate limits and sessions",
  "File storage": "The uploaded original files",
  "Background worker": "Processes new documents and syncs sources",
};
export const componentHint = (name: string): string => WHAT[name] ?? "";

/** "just now", "12 s ago", "3 min ago". */
export function checkedText(iso: string | undefined, now: number = Date.now()): string {
  if (!iso) return "";
  const s = Math.max(0, Math.floor((now - new Date(iso).getTime()) / 1000));
  if (s < 5) return "just now";
  if (s < 60) return `${s} s ago`;
  return `${Math.floor(s / 60)} min ago`;
}
