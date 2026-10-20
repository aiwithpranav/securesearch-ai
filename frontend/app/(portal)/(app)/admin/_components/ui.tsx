"use client";

import Link from "next/link";
import type { JobStatus } from "@/lib/documents";
import { STATUS_LABELS } from "@/lib/documents";

// Small shared pieces for the admin screens. Colour is never the only signal: every badge has text.

const STATUS_STYLE: Record<JobStatus, string> = {
  QUEUED: "border-line text-muted",
  PROCESSING: "border-accent2/60 text-accent2",
  READY: "border-ok/60 text-ok",
  FAILED: "border-bad/60 text-bad",
};

function StatusIcon({ status }: { status: JobStatus }) {
  if (status === "PROCESSING") {
    return (
      <svg aria-hidden="true" viewBox="0 0 24 24" className="h-3.5 w-3.5 animate-spin motion-reduce:animate-none">
        <circle cx="12" cy="12" r="9" fill="none" stroke="currentColor" strokeWidth="3" opacity="0.3" />
        <path d="M21 12a9 9 0 0 0-9-9" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
      </svg>
    );
  }
  const path = {
    QUEUED: "M12 6v6l4 2",
    READY: "M5 12.5l4.5 4.5L19 7.5",
    FAILED: "M6 6l12 12M18 6L6 18",
  }[status];
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24" className="h-3.5 w-3.5">
      <path d={path} fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function StatusBadge({ status }: { status: JobStatus }) {
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium ${STATUS_STYLE[status]}`}>
      <StatusIcon status={status} />
      {STATUS_LABELS[status]}
    </span>
  );
}

export function SensitivityBadge({ level, name }: { level: number; name: string }) {
  return (
    <span className="inline-flex rounded-full border border-line bg-surface2 px-2.5 py-0.5 text-xs">
      {level} · {name.replace("_", " ")}
    </span>
  );
}

export function TableSkeleton({ rows = 5 }: { rows?: number }) {
  return (
    <div role="status" aria-label="Loading documents" className="space-y-3">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="h-12 animate-pulse rounded-lg bg-surface motion-reduce:animate-none" />
      ))}
    </div>
  );
}

export function EmptyState({ title, text, action }: { title: string; text: string; action?: { href: string; label: string } }) {
  return (
    <div className="rounded-2xl border border-dashed border-line p-10 text-center">
      <h2 className="text-xl font-semibold">{title}</h2>
      <p className="mx-auto mt-2 max-w-md text-muted">{text}</p>
      {action && (
        <Link href={action.href} className="mt-6 inline-flex rounded-lg bg-accent px-5 py-3 font-medium text-bg hover:bg-accent2">
          {action.label}
        </Link>
      )}
    </div>
  );
}

export function ErrorState({ message, requestId, onRetry }: { message: string; requestId?: string; onRetry?: () => void }) {
  return (
    <div role="alert" className="rounded-2xl border border-bad/60 bg-bad/10 p-6">
      <p className="font-medium text-bad">{message}</p>
      {requestId && <p className="mt-1 text-xs text-muted">Reference for support: {requestId}</p>}
      {onRetry && (
        <button type="button" onClick={onRetry} className="mt-4 rounded-lg border border-line px-4 py-2 text-sm hover:border-accent2">
          Try again
        </button>
      )}
    </div>
  );
}

export function NoAccess() {
  return (
    <main id="main" className="mx-auto w-full max-w-xl px-5 py-20">
      <h1 className="text-3xl font-semibold tracking-tight">You don&apos;t have access to this page</h1>
      <p className="mt-3 text-muted">If you think this is a mistake, ask an administrator.</p>
      <Link href="/home" className="mt-8 inline-flex rounded-lg border border-line px-5 py-3 hover:border-accent2">
        Back to home
      </Link>
    </main>
  );
}

export const selectClass = "w-full rounded-lg border border-line bg-surface2 px-4 py-3 text-text";
