"use client";

import { takePendingQuestion } from "@/lib/pendingQuestion";
import { FormEvent, useEffect, useRef, useState } from "react";
import {
  allWeak, MAX_QUERY, previewText, relevanceWord, scoreDetails, scorePercent, searchDocuments, searchErrorText, validateQuery, whereText,
  type SearchHit, type SearchResponse,
} from "@/lib/search";
import { answersUnavailable, chatErrorText, streamAnswer, type ChatResult, type Stage } from "@/lib/chat";
import { useSession } from "../../_auth/AuthProvider";
import { FieldError } from "../../_auth/ui";
import { EmptyState, ErrorState } from "../admin/_components/ui";
import { AnswerCard } from "./AnswerCard";
import { EvidencePanel } from "./EvidencePanel";
import { HistoryList } from "./HistoryList";

const inputClass = "w-full rounded-lg border border-line bg-surface2 px-4 py-3 text-text";

function Result({ hit, isAdmin }: { hit: SearchHit; isAdmin: boolean }) {
  const [open, setOpen] = useState(false);
  const { short, truncated } = previewText(hit.content);
  const where = whereText(hit);
  const pct = scorePercent(hit.score);
  const details = scoreDetails(hit.scores);
  return (
    <article className="rounded-2xl border border-line bg-surface p-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-lg font-semibold">{hit.document_title}</h3>
          {where && <p className="mt-0.5 text-sm text-muted">{where}</p>}
        </div>
        <div className="min-w-[8rem]">
          <p className="text-xs text-muted">{relevanceWord(hit.score)} · {pct}%</p>
          <div role="img" aria-label={`Relevance ${pct} percent`} className="mt-1 h-2 w-full overflow-hidden rounded-full bg-surface2">
            <div className="h-full rounded-full bg-accent" style={{ width: `${pct}%` }} />
          </div>
        </div>
      </div>
      <p className="mt-4 whitespace-pre-line break-words">{open || !truncated ? hit.content : short}</p>
      {truncated && (
        <button type="button" onClick={() => setOpen(!open)} aria-expanded={open} className="mt-2 text-sm text-accent2 hover:underline">
          {open ? "Show less" : "Show more"}
        </button>
      )}
      {isAdmin && details.length > 0 && (
        <details className="mt-4 text-sm">
          <summary className="cursor-pointer text-muted">Score details (administrators only)</summary>
          <dl className="mt-2 grid grid-cols-[auto_1fr] gap-x-4 gap-y-1">
            {details.map((d) => (<div key={d.label} className="contents"><dt className="text-muted">{d.label}</dt><dd>{d.value}</dd></div>))}
          </dl>
        </details>
      )}
    </article>
  );
}

type Mode = "ask" | "find";

