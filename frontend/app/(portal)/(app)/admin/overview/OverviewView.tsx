"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { ApiError } from "@/lib/api";
import { ageText } from "@/lib/chat";
import { barHeights, dayLabel, getOverview, msText, percentText, reasonText, sum, type Overview } from "@/lib/dashboards";
import { verdict, verdictText } from "@/lib/evaluation";
import { ErrorState, TableSkeleton } from "../_components/ui";

const card = "rounded-2xl border border-line bg-surface p-5";

function Kpi({ label, value, hint }: { label: string; value: string | number; hint?: string }) {
  return (
    <div className={card}>
      <p className="text-sm text-muted">{label}</p>
      <p className="mt-1 text-3xl font-semibold tracking-tight">{value}</p>
      {hint && <p className="mt-1 text-xs text-muted">{hint}</p>}
    </div>
  );
}

/** Seven bars, one per day. The label and number are text, so colour is never the only signal. */
function DayChart({ days }: { days: Overview["per_day"] }) {
  const H = 120;
  const asked = days.map((d) => d.questions + d.searches);
  const heights = barHeights(asked, H);
  const answered = barHeights(days.map((d) => d.answered), H, Math.max(0, ...asked));
  return (
    <figure>
      <svg role="img" aria-label={`Questions and searches per day: ${days.map((d, i) => `${dayLabel(d.day)} ${asked[i]}`).join(", ")}`} viewBox="0 0 280 170" className="w-full">
        {days.map((d, i) => {
          const x = 10 + i * 38;
          return (
            <g key={d.day}>
              <rect x={x} y={140 - heights[i]} width="26" height={heights[i]} rx="4" className="fill-accent/40" />
              <rect x={x} y={140 - answered[i]} width="26" height={answered[i]} rx="4" className="fill-accent2" />
              <text x={x + 13} y={136 - heights[i]} textAnchor="middle" className="fill-muted" fontSize="10">{asked[i] || ""}</text>
              <text x={x + 13} y={158} textAnchor="middle" className="fill-muted" fontSize="10">{dayLabel(d.day)}</text>
            </g>
          );
        })}
      </svg>
      <figcaption className="mt-1 flex gap-4 text-xs text-muted">
        <span><span aria-hidden="true" className="mr-1 inline-block h-2 w-2 rounded-sm bg-accent/40" />Asked</span>
        <span><span aria-hidden="true" className="mr-1 inline-block h-2 w-2 rounded-sm bg-accent2" />Answered</span>
      </figcaption>
    </figure>
  );
}

function Bars({ items, empty }: { items: [string, number][]; empty: string }) {
  const total = sum(items.map(([, n]) => n));
  if (total === 0) return <p className="text-sm text-muted">{empty}</p>;
  return (
    <ul className="space-y-3">
      {items.map(([label, n]) => (
        <li key={label}>
          <div className="flex justify-between text-sm"><span>{label}</span><span className="text-muted">{n}</span></div>
          <div className="mt-1 h-2 rounded-full bg-surface2"><div className="h-2 rounded-full bg-accent2" style={{ width: `${(n / total) * 100}%` }} /></div>
        </li>
      ))}
    </ul>
  );
}

