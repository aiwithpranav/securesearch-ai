"use client";

import { Fragment, useCallback, useEffect, useState } from "react";
import { ApiError } from "@/lib/api";
import {
  dayEndExclusive, dayStart, downloadQueryCsv, listEvents, listQueries, pageRange, PAGE_SIZE, personLabel, statusLabel,
  type EventRow, type Page, type QueryFilters, type QueryRow,
} from "@/lib/audit";
import { ageText } from "@/lib/chat";
import { EmptyState, ErrorState, selectClass, TableSkeleton } from "../admin/_components/ui";

const inputClass = "w-full rounded-lg border border-line bg-surface2 px-3 py-2 text-text";
const EVENT_NAMES = ["", "admin.acl_rule_added", "admin.acl_rule_deleted", "admin.acl_rule_updated", "admin.document_deleted", "admin.document_reindex", "admin.document_updated", "admin.document_uploaded", "admin.group_created", "admin.group_member_added", "admin.group_member_removed", "admin.roles_set", "admin.user_created", "admin.user_deactivated", "admin.user_updated", "audit.export", "auth.change_password_failed", "auth.login_failed", "auth.login_locked", "auth.login_ok", "auth.logout_all", "auth.password_changed", "auth.password_reset", "auth.refresh_reuse_detected", "auth.reset_requested"];

type Tab = "queries" | "events";
type Draft = { kind: string; status: string; q: string; since: string; until: string };
const EMPTY: Draft = { kind: "", status: "", q: "", since: "", until: "" };
const toFilters = (d: Draft): QueryFilters => ({ kind: d.kind, status: d.status, q: d.q, since: dayStart(d.since), until: dayEndExclusive(d.until) });

function Pager({ offset, shown, total, onPage }: { offset: number; shown: number; total: number; onPage: (o: number) => void }) {
  return (
    <div className="mt-4 flex flex-wrap items-center justify-between gap-3 text-sm text-muted">
      <span aria-live="polite">{pageRange(offset, shown, total)}</span>
      <div className="flex gap-2">
        <button type="button" disabled={offset === 0} onClick={() => onPage(Math.max(0, offset - PAGE_SIZE))} className="rounded-lg border border-line px-4 py-2 enabled:hover:border-accent2 disabled:opacity-40">Previous</button>
        <button type="button" disabled={offset + shown >= total} onClick={() => onPage(offset + PAGE_SIZE)} className="rounded-lg border border-line px-4 py-2 enabled:hover:border-accent2 disabled:opacity-40">Next</button>
      </div>
    </div>
  );
}

