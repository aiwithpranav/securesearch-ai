"use client";

import { FormEvent, useState } from "react";
import { sendFeedback, splitAnswer, type ChatResult } from "@/lib/chat";
import { whereText } from "@/lib/search";

function Thumbs({ historyId }: { historyId: string }) {
  const [rating, setRating] = useState<"UP" | "DOWN" | null>(null);
  const [comment, setComment] = useState("");
  const [state, setState] = useState<"idle" | "saving" | "saved" | "error">("idle");

  async function rate(value: "UP" | "DOWN") {
    setRating(value);
    setState("saving");
    try {
      await sendFeedback(historyId, value);
      setState("saved");
    } catch {
      setState("error");
    }
  }
  async function sendComment(e: FormEvent) {
    e.preventDefault();
    if (!rating || !comment.trim()) return;
    setState("saving");
    try {
      await sendFeedback(historyId, rating, comment);
      setComment("");
      setState("saved");
    } catch {
      setState("error");
    }
  }
  const btn = (value: "UP" | "DOWN", label: string) => (
    <button
      type="button" aria-pressed={rating === value} onClick={() => void rate(value)}
      className={`rounded-lg border px-3 py-1.5 text-sm ${rating === value ? "border-accent bg-accent/15 text-text" : "border-line text-muted hover:border-accent2 hover:text-text"}`}
    >
      {label}
    </button>
  );
  return (
    <div className="mt-5 border-t border-line pt-4">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-sm text-muted">Was this helpful?</span>
        {btn("UP", "Yes")}
        {btn("DOWN", "No")}
        <span role="status" className="text-sm text-muted">
          {state === "saved" && "Thanks for the feedback."}
          {state === "error" && "Your feedback could not be saved."}
        </span>
      </div>
      {rating && (
        <form onSubmit={sendComment} className="mt-3 flex flex-wrap gap-2">
          <label htmlFor="fb-comment" className="sr-only">Tell us more (optional)</label>
          <input
            id="fb-comment" value={comment} maxLength={500} placeholder="Tell us more (optional)"
            onChange={(e) => setComment(e.target.value)}
            className="min-w-[12rem] flex-1 rounded-lg border border-line bg-surface2 px-3 py-2 text-sm text-text"
          />
          <button type="submit" disabled={!comment.trim() || state === "saving"} className="rounded-lg border border-line px-3 py-2 text-sm hover:border-accent2 disabled:opacity-60">Send</button>
        </form>
      )}
    </div>
  );
}

// The answer, its sources and the "was this helpful" buttons.
export function AnswerCard({ result, onOpen }: { result: ChatResult; onOpen: (chunkId: string, trigger: HTMLElement) => void }) {
  const known = result.citations.map((c) => c.source_id);
  const parts = splitAnswer(result.answer ?? "", known);
  return (
    <article className="rounded-2xl border border-line bg-surface p-6" aria-labelledby="answer-title">
      <h2 id="answer-title" className="text-sm font-medium uppercase tracking-wide text-muted">Answer</h2>
      <p className="mt-3 text-lg leading-relaxed">
        {parts.map((p, i) =>
          p.kind === "text" ? (
            <span key={i}>{p.value}</span>
          ) : (
            <sup key={i} className="mx-0.5 rounded bg-accent/20 px-1 text-xs font-medium text-accent2" title={`Source ${p.id}`}>{p.id}</sup>
          ),
        )}
      </p>

      <h3 className="mt-6 text-sm font-medium uppercase tracking-wide text-muted">Sources</h3>
      <ul className="mt-3 space-y-3">
        {result.citations.map((c) => {
          const where = whereText(c);
          return (
            <li key={c.chunk_id} className="rounded-xl border border-line bg-surface2 p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="font-medium"><span className="mr-2 rounded bg-accent/20 px-1.5 py-0.5 text-xs text-accent2">{c.source_id}</span>{c.document_title}</p>
                  {where && <p className="mt-0.5 text-sm text-muted">{where}</p>}
                </div>
                <button
                  type="button" onClick={(e) => onOpen(c.chunk_id, e.currentTarget)}
                  aria-label={`View passage from ${c.document_title}`} className="rounded-lg border border-line px-3 py-1.5 text-sm hover:border-accent2"
                >
                  View passage
                </button>
              </div>
              <p className="mt-2 break-words text-sm text-muted">{c.snippet}</p>
            </li>
          );
        })}
      </ul>
      {result.history_id && <Thumbs historyId={result.history_id} />}
    </article>
  );
}
