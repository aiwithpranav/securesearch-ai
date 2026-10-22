"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { ApiError, type Department } from "@/lib/api";
import { ageText } from "@/lib/chat";
import { DOCUMENT_TYPES, listDepartments, SENSITIVITY_LEVELS } from "@/lib/documents";
import {
  codeText, countsText, createSource, githubSourceBody, intervalText, INTERVALS, isRunning, listRuns, listSources, runSource, runVerdict,
  sourceLink, updateSource, validateGithubForm, verdictLabel, type GithubForm, type SyncRun, type SyncSource,
} from "@/lib/sync";
import { usePolling } from "@/lib/usePolling";
import { FieldError, FormErrorBox } from "../../../_auth/ui";
import { EmptyState, ErrorState, selectClass, TableSkeleton } from "../_components/ui";

const card = "rounded-2xl border border-line bg-surface p-6";
const inputClass = "w-full rounded-lg border border-line bg-surface2 px-4 py-3 text-text";
const EMPTY: GithubForm = { name: "", repo: "", branch: "main", path: "demo-docs", departmentId: "", documentType: "POLICY", sensitivity: "1", interval: "15", mirror: true };

function VerdictBadge({ run }: { run: SyncRun }) {
  const v = runVerdict(run);
  const style = v === "OK" ? "border-ok/60 text-ok" : v === "RUNNING" ? "border-accent2/60 text-accent2" : "border-bad/60 text-bad";
  return <span className={`inline-flex rounded-full border px-2.5 py-0.5 text-xs font-medium ${style}`}>{verdictLabel[v]}</span>;
}

function RunDetails({ run }: { run: SyncRun }) {
  return (
    <div className="text-sm">
      <p className="text-muted">{run.status === "RUNNING" ? "Running…" : countsText(run.counts)}</p>
      {run.error_code && <p className="mt-1 text-bad">{codeText(run.error_code)}</p>}
      {run.errors.length > 0 && (
        <ul className="mt-1 space-y-0.5 text-bad">
          {run.errors.map((e, i) => <li key={`${e.item}-${i}`} className="break-words"><span className="font-mono text-xs">{e.item}</span>: {codeText(e.code)}</li>)}
        </ul>
      )}
    </div>
  );
}