export function SearchView() {
  const { user } = useSession();
  const [mode, setMode] = useState<Mode>("ask");
  const [query, setQuery] = useState("");
  const [fieldError, setFieldError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  // "Find passages" (Phase 5)
  const [result, setResult] = useState<(SearchResponse & { searchedAt: number }) | null>(null);
  // "Ask" (Phase 6)
  const [stages, setStages] = useState<Stage[]>([]);
  const [answer, setAnswer] = useState<ChatResult | null>(null);
  const [error, setError] = useState<{ text: string; offerSearch: boolean } | null>(null);
  const [panel, setPanel] = useState<string | null>(null);
  const [historyKey, setHistoryKey] = useState(0);
  const latest = useRef(0); // only the newest request may update the screen
  const trigger = useRef<HTMLElement | null>(null); // the button that opened the panel, to return focus to it

  // A question picked on Home waits in memory; it only fills the box. The person still presses Ask.
  useEffect(() => {
    const picked = takePendingQuestion();
    if (picked) setQuery(picked);
  }, []);

  const isAdmin = user?.roles.includes("system_admin") ?? false;

  function reset() {
    setResult(null);
    setAnswer(null);
    setStages([]);
    setError(null);
  }

  async function find(text: string) {
    const id = ++latest.current;
    setLoading(true);
    reset();
    try {
      const res = await searchDocuments(text);
      if (id === latest.current) setResult({ ...res, searchedAt: Date.now() });
    } catch (err) {
      if (id === latest.current) setError({ text: searchErrorText(err), offerSearch: false });
    } finally {
      if (id === latest.current) setLoading(false);
    }
  }

  async function ask(text: string) {
    const id = ++latest.current;
    setLoading(true);
    reset();
    try {
      const res = await streamAnswer(text, (s) => {
        if (id === latest.current) setStages((prev) => [...prev.filter((p) => p.id !== s.id), s]);
      });
      if (id === latest.current) {
        setAnswer(res);
        setHistoryKey((k) => k + 1);
      }
    } catch (err) {
      if (id === latest.current) setError({ text: chatErrorText(err), offerSearch: answersUnavailable(err) });
    } finally {
      if (id === latest.current) setLoading(false);
    }
  }

  async function run(e?: FormEvent, forceMode?: Mode, text?: string) {
    e?.preventDefault();
    if (loading) return;
    const q = text ?? query;
    const problem = validateQuery(q);
    setFieldError(problem);
    if (problem) return;
    const m = forceMode ?? mode;
    if (m !== mode) setMode(m);
    if (m === "ask") await ask(q.trim());
    else await find(q.trim());
  }

  function openPanel(chunkId: string, button: HTMLElement) {
    trigger.current = button;
    setPanel(chunkId);
  }
  function closePanel() {
    setPanel(null);
    trigger.current?.focus();
  }

  const documents = result ? new Set(result.hits.map((h) => h.document_id)).size : 0;
  const seconds = result ? (result.took_ms / 1000).toFixed(1) : "";
  const modeBtn = (value: Mode, label: string) => (
    <button
      type="button" aria-pressed={mode === value} onClick={() => { if (!loading) { setMode(value); reset(); } }}
      className={`rounded-lg px-4 py-2 text-sm font-medium ${mode === value ? "bg-surface2 text-text" : "text-muted hover:text-text"}`}
    >
      {label}
    </button>
  );

  return (
    <main id="main" className="mx-auto w-full max-w-4xl px-5 py-12">
      <h1 className="text-3xl font-semibold tracking-tight">Ask</h1>
      <p className="mt-2 text-muted">Ask in your own words. Answers and passages come only from documents you are allowed to read.</p>

      <form onSubmit={run} noValidate className="mt-8" role="search">
        <div className="mb-3 inline-flex gap-1 rounded-xl border border-line p-1" role="group" aria-label="What do you want?">
          {modeBtn("ask", "Ask a question")}
          {modeBtn("find", "Find passages")}
        </div>
        <label htmlFor="q" className="mb-1 block text-sm font-medium">Your question</label>
        <div className="flex flex-wrap gap-3">
          <input
            id="q" type="search" autoComplete="off" autoFocus value={query} className={`${inputClass} min-w-[14rem] flex-1 ${fieldError ? "border-bad" : ""}`}
            placeholder="For example: how many days of annual leave do I get?"
            aria-invalid={fieldError ? true : undefined} aria-describedby={fieldError ? "q-error q-count" : "q-count"}
            onChange={(e) => { setQuery(e.target.value); setFieldError(null); }}
          />
          <button type="submit" disabled={loading} className="rounded-lg bg-accent px-6 py-3 font-medium text-bg hover:bg-accent2 disabled:opacity-70">
            {loading ? (mode === "ask" ? "Working…" : "Searching…") : mode === "ask" ? "Ask" : "Search"}
          </button>
        </div>
        <div className="mt-1 flex justify-between gap-3">
          <div id="q-error">{fieldError && <FieldError id="q-error-text" message={fieldError} />}</div>
          <p id="q-count" className={`text-xs ${query.trim().length > MAX_QUERY ? "text-bad" : "text-muted"}`}>{query.trim().length}/{MAX_QUERY}</p>
        </div>
      </form>

      <div className="mt-8" aria-live="polite" aria-busy={loading}>
        {loading ? (
          <div role="status">
            {mode === "ask" ? (
              <ul className="space-y-2" aria-label="Progress">
                {stages.length === 0 && <li className="text-muted">Starting…</li>}
                {stages.map((s) => (
                  <li key={s.id} className={s.status === "done" ? "text-muted" : "text-text"}>
                    <span aria-hidden="true" className="mr-2">{s.status === "done" ? "✓" : "…"}</span>{s.label}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-muted">Searching… this can take a few seconds.</p>
            )}
            <div className="mt-4 space-y-4" aria-hidden="true">
              {[0, 1].map((i) => <div key={i} className="h-24 animate-pulse rounded-2xl border border-line bg-surface motion-reduce:animate-none" />)}
            </div>
          </div>
        ) : error ? (
          <>
            <ErrorState message={error.text} onRetry={() => void run()} />
            {error.offerSearch && (
              <button type="button" onClick={() => void run(undefined, "find")} className="mt-4 rounded-lg border border-line px-4 py-2 hover:border-accent2">Find passages instead</button>
            )}
          </>
        ) : answer ? (
          answer.status === "ANSWERED" ? (
            <AnswerCard result={answer} onOpen={openPanel} />
          ) : (
            <EmptyState
              title="No answer found"
              text={`${answer.refusal ?? "Could not find enough accessible source material to answer this question."} Try different words, or look at the matching passages.`}
              action={undefined}
            />
          )
        ) : result ? (
          result.hits.length === 0 ? (
            <EmptyState title="No results" text="Nothing matched. Try different words. You can only find documents you are allowed to read, so a document may exist that you cannot see." />
          ) : (
            <>
              <p className="mb-4 text-sm text-muted">
                {result.count} {result.count === 1 ? "passage" : "passages"} from {documents} {documents === 1 ? "document" : "documents"} · {seconds} s
              </p>
              {allWeak(result.hits) && (
                <p role="note" className="mb-4 rounded-lg border border-line bg-surface2 p-3 text-sm">
                  These are only weak matches. The documents you may read probably do not cover this question. Try different words.
                </p>
              )}
              <div className="space-y-4">{result.hits.map((h) => <Result key={h.chunk_id} hit={h} isAdmin={isAdmin} />)}</div>
            </>
          )
        ) : null}
        {!loading && answer && answer.status !== "ANSWERED" && (
          <button type="button" onClick={() => void run(undefined, "find")} className="mt-4 rounded-lg border border-line px-4 py-2 hover:border-accent2">Show matching passages</button>
        )}
      </div>

      <HistoryList refreshKey={historyKey} onAskAgain={(q) => { setQuery(q); void run(undefined, "ask", q); }} />
      {panel && <EvidencePanel chunkId={panel} onClose={closePanel} />}
    </main>
  );
}
