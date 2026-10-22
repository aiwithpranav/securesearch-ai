"use client";

import { useCallback, useEffect, useState } from "react";
import { ApiError } from "@/lib/api";
import { ageText } from "@/lib/chat";
import { msText, percentText } from "@/lib/dashboards";
import { getRun, isRunning, listRuns, modeText, startFreeRun, verdict, verdictText, type Run, type RunDetail } from "@/lib/evaluation";
import { usePolling } from "@/lib/usePolling";
import { EmptyState, ErrorState, TableSkeleton } from "../_components/ui";

const card = "rounded-2xl border border-line bg-surface p-5";

function VerdictBadge({ run }: { run: Run }) {
  const v = verdict(run);
  const style = v === "PASS" ? "border-ok/60 text-ok" : v === "RUNNING" ? "border-accent2/60 text-accent2" : "border-bad/60 text-bad";
  return <span className={`inline-flex rounded-full border px-2.5 py-0.5 text-xs font-medium ${style}`}>{verdictText[v]}</span>;
}

function Metric({ label, value }: { label: string; value: string }) {
  return <div><dt className="text-sm text-muted">{label}</dt><dd className="mt-1 text-2xl font-semibold">{value}</dd></div>;
}

function Detail({ run }: { run: RunDetail }) {
  const m = run.summary.metrics;
  const failed = run.results.filter((r) => !r.passed);
  return (
    <div className="mt-6 space-y-6">
      {m && (
        <dl className={`${card} grid grid-cols-2 gap-6 lg:grid-cols-4`}>
          <Metric label="Leaks" value={String(m.leakage_cases)} />
          <Metric label="Recall@5" value={percentText(m.recall_at_5)} />
          <Metric label="Right sources cited" value={percentText(m.citation_correctness)} />
          <Metric label="Right refusals" value={percentText(m.refusal_accuracy)} />
          <Metric label="Scenarios passed" value={m.scenarios_passed} />
          <Metric label="Answer rate" value={percentText(m.answer_rate)} />
          <Metric label="Search time (P95)" value={msText(m.p95_search_ms)} />
          <Metric label="Answer time (P95)" value={msText(m.p95_answer_ms)} />
        </dl>
      )}
      {run.summary.mode_table && run.summary.mode_table.length > 0 && (
        <section className={`${card} overflow-x-auto`} aria-labelledby="h-modes">
          <h3 id="h-modes" className="text-lg font-semibold">Which search set-up works best</h3>
          <table className="mt-4 w-full min-w-[420px] text-left text-sm">
            <thead className="text-muted"><tr><th scope="col" className="py-2 font-medium">Set-up</th><th scope="col" className="py-2 font-medium">Recall@5</th><th scope="col" className="py-2 font-medium">MRR</th><th scope="col" className="py-2 font-medium">P95</th></tr></thead>
            <tbody>
              {run.summary.mode_table.map((r) => (
                <tr key={r.set_up} className="border-t border-line"><td className="py-2">{r.set_up}</td><td>{percentText(r.recall_at_5)}</td><td>{r.mrr.toFixed(2)}</td><td>{msText(r.p95_ms)}</td></tr>
              ))}
            </tbody>
          </table>
        </section>
      )}
      <section className={card} aria-labelledby="h-cases">
        <h3 id="h-cases" className="text-lg font-semibold">Cases ({run.passed} of {run.total} passed)</h3>
        {failed.length === 0 ? <p className="mt-2 text-sm text-ok">Every case passed.</p> : (
          <ul className="mt-3 space-y-2 text-sm">
            {failed.map((r) => <li key={r.case_id} className="rounded-lg border border-bad/60 p-3"><b>{r.case_id}</b> · {r.category}{r.leaked && <b className="ml-2 text-bad">LEAK</b>}{r.question && <p className="mt-1 text-muted">{r.question}</p>}</li>)}
          </ul>
        )}
        <details className="mt-4">
          <summary className="cursor-pointer text-accent2">Show all {run.results.length} cases</summary>
          <ul className="mt-3 grid gap-x-6 gap-y-1 text-sm sm:grid-cols-2">
            {run.results.map((r) => (
              <li key={r.case_id} className="flex justify-between gap-3 border-b border-line py-1">
                <span><b>{r.case_id}</b> <span className="text-muted">{r.category.toLowerCase()}</span></span>
                <span className={r.passed ? "text-ok" : "text-bad"}>{r.passed ? "Passed" : "Failed"}</span>
              </li>
            ))}
          </ul>
        </details>
      </section>
    </div>
  );
}