function SourceCard({ source, onChanged }: { source: SyncSource; onChanged: () => Promise<void> }) {
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState<string | null>(null);
  const [runs, setRuns] = useState<SyncRun[] | null>(null);
  const [open, setOpen] = useState(false);
  const running = source.last_run?.status === "RUNNING";
  const link = sourceLink(source);
  const cfg = source.config as { repo?: string; branch?: string; path?: string; mirror_collaborators?: boolean };

  async function act(fn: () => Promise<unknown>, fail: string) {
    setBusy(true);
    setNote(null);
    try {
      await fn();
      await onChanged();
    } catch (e) {
      setNote(e instanceof ApiError && e.status === 409 ? e.message : fail);
    } finally {
      setBusy(false);
    }
  }

  async function toggleRuns() {
    const next = !open;
    setOpen(next);
    if (next) setRuns(await listRuns(source.id).catch(() => []));
  }

  return (
    <li className={card}>
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <h2 className="break-words text-xl font-semibold">{source.name}</h2>
          <p className="mt-1 break-words text-sm text-muted">
            {source.kind === "GITHUB" ? "GitHub" : source.kind} ·{" "}
            {link ? <a href={link} target="_blank" rel="noopener noreferrer" className="text-accent2 hover:underline">{cfg.repo}{cfg.path ? `/${cfg.path}` : ""}</a> : "settings hidden"}
            {cfg.branch ? ` (${cfg.branch})` : ""}
          </p>
          <p className="mt-1 text-sm text-muted">
            Syncs {intervalText(source.interval_minutes)}
            {cfg.mirror_collaborators === false ? " · collaborator check off" : " · only repository collaborators may read"}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button type="button" disabled={busy || running} onClick={() => void act(() => runSource(source.id), "The sync could not be started.")}
            className="rounded-lg bg-accent px-5 py-2.5 font-medium text-bg hover:bg-accent2 disabled:opacity-60">
            {running ? "Syncing…" : "Sync now"}
          </button>
          <button type="button" disabled={busy} aria-pressed={source.enabled}
            onClick={() => void act(() => updateSource(source.id, { enabled: !source.enabled }), "The change could not be saved.")}
            className="rounded-lg border border-line px-4 py-2.5 hover:border-accent2 disabled:opacity-60">
            {source.enabled ? "Automatic sync on" : "Automatic sync off"}
          </button>
          <label className="sr-only" htmlFor={`iv-${source.id}`}>Sync interval</label>
          <select id={`iv-${source.id}`} className={`${selectClass} !w-auto !py-2.5`} value={source.interval_minutes} disabled={busy}
            onChange={(e) => void act(() => updateSource(source.id, { interval_minutes: Number(e.target.value) }), "The change could not be saved.")}>
            {Array.from(new Set([...INTERVALS, source.interval_minutes])).sort((a, b) => a - b).map((m) => <option key={m} value={m}>{intervalText(m)}</option>)}
          </select>
        </div>
      </div>
      {note && <p role="alert" className="mt-3 text-sm text-bad">{note}</p>}

      <div className="mt-5 rounded-xl border border-line bg-surface2 p-4" aria-live="polite">
        {source.last_run ? (
          <>
            <div className="mb-2 flex flex-wrap items-center gap-3">
              <VerdictBadge run={source.last_run} />
              <span className="text-sm text-muted">{source.last_run.trigger === "SCHEDULE" ? "Automatic" : "Manual"} · {ageText(source.last_run.started_at)}</span>
            </div>
            <RunDetails run={source.last_run} />
          </>
        ) : <p className="text-sm text-muted">Not synced yet. Press Sync now.</p>}
      </div>

      <button type="button" aria-expanded={open} onClick={() => void toggleRuns()} className="mt-4 text-sm text-accent2 hover:underline">
        {open ? "Hide recent runs" : "Show recent runs"}
      </button>
      {open && (
        <div className="mt-3 overflow-x-auto">
          {runs === null ? <p className="text-sm text-muted">Loading…</p> : runs.length === 0 ? <p className="text-sm text-muted">No runs yet.</p> : (
            <table className="w-full min-w-[520px] text-left text-sm">
              <thead className="text-muted"><tr><th scope="col" className="py-2 pr-4 font-medium">Started</th><th scope="col" className="py-2 pr-4 font-medium">How</th><th scope="col" className="py-2 pr-4 font-medium">Result</th><th scope="col" className="py-2 font-medium">What happened</th></tr></thead>
              <tbody>
                {runs.map((r) => (
                  <tr key={r.id} className="border-t border-line align-top">
                    <td className="whitespace-nowrap py-2 pr-4">{ageText(r.started_at)}</td>
                    <td className="py-2 pr-4">{r.trigger === "SCHEDULE" ? "Automatic" : "Manual"}</td>
                    <td className="py-2 pr-4"><VerdictBadge run={r} /></td>
                    <td className="py-2"><RunDetails run={r} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </li>
  );
}

function AddSource({ departments, onCreated }: { departments: Department[]; onCreated: () => Promise<void> }) {
  const [form, setForm] = useState<GithubForm>(EMPTY);
  const [errors, setErrors] = useState<Partial<Record<keyof GithubForm, string>>>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const set = <K extends keyof GithubForm>(k: K, v: GithubForm[K]) => { setForm((f) => ({ ...f, [k]: v })); setErrors((e) => ({ ...e, [k]: undefined })); };

  async function submit(e: FormEvent) {
    e.preventDefault();
    const found = validateGithubForm(form);
    setErrors(found);
    setFormError(null);
    if (Object.keys(found).length || busy) return;
    setBusy(true);
    try {
      await createSource(githubSourceBody(form));
      setForm(EMPTY);
      await onCreated();
    } catch (err) {
      setFormError(err instanceof ApiError && (err.status === 409 || err.status === 422) ? err.message : "The source could not be added.");
    } finally {
      setBusy(false);
    }
  }

  const field = (id: keyof GithubForm, label: string, hint?: string) => (
    <div>
      <label htmlFor={`s-${id}`} className="mb-1 block text-sm font-medium">{label}</label>
      <input id={`s-${id}`} className={inputClass} value={String(form[id])} onChange={(e) => set(id, e.target.value as never)}
        aria-invalid={errors[id] ? true : undefined} aria-describedby={errors[id] ? `s-${id}-err` : hint ? `s-${id}-hint` : undefined} />
      {hint && !errors[id] && <p id={`s-${id}-hint`} className="mt-1 text-xs text-muted">{hint}</p>}
      {errors[id] && <FieldError id={`s-${id}-err`} message={errors[id]!} />}
    </div>
  );

  return (
    <section className={`${card} mt-8`} aria-labelledby="add-title">
      <h2 id="add-title" className="text-xl font-semibold">Add a GitHub source</h2>
      <p className="mt-2 text-sm text-muted">
        The token is not entered here. The server reads it from its own <code>.env</code> file (<code>GITHUB_TOKEN</code>, read-only), so it never appears on a screen.
      </p>
      <form onSubmit={submit} noValidate className="mt-5 grid gap-5 sm:grid-cols-2">
        {field("name", "Name", "Shown in the list, for example demo docs.")}
        {field("repo", "Repository", "owner/name")}
        {field("branch", "Branch")}
        {field("path", "Folder", "Only files in this folder are imported. Leave empty for the whole repository.")}
        <div>
          <label htmlFor="s-dept" className="mb-1 block text-sm font-medium">Department of new documents</label>
          <select id="s-dept" className={selectClass} value={form.departmentId} onChange={(e) => set("departmentId", e.target.value)} aria-invalid={errors.departmentId ? true : undefined}>
            <option value="">Choose…</option>
            {departments.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
          </select>
          {errors.departmentId && <FieldError id="s-dept-err" message={errors.departmentId} />}
        </div>
        <div>
          <label htmlFor="s-type" className="mb-1 block text-sm font-medium">Document type</label>
          <select id="s-type" className={selectClass} value={form.documentType} onChange={(e) => set("documentType", e.target.value)}>
            {DOCUMENT_TYPES.map((t) => <option key={t} value={t}>{t.charAt(0) + t.slice(1).toLowerCase()}</option>)}
          </select>
        </div>
        <div>
          <label htmlFor="s-sens" className="mb-1 block text-sm font-medium">Sensitivity</label>
          <select id="s-sens" className={selectClass} value={form.sensitivity} onChange={(e) => set("sensitivity", e.target.value)}>
            {SENSITIVITY_LEVELS.map((s) => <option key={s.value} value={s.value}>{s.value} · {s.name.replace("_", " ")}</option>)}
          </select>
        </div>
        <div>
          <label htmlFor="s-interval" className="mb-1 block text-sm font-medium">Sync</label>
          <select id="s-interval" className={selectClass} value={form.interval} onChange={(e) => set("interval", e.target.value)}>
            {INTERVALS.map((m) => <option key={m} value={m}>{intervalText(m)}</option>)}
          </select>
        </div>
        <div className="sm:col-span-2">
          <label className="flex items-start gap-3 text-sm">
            <input type="checkbox" className="mt-1 h-4 w-4" checked={form.mirror} onChange={(e) => set("mirror", e.target.checked)} />
            <span>Only people who are collaborators of the repository may read its documents. Removing someone on GitHub removes their access here at the next sync.</span>
          </label>
        </div>
        {formError && <div className="sm:col-span-2"><FormErrorBox message={formError} /></div>}
        <div className="sm:col-span-2">
          <button type="submit" disabled={busy} className="rounded-lg bg-accent px-5 py-3 font-medium text-bg hover:bg-accent2 disabled:opacity-70">{busy ? "Adding…" : "Add source"}</button>
        </div>
      </form>
    </section>
  );
}

export function SourcesView() {
  const [sources, setSources] = useState<SyncSource[] | null>(null);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [error, setError] = useState<{ message: string; requestId?: string } | null>(null);

  const load = useCallback(async () => {
    try {
      setSources(await listSources());
      setError(null);
    } catch (e) {
      setError({ message: "The sources could not be loaded.", requestId: e instanceof ApiError ? e.requestId : undefined });
    }
  }, []);
  useEffect(() => { void load(); }, [load]);
  useEffect(() => { listDepartments().then(setDepartments).catch(() => setDepartments([])); }, []);
  usePolling(load, 3000, sources !== null && isRunning(sources));

  return (
    <main id="main" className="mx-auto w-full max-w-4xl px-5 py-10">
      <h1 className="text-3xl font-semibold tracking-tight">Sources</h1>
      <p className="mt-2 max-w-2xl text-muted">
        A source keeps documents in step with a place they live, such as a GitHub folder. Only what changed is processed, and who may read each document follows the source.
      </p>
      <div className="mt-8">
        {error ? <ErrorState message={error.message} requestId={error.requestId} onRetry={() => void load()} />
          : !sources ? <TableSkeleton rows={2} />
          : sources.length === 0 ? <EmptyState title="No sources yet" text="Add a GitHub source below to import a folder of documents." />
          : <ul className="space-y-6">{sources.map((s) => <SourceCard key={s.id} source={s} onChanged={load} />)}</ul>}
      </div>
      <AddSource departments={departments} onCreated={load} />
    </main>
  );
}
