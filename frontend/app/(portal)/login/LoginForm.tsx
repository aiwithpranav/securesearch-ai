"use client";

import { FormEvent, KeyboardEvent, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ApiError } from "@/lib/api";
import { login } from "@/lib/session";
import { MESSAGES, validateEmail, validatePassword } from "@/lib/validation";
import { useSession } from "../_auth/AuthProvider";

function ErrorIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 20 20" className="mt-0.5 h-4 w-4 shrink-0 fill-current">
      <path d="M10 1.5a8.5 8.5 0 1 0 0 17 8.5 8.5 0 0 0 0-17Zm-.9 4.5h1.8v5.2H9.1V6Zm0 6.7h1.8v1.8H9.1v-1.8Z" />
    </svg>
  );
}

function FieldError({ id, message }: { id: string; message: string }) {
  return (
    <p id={id} className="mt-2 flex items-start gap-2 text-sm text-bad">
      <ErrorIcon />
      <span>{message}</span>
    </p>
  );
}

const input = "w-full rounded-lg border bg-surface2 px-4 py-3 text-text placeholder:text-muted/60";

export function LoginForm() {
  const router = useRouter();
  const { status } = useSession();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [remember, setRemember] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [capsLock, setCapsLock] = useState(false);
  const [emailError, setEmailError] = useState<string | null>(null);
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [requestId, setRequestId] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [shaking, setShaking] = useState(false);

  const emailRef = useRef<HTMLInputElement>(null);
  const passwordRef = useRef<HTMLInputElement>(null);

  // Already signed in (or just signed in): go to the home page.
  useEffect(() => {
    if (status === "signed-in") router.replace("/home");
  }, [status, router]);

  function shake() {
    setShaking(true); // CSS animation; it is switched off for "reduce motion" users
  }

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (submitting) return;

    const eErr = validateEmail(email);
    const pErr = validatePassword(password);
    setEmailError(eErr);
    setPasswordError(pErr);
    setFormError(null);
    setRequestId(null);

    if (eErr || pErr) {
      shake();
      (eErr ? emailRef : passwordRef).current?.focus(); // focus the first problem
      return;
    }

    setSubmitting(true);
    try {
      await login(email.trim(), password, remember);
      // The effect above redirects once the session is set.
    } catch (err) {
      setPassword(""); // never keep a rejected password in the field
      shake();
      if (err instanceof ApiError) {
        if (err.status === 401) setFormError(MESSAGES.wrongCredentials);
        else if (err.status === 429) setFormError(err.message); // "Too many attempts. Try again in N minutes."
        else if (err.isNetworkError) setFormError(MESSAGES.network);
        else {
          setFormError(MESSAGES.generic);
          setRequestId(err.requestId ?? null);
        }
      } else {
        setFormError(MESSAGES.generic);
      }
      emailRef.current?.focus();
    } finally {
      setSubmitting(false);
    }
  }

  function trackCapsLock(e: KeyboardEvent<HTMLInputElement>) {
    setCapsLock(e.getModifierState("CapsLock"));
  }

  const errorSummary = emailError ?? passwordError ?? formError;

  return (
    <div
      className={`rounded-2xl border border-line bg-surface p-8 ${shaking ? "shake" : ""}`}
      onAnimationEnd={() => setShaking(false)}
    >
      <h1 className="text-3xl font-semibold tracking-tight">Welcome back</h1>
      <p className="mt-2 text-muted">Sign in to SecureSearch AI</p>

      {/* Screen readers hear the problem; sighted users see it inline. */}
      <div role="alert" className="sr-only">{errorSummary ?? ""}</div>

      {formError && (
        <div className="mt-6 flex items-start gap-2 rounded-lg border border-bad/60 bg-bad/10 p-3 text-sm text-bad">
          <ErrorIcon />
          <div>
            <p>{formError}</p>
            {requestId && <p className="mt-1 text-xs text-muted">Reference for support: {requestId}</p>}
          </div>
        </div>
      )}

      {/* A real form with proper autocomplete values, so browsers can offer to save the login. */}
      <form onSubmit={onSubmit} noValidate method="post" action="#" className="mt-6 space-y-5">
        <div>
          <label htmlFor="email" className="mb-2 block text-sm font-medium">Email</label>
          <input
            ref={emailRef}
            id="email"
            name="username"
            type="email"
            autoComplete="username"
            inputMode="email"
            autoCapitalize="none"
            spellCheck={false}
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            aria-invalid={emailError ? true : undefined}
            aria-describedby={emailError ? "email-error" : undefined}
            className={`${input} ${emailError ? "border-bad" : "border-line"}`}
            placeholder="name@company.com"
          />
          {emailError && <FieldError id="email-error" message={emailError} />}
        </div>

        <div>
          <div className="mb-2 flex items-center justify-between">
            <label htmlFor="password" className="text-sm font-medium">Password</label>
            <Link href="/forgot-password" className="text-sm text-accent2 hover:underline">Forgot password?</Link>
          </div>
          <div className="relative">
            <input
              ref={passwordRef}
              id="password"
              name="password"
              type={showPassword ? "text" : "password"}
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              onKeyDown={trackCapsLock}
              onKeyUp={trackCapsLock}
              onBlur={() => setCapsLock(false)}
              aria-invalid={passwordError ? true : undefined}
              aria-describedby={[passwordError ? "password-error" : "", capsLock ? "caps-hint" : ""].filter(Boolean).join(" ") || undefined}
              className={`${input} pr-20 ${passwordError ? "border-bad" : "border-line"}`}
            />
            <button
              type="button"
              onClick={() => setShowPassword((v) => !v)}
              aria-pressed={showPassword}
              aria-label={showPassword ? "Hide password" : "Show password"}
              className="absolute inset-y-0 right-2 my-auto h-9 rounded-md px-3 text-sm text-muted hover:text-text"
            >
              {showPassword ? "Hide" : "Show"}
            </button>
          </div>
          {passwordError && <FieldError id="password-error" message={passwordError} />}
          {capsLock && <p id="caps-hint" className="mt-2 text-sm text-muted">Caps Lock is on.</p>}
        </div>

        <label className="flex items-center gap-3 text-sm">
          <input
            type="checkbox"
            checked={remember}
            onChange={(e) => setRemember(e.target.checked)}
            className="h-4 w-4 accent-accent"
          />
          Remember me
        </label>

        <button
          type="submit"
          disabled={submitting}
          className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-accent px-5 py-3 font-medium text-bg hover:bg-accent2 disabled:cursor-not-allowed disabled:opacity-70"
        >
          {submitting && (
            <svg aria-hidden="true" viewBox="0 0 24 24" className="h-4 w-4 animate-spin motion-reduce:animate-none">
              <circle cx="12" cy="12" r="9" fill="none" stroke="currentColor" strokeWidth="3" opacity="0.3" />
              <path d="M21 12a9 9 0 0 0-9-9" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
            </svg>
          )}
          {submitting ? "Signing in…" : "Sign in"}
        </button>
      </form>
    </div>
  );
}
