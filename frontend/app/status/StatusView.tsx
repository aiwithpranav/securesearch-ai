"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { checkedText, componentHint, EXPLAIN, fetchStatus, HEADLINE, viewOf, type ServiceStatus } from "@/lib/status";
import { usePolling } from "@/lib/usePolling";

const TONE = {
  operational: "border-ok/60 text-ok",
  degraded: "border-accent2/60 text-accent2",
  down: "border-bad/60 text-bad",
  unreachable: "border-bad/60 text-bad",
} as const;

function Icon({ up }: { up: boolean }) {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24" className="h-4 w-4 shrink-0">
      <path d={up ? "M5 12.5l4.5 4.5L19 7.5" : "M6 6l12 12M18 6L6 18"} fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function StatusView() {
  const [status, setStatus] = useState<ServiceStatus | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [now, setNow] = useState(() => Date.now());

  const load = useCallback(async () => {
    setStatus(await fetchStatus());
    setLoaded(true);
    setNow(Date.now());
  }, []);
  useEffect(() => {
    let live = true;
    fetchStatus().then((s) => {
      if (!live) return;
      setStatus(s);
      setLoaded(true);
    });
    return () => { live = false; };
  }, []);
  usePolling(load, 30_000, true);
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 5000);
    return () => clearInterval(id);
  }, []);

  const view = viewOf(status);
  return (
    <main id="main" className="mx-auto min-h-screen w-full max-w-2xl px-5 py-16">
      <Link href="/" className="text-sm text-accent2 underline underline-offset-4">Back to home</Link>
      <h1 className="mt-6 text-4xl font-semibold tracking-tight">Status</h1>

      {!loaded ? (
        <div role="status" aria-label="Checking the service" className="mt-8 h-32 animate-pulse rounded-2xl bg-surface motion-reduce:animate-none" />
      ) : (
        <>
          <section aria-live="polite" className={`mt-8 rounded-2xl border bg-surface p-6 ${TONE[view]}`}>
            <p className="flex items-center gap-2 text-xl font-semibold"><Icon up={view === "operational"} />{HEADLINE[view]}</p>
            <p className="mt-2 text-sm text-muted">{EXPLAIN[view]}</p>
          </section>

          {status && (
            <ul className="mt-6 divide-y divide-line rounded-2xl border border-line bg-surface">
              {status.components.map((c) => (
                <li key={c.name} className="flex items-center justify-between gap-4 p-4">
                  <div>
                    <p className="font-medium">{c.name}</p>
                    <p className="text-sm text-muted">{componentHint(c.name)}</p>
                  </div>
                  <span className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-sm ${c.status === "up" ? "border-ok/60 text-ok" : "border-bad/60 text-bad"}`}>
                    <Icon up={c.status === "up"} />{c.status === "up" ? "Working" : "Not working"}
                  </span>
                </li>
              ))}
            </ul>
          )}
          <p className="mt-4 text-xs text-muted">
            {status ? `Checked ${checkedText(status.checked_at, now)}. ` : ""}This page refreshes by itself every 30 seconds.
          </p>
        </>
      )}
    </main>
  );
}
