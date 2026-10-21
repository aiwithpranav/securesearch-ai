"use client";

import Link from "next/link";
import { OPEN_TOUR_EVENT } from "@/lib/tour";
import { useSession } from "../../_auth/AuthProvider";

const card = "rounded-2xl border border-line bg-surface p-6";

type Step = { text: string; later?: string; href?: string };

// Blueprint section 20.3: Employee = sign in, ask, read, open source, rate.
// Admin = upload, set access, check status. Steps that need later phases say so honestly.
const EMPLOYEE_STEPS: Step[] = [
  { text: "Sign in (done: you are here)." },
  { text: "Search in your own words.", href: "/search" },
  { text: "Get a written answer with sources.", later: "Phase 6" },
  { text: "Open a source to check the original text.", later: "Phase 6" },
  { text: "Rate the answer with a thumbs up or down.", later: "Phase 6" },
];
const ADMIN_STEPS: Step[] = [
  { text: "Upload a document.", later: "Phase 3" },
  { text: "Set who can read it (allow and deny rules).", later: "Phase 4" },
  { text: "Check its status and the system health.", later: "Phases 3 and 7" },
];

function Steps({ title, steps }: { title: string; steps: Step[] }) {
  return (
    <section className={card} aria-labelledby={`guide-${title}`}>
      <h3 id={`guide-${title}`} className="text-lg font-semibold">{title}</h3>
      <ol className="mt-4 list-decimal space-y-2 pl-5">
        {steps.map((s) => (
          <li key={s.text}>
            {s.href ? <Link href={s.href} className="text-accent2 hover:underline">{s.text}</Link> : s.text}
            {s.later && <span className="ml-2 rounded-full border border-line px-2 py-0.5 text-xs text-muted">Coming in {s.later}</span>}
          </li>
        ))}
      </ol>
    </section>
  );
}

// Home shell. Search is here (Phase 5); answers with citations arrive in Phase 6.
export function HomeView() {
  const { user } = useSession();
  if (!user) return null;
  const isAdmin = user.roles.includes("system_admin");

  return (
    <main id="main" className="mx-auto w-full max-w-6xl px-5 py-12">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight">Welcome, {user.full_name}</h1>
          <p className="mt-2 text-muted">You are signed in. <Link href="/search" className="text-accent2 hover:underline">Search the documents you may read</Link>.</p>
        </div>
        <button
          type="button"
          onClick={() => window.dispatchEvent(new Event(OPEN_TOUR_EVENT))}
          className="rounded-lg border border-line px-4 py-2 text-sm hover:border-accent2"
        >
          Take the tour again
        </button>
      </div>

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

      <h2 className="mt-12 text-2xl font-semibold tracking-tight">Your first 2 minutes</h2>
      <div className={`mt-6 grid gap-6 ${isAdmin ? "md:grid-cols-2" : ""}`}>
        <Steps title="As an employee" steps={EMPLOYEE_STEPS} />
        {isAdmin && <Steps title="As an administrator" steps={ADMIN_STEPS} />}
      </div>
      {isAdmin && (
        <p className="mt-6 text-sm text-muted">
          Managing accounts does not give access to document content. Reading a document needs its own permission.
        </p>
      )}
    </main>
  );
}
