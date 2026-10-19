"use client";

import { forwardRef, useState, type InputHTMLAttributes } from "react";

// Small shared pieces for the auth forms. Errors always show an icon AND text (never colour alone).

export function ErrorIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 20 20" className="mt-0.5 h-4 w-4 shrink-0 fill-current">
      <path d="M10 1.5a8.5 8.5 0 1 0 0 17 8.5 8.5 0 0 0 0-17Zm-.9 4.5h1.8v5.2H9.1V6Zm0 6.7h1.8v1.8H9.1v-1.8Z" />
    </svg>
  );
}

export function FieldError({ id, message }: { id: string; message: string }) {
  return (
    <p id={id} className="mt-2 flex items-start gap-2 text-sm text-bad">
      <ErrorIcon />
      <span>{message}</span>
    </p>
  );
}

export function FormErrorBox({ message, requestId }: { message: string; requestId?: string | null }) {
  return (
    <div className="flex items-start gap-2 rounded-lg border border-bad/60 bg-bad/10 p-3 text-sm text-bad">
      <ErrorIcon />
      <div>
        <p>{message}</p>
        {requestId && <p className="mt-1 text-xs text-muted">Reference for support: {requestId}</p>}
      </div>
    </div>
  );
}

export function NoticeBox({ message }: { message: string }) {
  return (
    <p role="status" className="rounded-lg border border-ok/60 bg-ok/10 p-3 text-sm text-ok">
      {message}
    </p>
  );
}

export function Spinner() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24" className="h-4 w-4 animate-spin motion-reduce:animate-none">
      <circle cx="12" cy="12" r="9" fill="none" stroke="currentColor" strokeWidth="3" opacity="0.3" />
      <path d="M21 12a9 9 0 0 0-9-9" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
    </svg>
  );
}

export function SubmitButton({ busy, label, busyLabel }: { busy: boolean; label: string; busyLabel: string }) {
  return (
    <button
      type="submit"
      disabled={busy}
      className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-accent px-5 py-3 font-medium text-bg hover:bg-accent2 disabled:cursor-not-allowed disabled:opacity-70"
    >
      {busy && <Spinner />}
      {busy ? busyLabel : label}
    </button>
  );
}

export const inputClass = "w-full rounded-lg border bg-surface2 px-4 py-3 text-text placeholder:text-muted/60";

type TextFieldProps = InputHTMLAttributes<HTMLInputElement> & { label: string; error?: string | null; hint?: string };

/** Label + input + inline error. Pass ref to focus it on errors. */
export const TextField = forwardRef<HTMLInputElement, TextFieldProps>(function TextField(
  { label, error, hint, id, className = "", ...rest },
  ref,
) {
  const hintId = hint ? `${id}-hint` : undefined;
  const errorId = error ? `${id}-error` : undefined;
  return (
    <div>
      <label htmlFor={id} className="mb-2 block text-sm font-medium">{label}</label>
      <input
        ref={ref}
        id={id}
        aria-invalid={error ? true : undefined}
        aria-describedby={[errorId, hintId].filter(Boolean).join(" ") || undefined}
        className={`${inputClass} ${error ? "border-bad" : "border-line"} ${className}`}
        {...rest}
      />
      {hint && !error && <p id={hintId} className="mt-2 text-sm text-muted">{hint}</p>}
      {error && <FieldError id={errorId!} message={error} />}
    </div>
  );
});

/** Password input with a Show/Hide button. */
export const PasswordField = forwardRef<HTMLInputElement, TextFieldProps>(function PasswordField(props, ref) {
  const [show, setShow] = useState(false);
  const { label, error, hint, id, ...rest } = props;
  const hintId = hint ? `${id}-hint` : undefined;
  const errorId = error ? `${id}-error` : undefined;
  return (
    <div>
      <label htmlFor={id} className="mb-2 block text-sm font-medium">{label}</label>
      <div className="relative">
        <input
          ref={ref}
          id={id}
          type={show ? "text" : "password"}
          aria-invalid={error ? true : undefined}
          aria-describedby={[errorId, hintId].filter(Boolean).join(" ") || undefined}
          className={`${inputClass} pr-20 ${error ? "border-bad" : "border-line"}`}
          {...rest}
        />
        <button
          type="button"
          onClick={() => setShow((v) => !v)}
          aria-pressed={show}
          aria-label={show ? `Hide ${label.toLowerCase()}` : `Show ${label.toLowerCase()}`}
          className="absolute inset-y-0 right-2 my-auto h-9 rounded-md px-3 text-sm text-muted hover:text-text"
        >
          {show ? "Hide" : "Show"}
        </button>
      </div>
      {hint && !error && <p id={hintId} className="mt-2 text-sm text-muted">{hint}</p>}
      {error && <FieldError id={errorId!} message={error} />}
    </div>
  );
});
