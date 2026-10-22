"use client";

import { useCallback, useEffect, useState } from "react";
import { ApiError } from "@/lib/api";
import { ageText } from "@/lib/chat";
import { getGaps, type Gap } from "@/lib/dashboards";
import { EmptyState, ErrorState, TableSkeleton } from "../admin/_components/ui";

export function GapsView() {
  const [gaps, setGaps] = useState<{ window_days: number; items: Gap[] } | null>(null);
  const [error, setError] = useState<{ message: string; requestId?: string } | null>(null);

  const load = useCallback(async () => {
    try {
      setGaps(await getGaps());
      setError(null);
    } catch (e) {
      setError({ message: "The report could not be loaded.", requestId: e instanceof ApiError ? e.requestId : undefined });
    }
  }, []);
  useEffect(() => { void load(); }, [load]);

  return (
    <main id="main" className="mx-auto w-full max-w-4xl px-5 py-10">
      <h1 className="text-3xl font-semibold tracking-tight">Knowledge gaps</h1>
      <p className="mt-2 max-w-2xl text-muted">
        Questions people asked that could not be answered, most frequent first. Similar questions are counted together, personal details such as emails, links and long numbers are hidden, and nobody is named.
      </p>
      <div className="mt-8">
        {error ? <ErrorState message={error.message} requestId={error.requestId} onRetry={() => void load()} />
          : !gaps ? <TableSkeleton rows={4} />
          : gaps.items.length === 0 ? <EmptyState title="No gaps in the last 30 days" text="Every question was either answered or has not been asked yet." />
          : (
            <ol className="space-y-3">
              {gaps.items.map((g) => (
                <li key={g.question} className="rounded-2xl border border-line bg-surface p-5">
                  <p className="break-words text-lg font-medium">&ldquo;{g.question}&rdquo;</p>
                  <p className="mt-2 text-sm text-muted">
                    Asked <b className="text-text">{g.asked}</b> {g.asked === 1 ? "time" : "times"} by <b className="text-text">{g.people}</b> {g.people === 1 ? "person" : "people"} · last {ageText(g.last_asked)}
                  </p>
                  <p className="mt-2 text-sm">{g.suggested_action}</p>
                </li>
              ))}
            </ol>
          )}
      </div>
    </main>
  );
}