function QueriesTable({ rows }: { rows: QueryRow[] }) {
  const [open, setOpen] = useState<string | null>(null);
  return (
    <div className="overflow-x-auto rounded-2xl border border-line">
      <table className="w-full min-w-[720px] text-left text-sm">
        <thead className="bg-surface text-muted">
          <tr>{["When", "Who", "Type", "Question", "Result", "Time", ""].map((h, i) => <th key={i} scope="col" className="px-4 py-3 font-medium">{h || <span className="sr-only">Details</span>}</th>)}</tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <Fragment key={r.id}>
              <tr className="border-t border-line align-top">
                <td className="whitespace-nowrap px-4 py-3 text-muted" title={new Date(r.created_at).toLocaleString()}>{ageText(r.created_at)}</td>
                <td className="px-4 py-3">{personLabel(r.user)}</td>
                <td className="px-4 py-3">{r.kind === "CHAT" ? "Question" : "Search"}</td>
                <td className="max-w-xs break-words px-4 py-3">{r.query_text}</td>
                <td className="px-4 py-3">{statusLabel(r.response_status)}</td>
                <td className="whitespace-nowrap px-4 py-3 text-muted">{r.latency_ms} ms</td>
                <td className="px-4 py-3">
                  <button type="button" aria-expanded={open === r.id} onClick={() => setOpen(open === r.id ? null : r.id)} className="text-accent2 hover:underline">
                    {open === r.id ? "Hide" : "Details"}
                  </button>
                </td>
              </tr>
              {open === r.id && (
                <tr className="bg-surface/60">
                  <td colSpan={7} className="px-4 py-3 text-muted">
                    <p>Documents the person could read: <b className="text-text">{r.allowed_doc_count}</b>. Passages returned: <b className="text-text">{r.retrieved_chunk_ids.length}</b>.</p>
                    <p className="mt-1 break-all text-xs">Request: {r.request_id ?? "–"} · Record: {r.id}</p>
                  </td>
                </tr>
              )}
            </Fragment>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function EventsTable({ rows }: { rows: EventRow[] }) {
  return (
    <div className="overflow-x-auto rounded-2xl border border-line">
      <table className="w-full min-w-[640px] text-left text-sm">
        <thead className="bg-surface text-muted">
          <tr>{["When", "Event", "Done by", "Done to", "Details"].map((h) => <th key={h} scope="col" className="px-4 py-3 font-medium">{h}</th>)}</tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.id} className="border-t border-line align-top">
              <td className="whitespace-nowrap px-4 py-3 text-muted" title={new Date(r.created_at).toLocaleString()}>{ageText(r.created_at)}</td>
              <td className="px-4 py-3 font-mono text-xs">{r.event}</td>
              <td className="px-4 py-3">{personLabel(r.actor)}</td>
              <td className="px-4 py-3">{r.subject ? personLabel(r.subject) : "–"}</td>
              <td className="max-w-xs break-all px-4 py-3 text-xs text-muted">{Object.keys(r.detail).length ? JSON.stringify(r.detail) : "–"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function AuditView() {
  const [tab, setTab] = useState<Tab>("queries");
  const [draft, setDraft] = useState<Draft>(EMPTY);
  const [applied, setApplied] = useState<Draft>(EMPTY);
  const [event, setEvent] = useState("");
  const [offset, setOffset] = useState(0);
  const [queries, setQueries] = useState<Page<QueryRow> | null>(null);
  const [events, setEvents] = useState<Page<EventRow> | null>(null);
  const [error, setError] = useState<{ message: string; requestId?: string } | null>(null);
  const [note, setNote] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);

  const load = useCallback(async () => {
    setError(null);
    try {
      if (tab === "queries") setQueries(await listQueries(toFilters(applied), offset));
      else setEvents(await listEvents(event, offset));
    } catch (e) {
      setError({ message: "The audit records could not be loaded.", requestId: e instanceof ApiError ? e.requestId : undefined });
    }
  }, [tab, applied, event, offset]);

  useEffect(() => { void load(); }, [load]);

  async function exportCsv() {
    setExporting(true);
    setNote(null);
    try {
      await downloadQueryCsv(toFilters(applied));
      setNote("The export was downloaded. It was recorded in the audit trail.");
    } catch {
      setNote("The export could not be created.");
    } finally {
      setExporting(false);
    }
  }

  const switchTab = (t: Tab) => { setTab(t); setOffset(0); setError(null); };
  const page = tab === "queries" ? queries : events;
  const tabClass = (t: Tab) => `rounded-lg px-4 py-2 text-sm ${tab === t ? "bg-surface2 text-text" : "text-muted hover:text-text"}`;

  return (
    <main id="main" className="mx-auto w-full max-w-6xl px-5 py-10">
      <h1 className="text-3xl font-semibold tracking-tight">Audit trail</h1>
      <p className="mt-2 max-w-2xl text-muted">Who asked what, and what happened. Records cannot be changed or deleted. Answers and document text are never stored here.</p>

      <div role="tablist" aria-label="Audit records" className="mt-6 flex gap-2">
        <button role="tab" aria-selected={tab === "queries"} className={tabClass("queries")} onClick={() => switchTab("queries")}>Questions and searches</button>
        <button role="tab" aria-selected={tab === "events"} className={tabClass("events")} onClick={() => switchTab("events")}>Security events</button>
      </div>

      {tab === "queries" ? (
        <form
          className="mt-4 grid gap-3 rounded-2xl border border-line bg-surface p-4 sm:grid-cols-2 lg:grid-cols-5"
          onSubmit={(e) => { e.preventDefault(); setOffset(0); setApplied(draft); }}
        >
          <label className="text-sm">Type
            <select className={`${selectClass} mt-1 !py-2`} value={draft.kind} onChange={(e) => setDraft({ ...draft, kind: e.target.value })}>
              <option value="">All</option><option value="CHAT">Questions</option><option value="SEARCH">Searches</option>
            </select>
          </label>
          <label className="text-sm">Result
            <select className={`${selectClass} mt-1 !py-2`} value={draft.status} onChange={(e) => setDraft({ ...draft, status: e.target.value })}>
              <option value="">All</option>
              {["ANSWERED", "REFUSED_LOW_CONFIDENCE", "REFUSED_NO_ACCESS_EVIDENCE", "UNAVAILABLE", "OK", "NO_RESULTS"].map((s) => <option key={s} value={s}>{statusLabel(s)}</option>)}
            </select>
          </label>
          <label className="text-sm">From<input type="date" className={`${inputClass} mt-1`} value={draft.since} onChange={(e) => setDraft({ ...draft, since: e.target.value })} /></label>
          <label className="text-sm">To<input type="date" className={`${inputClass} mt-1`} value={draft.until} onChange={(e) => setDraft({ ...draft, until: e.target.value })} /></label>
          <label className="text-sm">Words in the question<input maxLength={200} className={`${inputClass} mt-1`} value={draft.q} onChange={(e) => setDraft({ ...draft, q: e.target.value })} /></label>
          <div className="flex flex-wrap gap-2 sm:col-span-2 lg:col-span-5">
            <button type="submit" className="rounded-lg bg-accent px-5 py-2 font-medium text-bg hover:bg-accent2">Apply filters</button>
            <button type="button" onClick={() => { setDraft(EMPTY); setApplied(EMPTY); setOffset(0); }} className="rounded-lg border border-line px-5 py-2 hover:border-accent2">Clear</button>
            <button type="button" onClick={exportCsv} disabled={exporting} className="rounded-lg border border-line px-5 py-2 hover:border-accent2 disabled:opacity-60 sm:ml-auto">
              {exporting ? "Preparing…" : "Export CSV"}
            </button>
          </div>
        </form>
      ) : (
        <div className="mt-4 max-w-xs">
          <label className="text-sm">Event
            <select className={`${selectClass} mt-1 !py-2`} value={event} onChange={(e) => { setEvent(e.target.value); setOffset(0); }}>
              {EVENT_NAMES.map((n) => <option key={n} value={n}>{n || "All events"}</option>)}
            </select>
          </label>
        </div>
      )}
      {note && <p role="status" className="mt-3 text-sm text-muted">{note}</p>}

      <div className="mt-6">
        {error ? <ErrorState message={error.message} requestId={error.requestId} onRetry={() => void load()} />
          : !page ? <TableSkeleton />
          : page.items.length === 0 ? <EmptyState title="No records match" text="Try clearing the filters or widening the dates." />
          : (
            <>
              {tab === "queries" ? <QueriesTable rows={queries!.items} /> : <EventsTable rows={events!.items} />}
              <Pager offset={page.offset} shown={page.items.length} total={page.total} onPage={setOffset} />
            </>
          )}
      </div>
    </main>
  );
}
