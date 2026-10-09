"use client";

import { useEffect, useRef, useState } from "react";
import { motion, useReducedMotion, AnimatePresence } from "motion/react";
import { AnimatedButton } from "./AnimatedButton";

const steps = [
  { title: "You ask", desc: "Type a question in your own words." },
  { title: "We check your access", desc: "Your permissions are read from the database, fresh, on every search." },
  { title: "We search only what you may read", desc: "Documents you cannot read are never searched, scored or shown to the AI." },
  { title: "You get an answer with sources", desc: "Every answer names its document and section. If nothing readable fits, it says so." },
];

export function TourDialog({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const [step, setStep] = useState(0);
  const prefersReducedMotion = useReducedMotion();

  useEffect(() => {
    const dialog = dialogRef.current;
    if (isOpen && dialog && !dialog.open) {
      dialog.showModal();
      setStep(0);
    }
  }, [isOpen]);

  useEffect(() => {
    const dialog = dialogRef.current;
    const handleCancel = (e: Event) => {
      e.preventDefault();
      onClose();
    };
    if (dialog) {
      dialog.addEventListener("cancel", handleCancel);
      return () => dialog.removeEventListener("cancel", handleCancel);
    }
  }, [onClose]);

  const handleBackdropClick = (e: React.MouseEvent<HTMLDialogElement>) => {
    if (e.target === dialogRef.current) {
      onClose();
    }
  };

  return (
    <dialog
      ref={dialogRef}
      onClick={handleBackdropClick}
      className="backdrop:bg-bg/80 backdrop:backdrop-blur-sm bg-transparent p-0 m-auto fixed inset-0 z-50 open:flex items-center justify-center"
      aria-labelledby="tour-title"
      aria-describedby="tour-desc"
    >
      <AnimatePresence onExitComplete={() => {
        if (dialogRef.current?.open) {
          dialogRef.current.close();
        }
      }}>
        {isOpen && (
          <motion.div
            className="w-full max-w-md rounded-2xl border border-line bg-surface p-6 shadow-xl relative"
            initial={prefersReducedMotion ? { opacity: 1, scale: 1 } : { opacity: 0, scale: 0.95, y: 10 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={prefersReducedMotion ? { opacity: 0, scale: 1 } : { opacity: 0, scale: 0.95, y: 10 }}
            transition={{ duration: 0.2 }}
            onClick={(e) => e.stopPropagation()} // prevent backdrop click
          >
            <button
              onClick={onClose}
              className="absolute right-4 top-4 rounded-md p-1 text-muted hover:bg-surface2 hover:text-text focus:outline-none focus:ring-2 focus:ring-accent"
              aria-label="Close tour"
            >
              ✕
            </button>
            <div className="mb-8 mt-2">
              <p className="text-sm font-medium text-accent2 mb-2">Step {step + 1} of {steps.length}</p>
              <h2 id="tour-title" className="text-2xl font-semibold text-text">{steps[step].title}</h2>
              <p id="tour-desc" className="mt-4 text-muted">{steps[step].desc}</p>
            </div>
            
            <div className="flex items-center justify-between mt-8 border-t border-line pt-4">
              <AnimatedButton
                onClick={() => {
                  if (step > 0) setStep((s) => s - 1);
                }}
                className={`rounded-lg px-4 py-2 font-medium text-muted hover:bg-surface2 ${step === 0 ? "opacity-50 pointer-events-none" : ""}`}
              >
                Back
              </AnimatedButton>
              <AnimatedButton
                onClick={() => {
                  if (step < steps.length - 1) {
                    setStep((s) => s + 1);
                  } else {
                    onClose();
                  }
                }}
                className="rounded-lg bg-accent px-5 py-2 font-medium text-bg hover:bg-accent2"
              >
                {step === steps.length - 1 ? "Finish" : "Next"}
              </AnimatedButton>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </dialog>
  );
}
