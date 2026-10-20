"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { failureReason, listNotifications, markNotificationRead, type NotificationItem } from "@/lib/documents";
import { usePolling } from "@/lib/usePolling";

/** Bell with the number of unread alerts (FR-33: failed ingestion). Shown to administrators only. */
export function NotificationBell() {
  const [items, setItems] = useState<NotificationItem[]>([]);
  const [open, setOpen] = useState(false);
  const [failed, setFailed] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  const load = useCallback(async () => {
    try {
      setItems(await listNotifications(false));
      setFailed(false);
    } catch {
      setFailed(true);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);
  usePolling(load, 30_000, true);

  // Close with Escape or a click outside.
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    const onClick = (e: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("keydown", onKey);
    document.addEventListener("mousedown", onClick);
    return () => {
      document.removeEventListener("keydown", onKey);
      document.removeEventListener("mousedown", onClick);
    };
  }, [open]);

  const unread = items.filter((n) => n.read_at === null).length;

  async function markRead(id: string) {
    try {
      const updated = await markNotificationRead(id);
      setItems((cur) => cur.map((n) => (n.id === id ? updated : n)));
    } catch {
      /* the next refresh shows the real state */
    }
  }

  return (
    <div ref={rootRef} className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        aria-controls="notif-panel"
        aria-label={unread > 0 ? `Notifications, ${unread} unread` : "Notifications"}
        className="relative rounded-lg px-3 py-2 text-muted hover:text-text"
      >
        <svg aria-hidden="true" viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M6 9a6 6 0 1 1 12 0c0 5 2 6 2 6H4s2-1 2-6" />
          <path d="M10 19a2 2 0 0 0 4 0" />
        </svg>
        {unread > 0 && (
          <span className="absolute -right-0.5 -top-0.5 min-w-[1.1rem] rounded-full bg-bad px-1 text-center text-[11px] font-semibold leading-[1.1rem] text-bg">
            {unread}
          </span>
        )}
      </button>

      {open && (
        <div id="notif-panel" className="absolute right-0 z-40 mt-2 w-80 max-w-[calc(100vw-2rem)] rounded-2xl border border-line bg-surface p-3 shadow-xl">
          <h2 className="px-2 pb-2 text-sm font-semibold">Notifications</h2>
          {failed && <p className="px-2 pb-2 text-sm text-bad">Notifications could not be loaded.</p>}
          {items.length === 0 && !failed ? (
            <p className="px-2 py-4 text-sm text-muted">You have no notifications.</p>
          ) : (
            <ul className="max-h-80 space-y-2 overflow-y-auto">
              {items.map((n) => {
                const docId = typeof n.payload.document_id === "string" ? n.payload.document_id : null;
                const code = typeof n.payload.error_code === "string" ? n.payload.error_code : null;
                return (
                  <li key={n.id} className={`rounded-lg border p-3 text-sm ${n.read_at ? "border-line text-muted" : "border-bad/50"}`}>
                    <p className="font-medium">{n.kind === "INGESTION_FAILED" ? "A document failed to process" : "Notification"}</p>
                    {n.kind === "INGESTION_FAILED" && <p className="mt-1 text-muted">{failureReason(code)}</p>}
                    <div className="mt-2 flex items-center gap-3">
                      {docId && <Link href={`/admin/documents/${docId}`} onClick={() => setOpen(false)} className="text-accent2 hover:underline">View document</Link>}
                      {!n.read_at && <button type="button" onClick={() => void markRead(n.id)} className="text-muted hover:text-text">Mark as read</button>}
                    </div>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
