"use client";

import { FormEvent, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { ApiError } from "@/lib/api";
import { changePassword, logoutAll } from "@/lib/session";
import { MESSAGES, validateConfirm, validateCurrentPassword, validateNewPassword } from "@/lib/validation";
import { useSession } from "../../_auth/AuthProvider";
import { FormErrorBox, PasswordField, SubmitButton } from "../../_auth/ui";

const card = "rounded-2xl border border-line bg-surface p-6";

function ChangePasswordCard() {
  const router = useRouter();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [curErr, setCurErr] = useState<string | null>(null);
  const [nextErr, setNextErr] = useState<string | null>(null);
  const [confirmErr, setConfirmErr] = useState<string | null>(null);
  const [formErr, setFormErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const curRef = useRef<HTMLInputElement>(null);
  const nextRef = useRef<HTMLInputElement>(null);
  const confirmRef = useRef<HTMLInputElement>(null);

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (busy) return;
    const c = validateCurrentPassword(current);
    const n = validateNewPassword(next);
    const f = n ? null : validateConfirm(next, confirm);
    setCurErr(c);
    setNextErr(n);
    setConfirmErr(f);
    setFormErr(null);
    if (c || n || f) {
      (c ? curRef : n ? nextRef : confirmRef).current?.focus();
      return;
    }
    setBusy(true);
    try {
      await changePassword(current, next);
      // The server ended every session, including this one. The guard now sends us to /login,
      // where the "password changed" notice is shown.
      router.replace("/login");
    } catch (err) {
      setBusy(false);
      if (err instanceof ApiError && err.status === 400) {
        setCurErr("Current password is incorrect.");
        setCurrent("");
        curRef.current?.focus();
      } else if (err instanceof ApiError && err.status === 401) {
        router.replace("/login");
      } else if (err instanceof ApiError && (err.status === 429 || err.isNetworkError)) {
        setFormErr(err.message);
      } else if (err instanceof ApiError && err.status === 422) {
        setNextErr(MESSAGES.newPasswordShort);
      } else {
        setFormErr(MESSAGES.generic);
      }
    }
  }

  return (
    <section className={card} aria-labelledby="chpw-title">
      <h2 id="chpw-title" className="text-xl font-semibold">Change password</h2>
      <p className="mt-2 text-sm text-muted">After changing it you are signed out on all devices and sign in again.</p>
      <div role="alert" className="sr-only">{curErr ?? nextErr ?? confirmErr ?? formErr ?? ""}</div>
      {formErr && <div className="mt-4"><FormErrorBox message={formErr} /></div>}
      <form onSubmit={onSubmit} noValidate method="post" action="#" className="mt-6 space-y-5">
        <PasswordField ref={curRef} id="current-password" name="current-password" label="Current password"
          autoComplete="current-password" value={current} onChange={(e) => setCurrent(e.target.value)} error={curErr} />
        <PasswordField ref={nextRef} id="new-password" name="new-password" label="New password"
          autoComplete="new-password" value={next} onChange={(e) => setNext(e.target.value)} error={nextErr}
          hint="At least 12 characters." />
        <PasswordField ref={confirmRef} id="confirm-password" name="confirm-password" label="Repeat new password"
          autoComplete="new-password" value={confirm} onChange={(e) => setConfirm(e.target.value)} error={confirmErr} />
        <SubmitButton busy={busy} label="Change password" busyLabel="Saving…" />
      </form>
    </section>
  );
}

function SignOutEverywhereCard() {
  const router = useRouter();
  const [asking, setAsking] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function confirm() {
    setBusy(true);
    setError(null);
    try {
      await logoutAll();
      router.replace("/login");
    } catch (err) {
      setBusy(false);
      if (err instanceof ApiError && err.status === 401) router.replace("/login");
      else setError(err instanceof ApiError ? err.message : MESSAGES.generic);
    }
  }

  return (
    <section className={card} aria-labelledby="signout-all-title">
      <h2 id="signout-all-title" className="text-xl font-semibold">Sign out of all devices</h2>
      <p className="mt-2 text-sm text-muted">
        Use this if you lost a device or think someone else used your account. Every browser, including this one, will need to sign in again.
      </p>
      {error && <div className="mt-4"><FormErrorBox message={error} /></div>}
      {!asking ? (
        <button type="button" onClick={() => setAsking(true)} className="mt-6 rounded-lg border border-line px-5 py-3 hover:border-accent2">
          Sign out of all devices
        </button>
      ) : (
        <div className="mt-6 flex flex-wrap items-center gap-3" role="group" aria-label="Confirm sign out of all devices">
          <span className="text-sm">Sign out everywhere, including here?</span>
          <button type="button" onClick={confirm} disabled={busy} autoFocus
            className="rounded-lg bg-accent px-4 py-2 text-sm font-medium text-bg hover:bg-accent2 disabled:opacity-70">
            {busy ? "Signing out…" : "Yes, sign out"}
          </button>
          <button type="button" onClick={() => setAsking(false)} disabled={busy} className="rounded-lg border border-line px-4 py-2 text-sm hover:border-accent2">
            Cancel
          </button>
        </div>
      )}
    </section>
  );
}

export function ProfileView() {
  const { user } = useSession();
  if (!user) return null;
  return (
    <main id="main" className="mx-auto w-full max-w-3xl px-5 py-12">
      <h1 className="text-3xl font-semibold tracking-tight">Profile and security</h1>

      <dl className={`${card} mt-8 grid gap-6 sm:grid-cols-2`}>
        <div><dt className="text-sm text-muted">Name</dt><dd className="mt-1 font-medium">{user.full_name}</dd></div>
        <div><dt className="text-sm text-muted">Email</dt><dd className="mt-1 font-medium">{user.email}</dd></div>
        <div><dt className="text-sm text-muted">Department</dt><dd className="mt-1 font-medium">{user.department.name}</dd></div>
        <div>
          <dt className="text-sm text-muted">Roles</dt>
          <dd className="mt-1 flex flex-wrap gap-2">
            {user.roles.map((r) => <span key={r} className="rounded-full border border-line bg-surface2 px-3 py-1 text-sm">{r}</span>)}
          </dd>
        </div>
      </dl>
      <p className="mt-3 text-sm text-muted">Name, department and roles are managed by an administrator.</p>

      <div className="mt-10 space-y-8">
        <ChangePasswordCard />
        <SignOutEverywhereCard />
      </div>
    </main>
  );
}
