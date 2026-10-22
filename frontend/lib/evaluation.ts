// The evaluation dashboard (Phase 7C). Ids, numbers and the synthetic questions: never answer or document text.
import { authedApi } from "./session";

export type Run = {
  id: string; label: string; model_mode: "FAKE_MODEL" | "LIVE_MODEL"; status: "RUNNING" | "DONE" | "FAILED" | string;
  started_at: string; finished_at: string | null; total: number; passed: number; leak_count: number;
  summary: { metrics?: Metrics; mode_table?: ModeRow[]; error?: string };
};
export type Metrics = {
  leakage_cases: number; recall_at_5: number | null; mrr: number | null; citation_correctness: number; refusal_accuracy: number;
  answer_rate: number; scenarios_passed: string; p95_answer_ms: number; p95_search_ms: number | null; by_category: Record<string, string>;
};
export type ModeRow = { set_up: string; recall_at_5: number; mrr: number; p95_ms: number };
export type CaseResult = { case_id: string; category: string; persona: string | null; question: string | null; passed: boolean; leaked: boolean; latency_ms: number };
export type RunDetail = Run & { results: CaseResult[] };

export const listRuns = () => authedApi<Run[]>("/evaluation/runs?limit=10");
export const getRun = (id: string) => authedApi<RunDetail>(`/evaluation/runs/${id}`);
/** Free run only (the built-in stand-in model). A real-model run costs money and is started from the command line. */
export const startFreeRun = () => authedApi<Run>("/evaluation/runs", { method: "POST", body: { live: false, label: "dashboard run" } });

export type Verdict = "RUNNING" | "LEAK" | "PASS" | "FAIL" | "ERROR";

/** One word for a run. A leak always wins over everything else. */
export function verdict(run: Pick<Run, "status" | "total" | "passed" | "leak_count">): Verdict {
  if (run.status === "RUNNING") return "RUNNING";
  if (run.status === "FAILED") return "ERROR";
  if (run.leak_count > 0) return "LEAK";
  return run.total > 0 && run.passed === run.total ? "PASS" : "FAIL";
}

export const verdictText: Record<Verdict, string> = {
  RUNNING: "Running…", LEAK: "Leak found", PASS: "All passed", FAIL: "Some cases failed", ERROR: "Could not finish",
};
export const modeText = (m: string): string => (m === "LIVE_MODEL" ? "Real model" : "Stand-in model (free)");
export const isRunning = (runs: Pick<Run, "status">[]): boolean => runs.some((r) => r.status === "RUNNING");
