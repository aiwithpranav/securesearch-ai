// Answers, citations, evidence preview, feedback and history (Phase 6C). Pure helpers are tested in chat.test.ts.
// The question is only sent in a request body. It is never put in a web address, storage or a log.
import { ApiError } from "./api";
import { authedApi, authedFetch } from "./session";

export type Citation = {
  source_id: string;
  chunk_id: string;
  document_id: string;
  document_title: string;
  section: string | null;
  page: number | null;
  snippet: string;
  document_updated_at: string | null;
};
export type ChatStatus = "ANSWERED" | "REFUSED_NO_ACCESS_EVIDENCE" | "REFUSED_LOW_CONFIDENCE";
export type ChatResult = {
  status: ChatStatus;
  answer: string | null;
  refusal: string | null;
  citations: Citation[];
  request_id: string | null;
  history_id: string | null;
};
export type Stage = { id: string; label: string; status: "running" | "done"; elapsed_ms: number };
export type Passage = {
  chunk_id: string;
  document_id: string;
  document_title: string;
  section: string | null;
  page: number | null;
  content: string;
  document_updated_at: string | null;
};
export type HistoryItem = { id: string; question: string; status: ChatStatus; citation_count: number; rating: "UP" | "DOWN" | null; created_at: string };
export type HistoryPage = { items: HistoryItem[]; total: number; limit: number; offset: number };

export type SseEvent = { event: string; data: unknown };

/** Splits received text into complete events and the unfinished rest (events end with a blank line). */
export function parseSse(buffer: string): { events: SseEvent[]; rest: string } {
  const parts = buffer.split("\n\n");
  const rest = parts.pop() ?? "";
  const events: SseEvent[] = [];
  for (const block of parts) {
    let event = "message";
    const data: string[] = [];
    for (const line of block.split("\n")) {
      if (line.startsWith("event:")) event = line.slice(6).trim();
      else if (line.startsWith("data:")) data.push(line.slice(5).trim());
    }
    if (data.length === 0) continue;
    try {
      events.push({ event, data: JSON.parse(data.join("\n")) });
    } catch {
      /* ignore a damaged message */
    }
  }
  return { events, rest };
}

/** Asks a question and follows the progress. Resolves with the final result; rejects with an ApiError. */
export async function streamAnswer(question: string, onStage: (s: Stage) => void, signal?: AbortSignal): Promise<ChatResult> {
  const res = await authedFetch("/chat/stream", { method: "POST", body: { question }, signal });
  if (!res.body) throw new ApiError(0, "Network error", "Can't reach the server. Check your connection and try again.");
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let result: ChatResult | null = null;
  for (;;) {
    const { value, done } = await reader.read();
    if (value) buffer += decoder.decode(value, { stream: true });
    const parsed = parseSse(done ? buffer + "\n\n" : buffer);
    buffer = parsed.rest;
    for (const ev of parsed.events) {
      if (ev.event === "stage") onStage(ev.data as Stage);
      else if (ev.event === "result") result = ev.data as ChatResult;
      else if (ev.event === "error") {
        const d = ev.data as { status?: number; title?: string; detail?: string };
        throw new ApiError(d.status ?? 500, d.title ?? "Request failed", d.detail ?? "The answer could not be completed.");
      }
    }
    if (done) break;
  }
  if (!result) throw new ApiError(0, "Network error", "The connection was lost before the answer arrived. Please try again.");
  return result;
}

export const getPassage = (chunkId: string) => authedApi<Passage>(`/chunks/${chunkId}/preview`);
export const sendFeedback = (historyId: string, rating: "UP" | "DOWN", comment?: string) =>
  authedApi<{ history_id: string; rating: "UP" | "DOWN" }>("/chat/feedback", {
    method: "POST", body: { history_id: historyId, rating, comment: comment?.trim() || undefined },
  });
export const listHistory = (limit = 10) => authedApi<HistoryPage>(`/me/search-history?limit=${limit}`);
export const deleteHistoryItem = (id: string) => authedApi<void>(`/me/search-history/${id}`, { method: "DELETE" });

export type AnswerPart = { kind: "text"; value: string } | { kind: "cite"; id: string };

/** Splits an answer at its [S1] markers so the screen can show them as small badges (and keeps unknown markers as text). */
export function splitAnswer(answer: string, known: string[]): AnswerPart[] {
  const parts: AnswerPart[] = [];
  let last = 0;
  for (const m of answer.matchAll(/\[(S\d+)\]/g)) {
    if (!known.includes(m[1])) continue;
    if (m.index! > last) parts.push({ kind: "text", value: answer.slice(last, m.index) });
    parts.push({ kind: "cite", id: m[1] });
    last = m.index! + m[0].length;
  }
  if (last < answer.length) parts.push({ kind: "text", value: answer.slice(last) });
  return parts.length ? parts : [{ kind: "text", value: answer }];
}

export const UNAVAILABLE_TEXT = "Answers are not available right now. You can still search.";

export function chatErrorText(e: unknown): string {
  if (e instanceof ApiError) {
    if (e.status === 429) {
      const s = e.retryAfterSeconds;
      return s ? `Too many questions. Try again in ${s} ${s === 1 ? "second" : "seconds"}.` : "Too many questions. Try again shortly.";
    }
    if (e.status === 503) return UNAVAILABLE_TEXT;
    if (e.status === 0) return "Can't reach the server. Check your connection and try again.";
    if (e.status === 422) return e.message || "That question can't be answered. Try different words.";
  }
  return "The answer could not be completed. Please try again.";
}

/** True when the failure is "answers are off" (no key or the provider is down), so the screen can offer plain search. */
export const answersUnavailable = (e: unknown): boolean => e instanceof ApiError && e.status === 503;

export function statusText(status: ChatStatus): string {
  return status === "ANSWERED" ? "Answered" : "No answer";
}

/** "just now", "5 min ago", "3 h ago", "2 days ago", then the date. */
export function ageText(iso: string, now: number = Date.now()): string {
  const diff = Math.max(0, now - new Date(iso).getTime());
  const min = Math.floor(diff / 60_000);
  if (min < 1) return "just now";
  if (min < 60) return `${min} min ago`;
  const h = Math.floor(min / 60);
  if (h < 24) return `${h} h ago`;
  const d = Math.floor(h / 24);
  if (d < 7) return `${d} ${d === 1 ? "day" : "days"} ago`;
  return new Date(iso).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });
}
