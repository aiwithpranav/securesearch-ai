"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { ApiError } from "@/lib/api";
import { resetPassword } from "@/lib/authApi";
import { logout } from "@/lib/session";
import { MESSAGES, tokenFromHash, validateConfirm, validateNewPassword } from "@/lib/validation";
import { FormErrorBox, PasswordField, SubmitButton } from "../_auth/ui";

function BadLink() {
  return (
    <div className="rounded-2xl border border-line bg-surface p-8">
      <h1 className="text-3xl font-semibold tracking-tight">Link not valid</h1>
      <p role="alert" className="mt-4 text-muted">{MESSAGES.resetLinkInvalid} Links work once and expire after a short time.</p>
      <Link href="/forgot-password" className="mt-8 inline-flex rounded-lg bg-accent px-5 py-3 font-medium text-bg hover:bg-accent2">
        Get a new link
      </Link>
    </div>
  );
}

export function ResetForm() {
  // undefined = not read yet, null = no token in the address, string = token
  const [token, setToken] = useState<string | null | undefined>(undefined);
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [pwError, setPwError] = useState<string | null>(null);
  const [confirmError, setConfirmError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);
  const [badLink, setBadLink] = useState(false);
  const pwRef = useRef<HTMLInputElement>(null);
  const confirmRef = useRef<HTMLInputElement>(null);

  // Read the token only once. In development React runs effects twice, and by then the
  // token has already been removed from the address, so we keep the first reading in a ref.
  const tokenRef = useRef<string | null | undefined>(undefined);
  useEffect(() => {
    function readToken() {
      const t = tokenFromHash(window.location.hash);
      if (t) {
        tokenRef.current = t;
        setBadLink(false);
        // Remove the token from the address bar and history so it is not left lying around.
        window.history.replaceState(null, "", window.location.pathname + window.location.search);
      } else if (tokenRef.current === undefined) {
        tokenRef.current = null; // opened without a token
      }
      setToken(tokenRef.current);
    }
    readToken();
    // Pasting a new link into a tab that is already on this page only changes the "#" part.
    window.addEventListener("hashchange", readToken);
    return () => window.removeEventListener("hashchange", readToken);
  }, []);

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (busy || !token) return;
    const pErr = validateNewPassword(password);
    const cErr = pErr ? null : validateConfirm(password, confirm);
    setPwError(pErr);
    setConfirmError(cErr);
    setFormError(null);
    if (pErr || cErr) {
      (pErr ? pwRef : confirmRef).current?.focus();
      return;
    }
    setBusy(true);
    try {
      await resetPassword(token, password);
      await logout(); // the server ended every session; make this browser forget its own too
      setDone(true);
    } catch (err) {
      setPassword("");
      setConfirm("");
      if (err instanceof ApiError && err.status === 400) setBadLink(true);
      else if (err instanceof ApiError && (err.status === 422 || err.status === 429 || err.isNetworkError)) {
        setFormError(err.status === 422 ? MESSAGES.newPasswordShort : err.message);
      } else setFormError(MESSAGES.generic);
    } finally {
      setBusy(false);
    }
  }

  if (token === undefined) return <p role="status" className="text-muted">Loading…</p>;
  if (token === null || badLink) return <BadLink />;

  if (done) {
    return (
      <div className="rounded-2xl border border-line bg-surface p-8">
        <h1 className="text-3xl font-semibold tracking-tight">Password updated</h1>
        <p role="status" className="mt-4 text-muted">Your new password is set. You were signed out on all devices.</p>
        <Link href="/login?notice=password-reset" className="mt-8 inline-flex rounded-lg bg-accent px-5 py-3 font-medium text-bg hover:bg-accent2">
          Go to sign in
        </Link>
      </div>
    );
  }

  return (
    <div className="rounded-2xl border border-line bg-surface p-8">
      <h1 className="text-3xl font-semibold tracking-tight">Set a new password</h1>
      <p className="mt-2 text-muted">Choose a password with at least 12 characters. A short sentence works well.</p>
      <div role="alert" className="sr-only">{pwError ?? confirmError ?? formError ?? ""}</div>
      {formError && <div className="mt-6"><FormErrorBox message={formError} /></div>}
      <form onSubmit={onSubmit} noValidate method="post" action="#" className="mt-6 space-y-5">
        <PasswordField
          ref={pwRef}
          id="new-password"
          name="new-password"
          label="New password"
          autoComplete="new-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          error={pwError}
          hint="At least 12 characters."
        />
        <PasswordField
          ref={confirmRef}
          id="confirm-password"
          name="confirm-password"
          label="Repeat new password"
          autoComplete="new-password"
          value={confirm}
          onChange={(e) => setConfirm(e.target.value)}
          error={confirmError}
        />
        <SubmitButton busy={busy} label="Set password" busyLabel="Saving…" />
      </form>
    </div>
  );
}
