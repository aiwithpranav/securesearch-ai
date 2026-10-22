// Admin overview, knowledge gaps and suggested questions (Phase 7C). The numbers hold no text and no names.
import { authedApi } from "./session";

export type DayCount = { day: string; searches: number; questions: number; answered: number };
export type Overview = {
  documents_by_status: Record<string, number>;
  documents_total: number;
  people_active: number;
  people_total: number;
  groups: number;
  per_day: DayCount[];
  answers: { answered: number; refused: number; unavailable: number; refusal_rate: number | null };
  refusal_reasons: Record<string, number>;
  p95_latency_ms: Record<string, number>;
  feedback: { up: number; down: number; helpful_rate: number | null };
  permission_changes_7d: number;
  failed_ingestions_7d: number;
  latest_evaluation: { started_at: string; status: string; total: number; passed: number; leak_count: number } | null;
  window_days: number;
};
export type Gap = { question: string; asked: number; people: number; last_asked: string; suggested_action: string };

export const getOverview = () => authedApi<Overview>("/dashboards/admin-overview");
export const getGaps = () => authedApi<{ window_days: number; items: Gap[] }>("/dashboards/knowledge-gaps");
export const getSuggestions = () => authedApi<{ items: string[] }>("/me/suggested-questions");

/** 0.25 becomes "25%"; a missing number (nothing to divide by yet) becomes a dash. */
export const percentText = (x: number | null | undefined): string => (x == null ? "–" : `${Math.round(x * 100)}%`);

/** 320 becomes "320 ms", 2040 becomes "2.0 s". */
export function msText(ms: number | null | undefined): string {
  if (ms == null) return "–";
  return ms < 1000 ? `${Math.round(ms)} ms` : `${(ms / 1000).toFixed(1)} s`;
}

/** Heights (0 to `max`) for a small bar chart. The tallest bar fills the space; an empty series stays flat.
 *  `scaleTo` lets a second series share the scale of the first. */
export function barHeights(values: number[], max: number, scaleTo?: number): number[] {
  const top = scaleTo ?? Math.max(0, ...values);
  return values.map((v) => (top === 0 ? 0 : Math.round((v / top) * max)));
}

/** "2026-10-22" becomes "Thu". */
export const dayLabel = (iso: string): string => new Date(`${iso}T12:00:00Z`).toLocaleDateString("en-GB", { weekday: "short", timeZone: "UTC" });

const REASONS: Record<string, string> = {
  WEAK_EVIDENCE: "Passages were too weak",
  NO_HITS: "Nothing matched at all",
  NO_ACCESSIBLE_EVIDENCE: "Nothing the person may read",
  NO_CITATION: "Model gave no source",
  INVALID_CITATION: "Model cited an unknown source",
};
/** Code words are turned into plain words; an unknown code is shown nicely rather than hidden. */
export const reasonText = (code: string): string => REASONS[code] ?? code.toLowerCase().replace(/_/g, " ").replace(/^./, (c) => c.toUpperCase());

export const sum = (values: number[]): number => values.reduce((a, b) => a + b, 0);
