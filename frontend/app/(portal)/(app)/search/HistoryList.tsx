"use client";

import { useCallback, useEffect, useState } from "react";
import { ageText, deleteHistoryItem, listHistory, statusText, type HistoryItem } from "@/lib/chat";

// Your own recent questions. Only the question is kept (never the answer), so asking again writes a fresh answer from
// what you may read today. Items can be removed one by one.
export function HistoryList({ refreshKey, onAskAgain }: { refreshKey: number; onAskAgain: (question: string) => void }) {
  const [items, setItems] = useState<HistoryItem[] | null>(null);
  const [confirm, setConfirm] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setItems((await listHistory(10)).items);
      setError(null);
    } catch {
      setError("Your recent questions could not be loaded.");
    }
  }, []);

  useEffect(() => { void load(); }, [load, refreshKey]);

  async function remove(id: string) {
    try {
      await deleteHistoryItem(id);
      setConfirm(null);
      await load();
    } catch {
      setError("That question could not be removed.");
    }
  }

  if (items === null && !error) return null;
  if (items && items.length === 0 && !error) return null;
  return (
    <section className="mt-12" aria-labelledby="history-title">
      <h2 id="history-title" className="text-xl font-semibold">Your recent questions</h2>
      {error && <p role="alert" className="mt-3 text-sm text-bad">{error}</p>}
      <ul className="mt-4 divide-y divide-line rounded-2xl border border-line bg-surface">
        {(items ?? []).map((h) => (
          <li key={h.id} className="flex flex-wrap items-center justify-between gap-3 px-5 py-3">
            <div className="min-w-0 flex-1">
              <p className="break-words font-medium">{h.question}</p>
              <p className="text-xs text-muted">{statusText(h.status)} · {ageText(h.created_at)}</p>
            </div>
            {confirm === h.id ? (
              <span className="flex items-center gap-2 text-sm" role="group" aria-label="Confirm remove">
                Remove this question?
                <button type="button" autoFocus onClick={() => void remove(h.id)} className="rounded-lg bg-bad px-3 py-1.5 font-medium text-bg">Yes</button>
                <button type="button" onClick={() => setConfirm(null)} className="rounded-lg border border-line px-3 py-1.5">No</button>
              </span>
            ) : (
              <span className="flex gap-2">
                <button type="button" onClick={() => onAskAgain(h.question)} aria-label={`Ask again: ${h.question}`} className="rounded-lg border border-line px-3 py-1.5 text-sm hover:border-accent2">Ask again</button>
                <button type="button" onClick={() => setConfirm(h.id)} aria-label={`Remove: ${h.question}`} className="rounded-lg border border-line px-3 py-1.5 text-sm hover:border-bad/60">Remove</button>
              </span>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}
