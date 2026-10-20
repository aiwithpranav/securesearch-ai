"use client";

import { useEffect, useRef } from "react";

/** Calls `callback` every `intervalMs` while `enabled` is true. Skips ticks while the tab is hidden. */
export function usePolling(callback: () => void | Promise<void>, intervalMs: number, enabled: boolean): void {
  const saved = useRef(callback);
  useEffect(() => {
    saved.current = callback;
  }, [callback]);

  useEffect(() => {
    if (!enabled) return;
    const id = setInterval(() => {
      if (typeof document !== "undefined" && document.hidden) return;
      void saved.current();
    }, intervalMs);
    return () => clearInterval(id);
  }, [intervalMs, enabled]);
}
