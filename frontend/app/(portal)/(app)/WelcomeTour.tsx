"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { hasSeenTour, markTourSeen, OPEN_TOUR_EVENT } from "@/lib/tour";
import { useSession } from "../_auth/AuthProvider";

// Blueprint 19.1: a 3-step skippable tour: ask, check sources, rate.
const STEPS = [
  { title: "Ask in your own words", text: "Type a question the way you would ask a colleague. Use Search in the menu to find passages in the documents you may read. Written answers with sources arrive in a later phase." },
  { title: "Check the sources", text: "Every answer will name the document and section it came from. Open the source to read the original text yourself." },
  { title: "Rate the answer", text: "Tell us with a thumbs up or down whether the answer helped. Your rating helps improve what the team finds." },
];

/** Opens by itself the first time a person arrives, and again when they ask for it. */
export function WelcomeTour() {
  const { user } = useSession();
  const userId = user?.id;
  const dialogRef = useRef<HTMLDialogElement>(null);
  const [step, setStep] = useState(0);

  const open = useCallback(() => {
    const d = dialogRef.current;
    if (d && !d.open) {
      setStep(0);
      d.showModal(); // native modal: Esc closes it, focus stays inside
    }
  }, []);

  // First visit: open automatically, once per person per browser.
  useEffect(() => {
    if (userId && !hasSeenTour(userId)) open();
  }, [userId, open]);

  // "Take the tour again" button on the home page.
  useEffect(() => {
    window.addEventListener(OPEN_TOUR_EVENT, open);
    return () => window.removeEventListener(OPEN_TOUR_EVENT, open);
  }, [open]);

  // Any way of closing (Done, Skip, Esc) counts as "seen".
  function onClose() {
    if (userId) markTourSeen(userId);
  }

  const last = step === STEPS.length - 1;
  const current = STEPS[step];

  return (
    <dialog
      ref={dialogRef}
      onClose={onClose}
      aria-labelledby="tour-title"
      className="m-auto w-[calc(100%-2.5rem)] max-w-md rounded-2xl border border-line bg-surface p-6 text-text backdrop:bg-bg/80"
    >
      <p className="text-sm text-muted" aria-live="polite">Step {step + 1} of {STEPS.length}</p>
      <h2 id="tour-title" className="mt-2 text-2xl font-semibold">{current.title}</h2>
      <p className="mt-3 text-muted">{current.text}</p>

      <div className="mt-6 flex items-center justify-between gap-3">
        <button
          type="button"
          onClick={() => dialogRef.current?.close()}
          className="rounded-lg px-3 py-2 text-sm text-muted hover:text-text"
        >
          Skip tour
        </button>
        <div className="flex gap-2">
          {step > 0 && (
            <button type="button" onClick={() => setStep(step - 1)} className="rounded-lg border border-line px-4 py-2 text-sm hover:border-accent2">
              Back
            </button>
          )}
          <button
            type="button"
            autoFocus
            onClick={() => (last ? dialogRef.current?.close() : setStep(step + 1))}
            className="rounded-lg bg-accent px-4 py-2 text-sm font-medium text-bg hover:bg-accent2"
          >
            {last ? "Done" : "Next"}
          </button>
        </div>
      </div>
    </dialog>
  );
}