export function OverviewView() {
  const [data, setData] = useState<Overview | null>(null);
  const [error, setError] = useState<{ message: string; requestId?: string } | null>(null);

  const load = useCallback(async () => {
    try {
      setData(await getOverview());
      setError(null);
    } catch (e) {
      setError({ message: "The overview could not be loaded.", requestId: e instanceof ApiError ? e.requestId : undefined });
    }
  }, []);
  useEffect(() => { void load(); }, [load]);

  if (error) return <main id="main" className="mx-auto w-full max-w-6xl px-5 py-10"><ErrorState message={error.message} requestId={error.requestId} onRetry={() => void load()} /></main>;
  if (!data) return <main id="main" className="mx-auto w-full max-w-6xl px-5 py-10"><TableSkeleton rows={4} /></main>;

  const ev = data.latest_evaluation;
  const v = ev ? verdict({ status: ev.status, total: ev.total, passed: ev.passed, leak_count: ev.leak_count }) : null;
  const docs = Object.entries(data.documents_by_status);
  const nothingYet = data.documents_total === 0 && sum(data.per_day.map((d) => d.questions + d.searches)) === 0;

  return (
    <main id="main" className="mx-auto w-full max-w-6xl px-5 py-10">
      <h1 className="text-3xl font-semibold tracking-tight">Overview</h1>
      <p className="mt-2 max-w-2xl text-muted">Numbers only: no questions, no answers, no document text and no names. Last {data.window_days} days unless it says otherwise.</p>

      {nothingYet && <p className="mt-6 rounded-2xl border border-dashed border-line p-6 text-muted">Nothing here yet. Upload a document and ask a question, and the numbers will appear.</p>}

      <section aria-label="Key numbers" className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Kpi label="Documents" value={data.documents_total} hint={`${data.documents_by_status.READY ?? 0} ready`} />
        <Kpi label="People" value={data.people_active} hint={`${data.people_total} accounts, ${data.groups} groups`} />
        <Kpi label="Refusal rate" value={percentText(data.answers.refusal_rate)} hint={`${data.answers.refused} of ${data.answers.answered + data.answers.refused} questions`} />
        <Kpi label="Helpful answers" value={percentText(data.feedback.helpful_rate)} hint={`${data.feedback.up} up, ${data.feedback.down} down`} />
        <Kpi label="Answer time (P95)" value={msText(data.p95_latency_ms.CHAT)} hint="slowest 5% of questions" />
        <Kpi label="Search time (P95)" value={msText(data.p95_latency_ms.SEARCH)} hint="slowest 5% of searches" />
        <Kpi label="Permission changes" value={data.permission_changes_7d} hint="last 7 days" />
        <Kpi label="Failed uploads" value={data.failed_ingestions_7d} hint="last 7 days" />
      </section>

      <div className="mt-8 grid gap-6 lg:grid-cols-2">
        <section className={card} aria-labelledby="h-days">
          <h2 id="h-days" className="text-lg font-semibold">Last 7 days</h2>
          <div className="mt-4"><DayChart days={data.per_day} /></div>
        </section>
        <section className={card} aria-labelledby="h-docs">
          <h2 id="h-docs" className="text-lg font-semibold">Documents by status</h2>
          <div className="mt-4"><Bars items={docs} empty="No documents yet." /></div>
          <h2 className="mt-8 text-lg font-semibold">Why answers were refused</h2>
          <div className="mt-4"><Bars items={Object.entries(data.refusal_reasons).map(([k, n]): [string, number] => [reasonText(k), n])} empty="No refusals." /></div>
        </section>
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <section className={card} aria-labelledby="h-service">
          <div className="flex items-center justify-between gap-3">
            <h2 id="h-service" className="text-lg font-semibold">Service, last 24 hours</h2>
            <Link href="/status" className="text-sm text-accent2 hover:underline">Status page</Link>
          </div>
          <dl className="mt-4 grid grid-cols-3 gap-4">
            <div><dt className="text-sm text-muted">Requests</dt><dd className="mt-1 text-2xl font-semibold">{data.service_24h.requests}</dd></div>
            <div><dt className="text-sm text-muted">Server errors</dt><dd className="mt-1 text-2xl font-semibold">{data.service_24h.errors_5xx}</dd></div>
            <div><dt className="text-sm text-muted">Too many requests</dt><dd className="mt-1 text-2xl font-semibold">{data.service_24h.rate_limited}</dd></div>
          </dl>
        </section>
        <section className={card} aria-labelledby="h-retention">
          <h2 id="h-retention" className="text-lg font-semibold">Audit retention</h2>
          <p className="mt-4 text-muted">
            {data.audit_retention.days === 0 ? "Audit records are kept forever." : `Audit records are kept for ${data.audit_retention.days} days, then removed every night.`}
          </p>
          {data.audit_retention.days !== 0 && <p className="mt-2 text-sm text-muted"><b className="text-text">{data.audit_retention.records_due}</b> records are past that and will be removed tonight.</p>}
        </section>
      </div>

      <section className={`${card} mt-6 flex flex-wrap items-center justify-between gap-4`} aria-labelledby="h-eval">
        <div>
          <h2 id="h-eval" className="text-lg font-semibold">Latest evaluation</h2>
          {ev && v ? (
            <p className="mt-1 text-muted">
              <b className={v === "PASS" ? "text-ok" : "text-bad"}>{verdictText[v]}</b> · {ev.passed}/{ev.total} cases · {ev.leak_count} leaks · {ageText(ev.started_at)}
            </p>
          ) : <p className="mt-1 text-muted">No evaluation has been run yet.</p>}
        </div>
        <Link href="/admin/evaluation" className="rounded-lg border border-line px-5 py-2 hover:border-accent2">Open evaluation</Link>
      </section>
    </main>
  );
}
