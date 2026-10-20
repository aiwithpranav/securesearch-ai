"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { ApiError, type Department } from "@/lib/api";
import {
  anyBusy,
  failureReason,
  formatDateTime,
  listDepartments,
  listDocuments,
  STATUS_LABELS,
  type DocumentPage,
  type JobStatus,
} from "@/lib/documents";
import { usePolling } from "@/lib/usePolling";
import { EmptyState, ErrorState, SensitivityBadge, selectClass, StatusBadge, TableSkeleton } from "../_components/ui";

const PAGE_SIZE = 20;

export function DocumentsView() {
  const [page, setPage] = useState<DocumentPage | null>(null);
  const [error, setError] = useState<{ message: string; requestId?: string } | null>(null);
  const [loading, setLoading] = useState(true);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [status, setStatus] = useState<JobStatus | "">("");
  const [departmentId, setDepartmentId] = useState("");
  const [offset, setOffset] = useState(0);

  const query = useCallback(() => {
    const p = new URLSearchParams({ limit: String(PAGE_SIZE), offset: String(offset) });
    if (status) p.set("status", status);
    if (departmentId) p.set("department_id", departmentId);
    return `?${p.toString()}`;
  }, [offset, status, departmentId]);

  const load = useCallback(
    async (silent = false) => {
      if (!silent) setLoading(true);
      try {
        setPage(await listDocuments(query()));
        setError(null);
      } catch (e) {
        if (!silent || !page) {
          setError({
            message: e instanceof ApiError && !e.isNetworkError ? "The documents could not be loaded." : (e as Error).message,
            requestId: e instanceof ApiError ? e.requestId : undefined,
          });
        }
      } finally {
        setLoading(false);
      }
    },
    [query, page],
  );

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [offset, status, departmentId]);

  useEffect(() => {
    listDepartments().then(setDepartments).catch(() => setDepartments([]));
  }, []);

  // While something is still being processed, refresh the table every 3 seconds.
  usePolling(() => load(true), 3000, page !== null && anyBusy(page.items));

  const filtered = status !== "" || departmentId !== "";
  const total = page?.total ?? 0;
  const from = total === 0 ? 0 : offset + 1;
  const to = Math.min(offset + PAGE_SIZE, total);

  return (
    <main id="main" className="mx-auto w-full max-w-6xl px-5 py-12">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight">Documents</h1>
          <p className="mt-2 text-muted">Upload documents and follow their processing. Text is never shown here.</p>
        </div>
        <Link href="/admin/documents/upload" className="rounded-lg bg-accent px-5 py-3 font-medium text-bg hover:bg-accent2">
          Upload document
        </Link>
      </div>

      <div className="mt-8 flex flex-wrap gap-4">
        <div>
          <label htmlFor="f-status" className="mb-1 block text-sm text-muted">Status</label>
          <select id="f-status" className={selectClass} value={status}
            onChange={(e) => { setOffset(0); setStatus(e.target.value as JobStatus | ""); }}>
            <option value="">All</option>
            {(Object.keys(STATUS_LABELS) as JobStatus[]).map((s) => (
              <option key={s} value={s}>{STATUS_LABELS[s]}</option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="f-dept" className="mb-1 block text-sm text-muted">Department</label>
          <select id="f-dept" className={selectClass} value={departmentId}
            onChange={(e) => { setOffset(0); setDepartmentId(e.target.value); }}>
            <option value="">All</option>
            {departments.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
          </select>
        </div>
      </div>

      <div className="mt-8" aria-live="polite">
        {loading && !page ? (
          <TableSkeleton />
        ) : error && !page ? (
          <ErrorState message={error.message} requestId={error.requestId} onRetry={() => void load()} />
        ) : page && page.total === 0 ? (
          filtered ? (
            <EmptyState title="No documents match" text="Try a different status or department." />
          ) : (
            <EmptyState
              title="No documents yet"
              text="Upload your first document. It will be processed in the background."
              action={{ href: "/admin/documents/upload", label: "Upload your first document" }}
            />
          )
        ) : page ? (
          <>
            {error && <div className="mb-4"><ErrorState message={error.message} requestId={error.requestId} onRetry={() => void load()} /></div>}
            <div className="relative overflow-x-auto rounded-2xl border border-line">
              <table className="w-full min-w-[820px] text-left text-sm">
                <caption className="sr-only">Documents</caption>
                <thead className="bg-surface text-muted">
                  <tr>
                    <th scope="col" className="px-4 py-3 font-medium">Title</th>
                    <th scope="col" className="px-4 py-3 font-medium">Department</th>
                    <th scope="col" className="px-4 py-3 font-medium">Type</th>
                    <th scope="col" className="px-4 py-3 font-medium">Sensitivity</th>
                    <th scope="col" className="px-4 py-3 font-medium">Status</th>
                    <th scope="col" className="px-4 py-3 text-right font-medium">Chunks</th>
                    <th scope="col" className="px-4 py-3 font-medium">Updated</th>
                  </tr>
                </thead>
                <tbody>
                  {page.items.map((d) => (
                    <tr key={d.id} className="border-t border-line align-top">
                      <td className="px-4 py-3">
                        <Link href={`/admin/documents/${d.id}`} className="font-medium text-accent2 hover:underline">{d.title}</Link>
                        <div className="text-xs text-muted">{d.original_filename}</div>
                      </td>
                      <td className="px-4 py-3">{d.department.name}</td>
                      <td className="px-4 py-3">{d.document_type}</td>
                      <td className="px-4 py-3"><SensitivityBadge level={d.sensitivity_level} name={d.sensitivity_name} /></td>
                      <td className="px-4 py-3">
                        <StatusBadge status={d.latest_job && d.latest_job.status !== "READY" && d.status === "READY" ? d.latest_job.status : d.status} />
                        {d.latest_job?.status === "FAILED" && (
                          <div className="mt-1 max-w-xs text-xs text-bad">{failureReason(d.latest_job.error_code)}</div>
                        )}
                      </td>
                      <td className="px-4 py-3 text-right tabular-nums">{d.chunk_count}</td>
                      <td className="px-4 py-3 text-muted">{formatDateTime(d.updated_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="mt-4 flex items-center justify-between text-sm text-muted">
              <span>Showing {from} to {to} of {total}</span>
              <div className="flex gap-2">
                <button type="button" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
                  className="rounded-lg border border-line px-4 py-2 hover:border-accent2 disabled:opacity-50">Previous</button>
                <button type="button" disabled={offset + PAGE_SIZE >= total} onClick={() => setOffset(offset + PAGE_SIZE)}
                  className="rounded-lg border border-line px-4 py-2 hover:border-accent2 disabled:opacity-50">Next</button>
              </div>
            </div>
          </>
        ) : null}
      </div>
    </main>
  );
}
