"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { ApiError, type Department } from "@/lib/api";
import {
  deleteDocument,
  DOCUMENT_TYPES,
  failureReason,
  formatBytes,
  formatDateTime,
  getDocument,
  isBusy,
  listDepartments,
  listJobs,
  listVersions,
  parseCountries,
  reindexDocument,
  SENSITIVITY_LEVELS,
  updateDocument,
  type DocumentItem,
  type Job,
  type Version,
} from "@/lib/documents";
import { usePolling } from "@/lib/usePolling";
import { FieldError, FormErrorBox } from "../../../../_auth/ui";
import { ErrorState, SensitivityBadge, selectClass, StatusBadge, TableSkeleton } from "../../_components/ui";

const card = "rounded-2xl border border-line bg-surface p-6";
const inputClass = "w-full rounded-lg border border-line bg-surface2 px-4 py-3 text-text";

export function DocumentDetail() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [doc, setDoc] = useState<DocumentItem | null>(null);
  const [versions, setVersions] = useState<Version[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [loadError, setLoadError] = useState<{ message: string; requestId?: string; notFound: boolean } | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);
  const [busy, setBusy] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [form, setForm] = useState({ title: "", department_id: "", document_type: "", sensitivity_level: "1", countries: "" });
  const [countryError, setCountryError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [d, v, j] = await Promise.all([getDocument(id), listVersions(id), listJobs(id)]);
      setDoc(d);
      setVersions(v);
      setJobs(j.items);
      setLoadError(null);
    } catch (e) {
      const api = e instanceof ApiError ? e : null;
      setLoadError({
        message: api?.status === 404 ? "This document was not found." : api && !api.isNetworkError ? "The document could not be loaded." : (e as Error).message,
        requestId: api?.requestId,
        notFound: api?.status === 404,
      });
    }
  }, [id]);

  useEffect(() => {
    void load();
    listDepartments().then(setDepartments).catch(() => setDepartments([]));
  }, [load]);

  const unfinished = doc !== null && (isBusy(doc.status) || (doc.latest_job !== null && isBusy(doc.latest_job.status)));
  usePolling(load, 3000, unfinished && !editing);

  function startEdit() {
    if (!doc) return;
    setForm({
      title: doc.title,
      department_id: String(doc.department.id),
      document_type: doc.document_type,
      sensitivity_level: String(doc.sensitivity_level),
      countries: (doc.allowed_countries ?? []).join(", "),
    });
    setActionError(null);
    setCountryError(null);
    setEditing(true);
  }

  async function onSave(e: FormEvent) {
    e.preventDefault();
    const c = parseCountries(form.countries);
    setCountryError(c.error);
    if (c.error || busy) return;
    setBusy(true);
    setActionError(null);
    try {
      setDoc(await updateDocument(id, {
        title: form.title.trim() || undefined,
        department_id: Number(form.department_id),
        document_type: form.document_type,
        sensitivity_level: Number(form.sensitivity_level),
        allowed_countries: c.codes.length ? c.codes : null,
      }));
      setEditing(false);
    } catch (err) {
      setActionError(err instanceof ApiError && err.status === 422 ? err.message : "The changes could not be saved.");
    } finally {
      setBusy(false);
    }
  }

  async function onReindex() {
    setBusy(true);
    setActionError(null);
    try {
      await reindexDocument(id);
      await load();
    } catch (err) {
      setActionError(err instanceof ApiError && err.status === 409 ? "This document is already being processed." : "Re-indexing could not be started.");
    } finally {
      setBusy(false);
    }
  }

  async function onDelete() {
    setBusy(true);
    setActionError(null);
    try {
      await deleteDocument(id);
      router.replace("/admin/documents");
    } catch {
      setBusy(false);
      setActionError("The document could not be deleted.");
    }
  }

  if (loadError && !doc) {
    return (
      <main id="main" className="mx-auto w-full max-w-3xl px-5 py-12">
        <Link href="/admin/documents" className="text-sm text-muted hover:text-text">← Documents</Link>
        <div className="mt-6"><ErrorState message={loadError.message} requestId={loadError.requestId} onRetry={loadError.notFound ? undefined : () => void load()} /></div>
      </main>
    );
  }
  if (!doc) {
    return <main id="main" className="mx-auto w-full max-w-3xl px-5 py-12"><TableSkeleton rows={4} /></main>;
  }

  const latest = doc.latest_job;
  const reindexDisabled = busy || unfinished;

  return (
    <main id="main" className="mx-auto w-full max-w-4xl px-5 py-12">
      <Link href="/admin/documents" className="text-sm text-muted hover:text-text">← Documents</Link>
      <div className="mt-4 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight">{doc.title}</h1>
          <p className="mt-1 text-sm text-muted">{doc.original_filename}</p>
        </div>
        <div aria-live="polite"><StatusBadge status={latest && isBusy(latest.status) ? latest.status : doc.status} /></div>
      </div>

      {actionError && <div className="mt-6"><FormErrorBox message={actionError} /></div>}
      {latest?.status === "FAILED" && (
        <div role="alert" className="mt-6 rounded-lg border border-bad/60 bg-bad/10 p-4 text-sm text-bad">
          Processing failed: {latest.error_message ?? failureReason(latest.error_code)}
          {doc.chunk_count > 0 && " The previous version is still in use."}
        </div>
      )}

      <section className={`${card} mt-8`} aria-labelledby="meta-title">
        <div className="flex items-center justify-between gap-4">
          <h2 id="meta-title" className="text-xl font-semibold">Details</h2>
          {!editing && <button type="button" onClick={startEdit} className="rounded-lg border border-line px-4 py-2 text-sm hover:border-accent2">Edit details</button>}
        </div>

        {!editing ? (
          <dl className="mt-6 grid gap-6 sm:grid-cols-2">
            <div><dt className="text-sm text-muted">Department</dt><dd className="mt-1 font-medium">{doc.department.name}</dd></div>
            <div><dt className="text-sm text-muted">Type</dt><dd className="mt-1 font-medium">{doc.document_type}</dd></div>
            <div><dt className="text-sm text-muted">Sensitivity</dt><dd className="mt-1"><SensitivityBadge level={doc.sensitivity_level} name={doc.sensitivity_name} /></dd></div>
            <div><dt className="text-sm text-muted">Allowed countries</dt><dd className="mt-1 font-medium">{doc.allowed_countries?.join(", ") ?? "No country limit"}</dd></div>
            <div><dt className="text-sm text-muted">Chunks in use</dt><dd className="mt-1 font-medium tabular-nums">{doc.chunk_count}</dd></div>
            <div><dt className="text-sm text-muted">Version</dt><dd className="mt-1 font-medium">{doc.current_version_no ?? "-"} (of {doc.version_count})</dd></div>
            <div><dt className="text-sm text-muted">Uploaded by</dt><dd className="mt-1 font-medium">{doc.uploaded_by.full_name}</dd></div>
            <div><dt className="text-sm text-muted">Uploaded</dt><dd className="mt-1 font-medium">{formatDateTime(doc.created_at)}</dd></div>
          </dl>
        ) : (
          <form onSubmit={onSave} noValidate className="mt-6 space-y-5">
            <div>
              <label htmlFor="e-title" className="mb-2 block text-sm font-medium">Title</label>
              <input id="e-title" maxLength={200} className={inputClass} value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
            </div>
            <div className="grid gap-5 sm:grid-cols-2">
              <div>
                <label htmlFor="e-dept" className="mb-2 block text-sm font-medium">Department</label>
                <select id="e-dept" className={selectClass} value={form.department_id} onChange={(e) => setForm({ ...form, department_id: e.target.value })}>
                  {departments.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
                </select>
              </div>
              <div>
                <label htmlFor="e-type" className="mb-2 block text-sm font-medium">Document type</label>
                <select id="e-type" className={selectClass} value={form.document_type} onChange={(e) => setForm({ ...form, document_type: e.target.value })}>
                  {DOCUMENT_TYPES.map((t) => <option key={t} value={t}>{t.charAt(0) + t.slice(1).toLowerCase()}</option>)}
                </select>
              </div>
              <div>
                <label htmlFor="e-sens" className="mb-2 block text-sm font-medium">Sensitivity</label>
                <select id="e-sens" className={selectClass} value={form.sensitivity_level} onChange={(e) => setForm({ ...form, sensitivity_level: e.target.value })}>
                  {SENSITIVITY_LEVELS.map((s) => <option key={s.value} value={s.value}>{s.value} · {s.name.replace("_", " ")}</option>)}
                </select>
              </div>
              <div>
                <label htmlFor="e-countries" className="mb-2 block text-sm font-medium">Allowed countries</label>
                <input id="e-countries" className={inputClass} placeholder="IN, US" value={form.countries}
                  aria-invalid={countryError ? true : undefined} aria-describedby={countryError ? "e-country-error" : undefined}
                  onChange={(e) => { setForm({ ...form, countries: e.target.value }); setCountryError(null); }} />
                {countryError && <FieldError id="e-country-error" message={countryError} />}
              </div>
            </div>
            <div className="flex gap-3">
              <button type="submit" disabled={busy} className="rounded-lg bg-accent px-5 py-2.5 font-medium text-bg hover:bg-accent2 disabled:opacity-70">{busy ? "Saving…" : "Save"}</button>
              <button type="button" onClick={() => setEditing(false)} disabled={busy} className="rounded-lg border border-line px-5 py-2.5 hover:border-accent2">Cancel</button>
            </div>
          </form>
        )}
        <p className="mt-6 text-sm text-muted">
          Document text is not shown here. Administrators manage documents but cannot read their content.
        </p>
      </section>

      <section className={`${card} mt-8`} aria-labelledby="actions-title">
        <h2 id="actions-title" className="text-xl font-semibold">Actions</h2>
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <button type="button" onClick={onReindex} disabled={reindexDisabled}
            className="rounded-lg border border-line px-5 py-2.5 hover:border-accent2 disabled:cursor-not-allowed disabled:opacity-50">
            Re-index
          </button>
          {!confirmDelete ? (
            <button type="button" onClick={() => setConfirmDelete(true)} disabled={busy}
              className="rounded-lg border border-bad/60 px-5 py-2.5 text-bad hover:bg-bad/10 disabled:opacity-50">
              Delete document
            </button>
          ) : (
            <div className="flex flex-wrap items-center gap-3" role="group" aria-label="Confirm delete">
              <span className="text-sm">Delete this document? It disappears from the list.</span>
              <button type="button" onClick={onDelete} disabled={busy} autoFocus className="rounded-lg bg-bad px-4 py-2 text-sm font-medium text-bg disabled:opacity-70">{busy ? "Deleting…" : "Yes, delete"}</button>
              <button type="button" onClick={() => setConfirmDelete(false)} disabled={busy} className="rounded-lg border border-line px-4 py-2 text-sm hover:border-accent2">Cancel</button>
            </div>
          )}
        </div>
        <p className="mt-3 text-sm text-muted">Re-index reads the stored file again and rebuilds the chunks. The current chunks stay in use until the new ones are complete.</p>
      </section>

      <section className={`${card} mt-8`} aria-labelledby="hist-title">
        <h2 id="hist-title" className="text-xl font-semibold">Processing history</h2>
        {jobs.length === 0 ? <p className="mt-4 text-muted">No jobs yet.</p> : (
          <div className="mt-4 overflow-x-auto">
            <table className="w-full min-w-[560px] text-left text-sm">
              <caption className="sr-only">Processing jobs, newest first</caption>
              <thead className="text-muted"><tr>
                <th scope="col" className="py-2 pr-4 font-medium">Started</th>
                <th scope="col" className="py-2 pr-4 font-medium">Status</th>
                <th scope="col" className="py-2 pr-4 font-medium">Attempts</th>
                <th scope="col" className="py-2 font-medium">Result</th>
              </tr></thead>
              <tbody>
                {jobs.map((j) => (
                  <tr key={j.id} className="border-t border-line align-top">
                    <td className="py-2 pr-4">{formatDateTime(j.started_at ?? j.created_at)}</td>
                    <td className="py-2 pr-4"><StatusBadge status={j.status} /></td>
                    <td className="py-2 pr-4 tabular-nums">{j.attempt}</td>
                    <td className="py-2 text-muted">{j.status === "FAILED" ? (j.error_message ?? failureReason(j.error_code)) : j.completed_at ? `Finished ${formatDateTime(j.completed_at)}` : "In progress"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className={`${card} mt-8`} aria-labelledby="ver-title">
        <h2 id="ver-title" className="text-xl font-semibold">Versions</h2>
        <ul className="mt-4 space-y-2 text-sm">
          {versions.map((v) => (
            <li key={v.id} className="flex flex-wrap gap-x-6 gap-y-1">
              <span className="font-medium">Version {v.version_no}</span>
              <span className="text-muted">{formatBytes(v.size_bytes)}</span>
              <span className="text-muted">{formatDateTime(v.created_at)}</span>
              <span className="font-mono text-xs text-muted" title="SHA-256 fingerprint of the original file">{v.content_hash.slice(0, 12)}…</span>
            </li>
          ))}
        </ul>
      </section>
    </main>
  );
}