export function EvaluationView() {
  const [runs, setRuns] = useState<Run[] | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [detail, setDetail] = useState<RunDetail | null>(null);
  const [error, setError] = useState<{ message: string; requestId?: string } | null>(null);
  const [starting, setStarting] = useState(false);
  const [startError, setStartError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const r = await listRuns();
      setRuns(r);
      setError(null);
      setSelected((s) => s ?? r.find((x) => x.status !== "RUNNING")?.id ?? null);
    } catch (e) {
      setError({ message: "The evaluation runs could not be loaded.", requestId: e instanceof ApiError ? e.requestId : undefined });
    }
  }, []);
  useEffect(() => { void load(); }, [load]);
  usePolling(load, 4000, runs !== null && isRunning(runs));

  const selectedStatus = runs?.find((r) => r.id === selected)?.status;
  useEffect(() => {
    if (!selected || selectedStatus === "RUNNING") { setDetail(null); return; }
    let live = true;
    getRun(selected).then((d) => { if (live) setDetail(d); }).catch(() => { if (live) setDetail(null); });
    return () => { live = false; };
  }, [selected, selectedStatus]);

  async function start() {
    setStarting(true);
    setStartError(null);
    try {
      await startFreeRun();
      setSelected(null);
      await load();
    } catch (e) {
      setStartError(e instanceof ApiError && e.status === 409 ? "An evaluation is already running. Wait for it to finish." : "The evaluation could not be started.");
    } finally {
      setStarting(false);
    }
  }

  const running = runs ? isRunning(runs) : false;

  return (
    <main id="main" className="mx-auto w-full max-w-6xl px-5 py-10">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight">Evaluation</h1>
          <p className="mt-2 max-w-2xl text-muted">62 test questions asked as different people. The most important number is leaks: it must always be 0. A free run uses a built-in stand-in model; a real-model run costs money and is started from the command line.</p>
        </div>
        <button type="button" onClick={start} disabled={starting || running} className="rounded-lg bg-accent px-5 py-3 font-medium text-bg hover:bg-accent2 disabled:opacity-60">
          {running ? "Running…" : starting ? "Starting…" : "Run evaluation (free)"}
        </button>
      </div>
      {startError && <p role="alert" className="mt-3 text-sm text-bad">{startError}</p>}
      {running && <p role="status" className="mt-3 text-sm text-muted">The evaluation is running. This takes about three minutes; this page updates by itself.</p>}

      <div className="mt-8">
        {error ? <ErrorState message={error.message} requestId={error.requestId} onRetry={() => void load()} />
          : !runs ? <TableSkeleton rows={3} />
          : runs.length === 0 ? <EmptyState title="No runs yet" text="Press Run evaluation to check that nobody can see what they should not." />
          : (
            <>
              <div className="overflow-x-auto rounded-2xl border border-line">
                <table className="w-full min-w-[560px] text-left text-sm">
                  <thead className="bg-surface text-muted"><tr>{["Started", "Model", "Result", "Passed", "Leaks", ""].map((h) => <th key={h} scope="col" className="px-4 py-3 font-medium">{h}</th>)}</tr></thead>
                  <tbody>
                    {runs.map((r) => (
                      <tr key={r.id} className={`border-t border-line ${r.id === selected ? "bg-surface2/60" : ""}`}>
                        <td className="whitespace-nowrap px-4 py-3">{ageText(r.started_at)}</td>
                        <td className="px-4 py-3">{modeText(r.model_mode)}</td>
                        <td className="px-4 py-3"><VerdictBadge run={r} /></td>
                        <td className="px-4 py-3">{r.status === "RUNNING" ? "–" : `${r.passed}/${r.total}`}</td>
                        <td className="px-4 py-3">{r.status === "RUNNING" ? "–" : r.leak_count}</td>
                        <td className="px-4 py-3">{r.status !== "RUNNING" && <button type="button" aria-pressed={r.id === selected} onClick={() => setSelected(r.id)} className="text-accent2 hover:underline">{r.id === selected ? "Shown below" : "Show details"}</button>}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {detail && <Detail run={detail} />}
            </>
          )}
      </div>
    </main>
  );
}
