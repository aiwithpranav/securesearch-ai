// Search API wrapper and the small pure helpers the search screen uses (tested in search.test.ts).
// The question text is only sent in the request body. It never goes into a URL, storage or a log.
import { ApiError } from "./api";
import { authedApi } from "./session";

export const MAX_QUERY = 500;

export type SearchHit = {
  chunk_id: string;
  document_id: string;
  document_title: string;
  page_number: number | null;
  section: string | null;
  content: string;
  score: number; // 0 to 1, reranker score (hybrid) or rank score; only for ordering and a rough bar
  scores: Record<string, number> | null; // only administrators get the details
};
export type SearchResponse = { mode: string; count: number; took_ms: number; hits: SearchHit[] };

export const searchDocuments = (query: string) =>
  authedApi<SearchResponse>("/search", { method: "POST", body: { query } });

/** Message to show under the box, or null when the question may be sent. */
export function validateQuery(raw: string): string | null {
  const q = raw.trim();
  if (!q) return "Type a question or a few words to search for.";
  if (q.length > MAX_QUERY) return `Keep it under ${MAX_QUERY} characters (now ${q.length}).`;
  return null;
}

export const scorePercent = (score: number): number => Math.round(Math.min(1, Math.max(0, score)) * 100);

export function relevanceWord(score: number): string {
  const p = scorePercent(score);
  return p >= 70 ? "Strong match" : p >= 30 ? "Possible match" : "Weak match";
}

/** Provisional "nothing really matches" level (see ADR 028); Phase 6 uses it for refusals, Phase 7 tunes it. */
export const WEAK_BELOW = 0.03;
/** True when even the best passage is a very weak match (only meaningful for scored, reranked results). */
export const allWeak = (hits: Pick<SearchHit, "score">[]): boolean => hits.length > 0 && Math.max(...hits.map((h) => h.score)) < WEAK_BELOW;

const SHORT = 320;
/** First part of a long passage, cut at a word boundary; the rest is behind "Show more". */
export function previewText(content: string, max = SHORT): { short: string; truncated: boolean } {
  if (content.length <= max) return { short: content, truncated: false };
  const cut = content.slice(0, max);
  const lastSpace = cut.lastIndexOf(" ");
  return { short: (lastSpace > max * 0.6 ? cut.slice(0, lastSpace) : cut).trimEnd() + "…", truncated: true };
}

/** "Page 3 · Alerts", or empty text when the passage has neither. Accepts search hits (page_number) and citations (page). */
export function whereText(hit: { page_number?: number | null; page?: number | null; section?: string | null }): string {
  const page = hit.page_number ?? hit.page;
  const parts = [page ? `Page ${page}` : null, hit.section?.trim() || null].filter(Boolean);
  return parts.join(" · ");
}

const DETAIL_LABELS: [string, string, (n: number) => string][] = [
  ["keyword_rank", "Keyword rank", (n) => `#${n}`],
  ["vector_rank", "Meaning rank", (n) => `#${n}`],
  ["rrf_score", "Combined score", (n) => n.toFixed(4)],
  ["rerank_score", "Reranker score", (n) => n.toFixed(3)],
];
/** Administrator details in a fixed, readable order; signals that were not computed are left out. */
export function scoreDetails(scores: Record<string, number> | null): { label: string; value: string }[] {
  if (!scores) return [];
  return DETAIL_LABELS.filter(([key]) => key in scores).map(([key, label, fmt]) => ({ label, value: fmt(scores[key]) }));
}

export function searchErrorText(e: unknown): string {
  if (e instanceof ApiError) {
    if (e.status === 429) {
      const s = e.retryAfterSeconds;
      return s ? `Too many searches. Try again in ${s} ${s === 1 ? "second" : "seconds"}.` : "Too many searches. Try again shortly.";
    }
    if (e.status === 0) return "Can't reach the server. Check your connection and try again.";
    if (e.status === 422) return e.message || "That question can't be searched. Try different words.";
  }
  return "The search could not be completed. Please try again.";
}
