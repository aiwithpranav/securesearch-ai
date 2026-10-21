"use client";

import { useEffect, useRef, useState } from "react";
import { ApiError } from "@/lib/api";
import { getPassage, type Passage } from "@/lib/chat";
import { whereText } from "@/lib/search";

// The passage behind a citation. A side panel on a laptop, a bottom sheet on a phone. The server checks READ again
// every time, so a passage that is no longer allowed simply is not shown.
export function EvidencePanel({ chunkId, onClose }: { chunkId: string; onClose: () => void }) {
  const [passage, setPassage] = useState<Passage | null>(null);
  const [error, setError] = useState<string | null>(null);
  const closeRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    let alive = true;
    setPassage(null);
    setError(null);
    getPassage(chunkId)
      .then((p) => alive && setPassage(p))
      .catch((e) => alive && setError(e instanceof ApiError && e.status === 404 ? "This passage is no longer available." : "The passage could not be loaded. Please try again."));
    return () => { alive = false; };
  }, [chunkId]);

  useEffect(() => {
    closeRef.current?.focus();
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const where = passage ? whereText(passage) : "";
  const updated = passage?.document_updated_at ? new Date(passage.document_updated_at).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" }) : null;

  return (
    <div className="fixed inset-0 z-50" role="presentation">
      <div className="absolute inset-0 bg-black/60" onClick={onClose} aria-hidden="true" />
      <aside
        role="dialog" aria-modal="true" aria-labelledby="evidence-title"
        className="absolute inset-x-0 bottom-0 max-h-[85vh] overflow-y-auto rounded-t-2xl border border-line bg-surface p-6 sm:inset-y-0 sm:left-auto sm:right-0 sm:max-h-none sm:w-[28rem] sm:rounded-none sm:rounded-l-2xl"
      >
        <div className="flex items-start justify-between gap-3">
          <h2 id="evidence-title" className="text-lg font-semibold">{passage ? passage.document_title : "Source passage"}</h2>
          <button ref={closeRef} type="button" onClick={onClose} className="rounded-lg border border-line px-3 py-1.5 text-sm hover:border-accent2">Close</button>
        </div>
        <div aria-live="polite">
          {!passage && !error && <p className="mt-6 text-muted">Loading…</p>}
          {error && <p role="alert" className="mt-6 text-bad">{error}</p>}
          {passage && (
            <>
              {(where || updated) && <p className="mt-1 text-sm text-muted">{[where, updated && `Updated ${updated}`].filter(Boolean).join(" · ")}</p>}
              <p className="mt-5 whitespace-pre-line break-words">{passage.content}</p>
            </>
          )}
        </div>
      </aside>
    </div>
  );
}
