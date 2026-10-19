"use client";

import { FormEvent, useRef, useState } from "react";
import Link from "next/link";
import { ApiError } from "@/lib/api";
import { forgotPassword } from "@/lib/authApi";
import { MESSAGES, validateEmail } from "@/lib/validation";
import { FormErrorBox, SubmitButton, TextField } from "../_auth/ui";

export function ForgotForm() {
  const [email, setEmail] = useState("");
  const [emailError, setEmailError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState(false);
  const emailRef = useRef<HTMLInputElement>(null);

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (busy) return;
    const err = validateEmail(email);
    setEmailError(err);
    setFormError(null);
    if (err) {
      emailRef.current?.focus();
      return;
    }
    setBusy(true);
    try {
      await forgotPassword(email.trim());
      setSent(true); // same screen whether or not the account exists
    } catch (e2) {
      if (e2 instanceof ApiError && (e2.status === 429 || e2.isNetworkError)) setFormError(e2.message);
      else setFormError(MESSAGES.generic);
    } finally {
      setBusy(false);
    }
  }

  if (sent) {
    return (
      <div className="rounded-2xl border border-line bg-surface p-8">
        <h1 className="text-3xl font-semibold tracking-tight">Check your email</h1>
        <p role="status" className="mt-4 text-muted">
          If that account exists, a reset link has been sent. The link works once and expires in 30 minutes.
        </p>
        <p className="mt-4 text-sm text-muted">Nothing arrived? Check your spam folder, or try again in a few minutes.</p>
        <Link href="/login" className="mt-8 inline-flex rounded-lg border border-line px-5 py-3 hover:border-accent2">Back to sign in</Link>
      </div>
    );
  }

  return (
    <div className="rounded-2xl border border-line bg-surface p-8">
      <h1 className="text-3xl font-semibold tracking-tight">Forgot your password?</h1>
      <p className="mt-2 text-muted">Enter your email and we will send you a link to set a new one.</p>
      <div role="alert" className="sr-only">{emailError ?? formError ?? ""}</div>
      {formError && <div className="mt-6"><FormErrorBox message={formError} /></div>}
      <form onSubmit={onSubmit} noValidate method="post" action="#" className="mt-6 space-y-5">
        <TextField
          ref={emailRef}
          id="email"
          name="username"
          label="Email"
          type="email"
          autoComplete="username"
          inputMode="email"
          autoCapitalize="none"
          spellCheck={false}
          placeholder="name@company.com"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          error={emailError}
        />
        <SubmitButton busy={busy} label="Send reset link" busyLabel="Sending…" />
      </form>
    </div>
  );
}
