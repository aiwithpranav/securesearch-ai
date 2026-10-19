"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { logout } from "@/lib/session";
import { useSession } from "../_auth/AuthProvider";

const card = "rounded-2xl border border-line bg-surface p-6";

// Phase 2C-1: a simple home shell that proves who is signed in.
// Search arrives in Phase 6; the tour, guide and profile come in 2C-2.
export function HomeView() {
  const { user } = useSession();
  const router = useRouter();
  const [leaving, setLeaving] = useState(false);

  if (!user) return null;

  async function signOut() {
    setLeaving(true);
    await logout();
    router.replace("/login");
  }

  const isAdmin = user.roles.includes("system_admin");

  return (
    <div className="min-h-screen">
      <header className="border-b border-line bg-bg/90">
        <div className="mx-auto flex h-16 w-full max-w-6xl items-center justify-between px-5">
          <span className="font-semibold">SecureSearch AI</span>
          <button
            onClick={signOut}
            disabled={leaving}
            className="rounded-lg border border-line px-4 py-2 text-sm hover:border-accent2 disabled:opacity-70"
          >
            {leaving ? "Signing out…" : "Sign out"}
          </button>
        </div>
      </header>

      <main id="main" className="mx-auto w-full max-w-6xl px-5 py-12">
        <h1 className="text-3xl font-semibold tracking-tight">Welcome, {user.full_name}</h1>
        <p className="mt-2 text-muted">You are signed in. Search will appear here in a later phase.</p>

        <dl className={`${card} mt-8 grid gap-6 sm:grid-cols-2`}>
          <div><dt className="text-sm text-muted">Email</dt><dd className="mt-1 font-medium">{user.email}</dd></div>
          <div><dt className="text-sm text-muted">Department</dt><dd className="mt-1 font-medium">{user.department.name}</dd></div>
          <div>
            <dt className="text-sm text-muted">Roles</dt>
            <dd className="mt-1 flex flex-wrap gap-2">
              {user.roles.map((r) => (
                <span key={r} className="rounded-full border border-line bg-surface2 px-3 py-1 text-sm">{r}</span>
              ))}
            </dd>
          </div>
          <div><dt className="text-sm text-muted">Clearance level</dt><dd className="mt-1 font-medium">{user.clearance_level}</dd></div>
          <div><dt className="text-sm text-muted">Country</dt><dd className="mt-1 font-medium">{user.country}</dd></div>
        </dl>

        {isAdmin && (
          <p className="mt-6 text-sm text-muted">
            You can manage accounts as an administrator. Managing accounts does not give access to document content.
          </p>
        )}
      </main>
    </div>
  );
}
