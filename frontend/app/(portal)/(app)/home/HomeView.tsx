"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ageText, listHistory, statusText, type HistoryItem } from "@/lib/chat";
import { getSuggestions } from "@/lib/dashboards";
import { setPendingQuestion } from "@/lib/pendingQuestion";
import { OPEN_TOUR_EVENT } from "@/lib/tour";
import { useSession } from "../../_auth/AuthProvider";

const card = "rounded-2xl border border-line bg-surface p-6";

type Step = { text: string; later?: string; href?: string };

// Blueprint section 20.3: Employee = sign in, ask, read, open source, rate.
// Admin = upload, set access, check status. Steps that need later phases say so honestly.
const EMPLOYEE_STEPS: Step[] = [
  { text: "Sign in (done: you are here)." },
  { text: "Ask a question in your own words.", href: "/search" },
  { text: "Read the answer and its sources." },
  { text: "Open a source to check the original text." },
  { text: "Rate the answer with a thumbs up or down." },
];
const ADMIN_STEPS: Step[] = [
  { text: "Upload a document.", href: "/admin/documents/upload" },
  { text: "Set who can read it (allow and deny rules).", href: "/admin/documents" },
  { text: "Check its status and the system health.", href: "/admin/overview" },
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

/** Recent questions and ideas to ask. Picking one fills the Ask box (through memory, never the address bar); it does not ask by itself. */
function QuickStart() {
  const router = useRouter();
  const [recent, setRecent] = useState<HistoryItem[] | null>(null);
  const [ideas, setIdeas] = useState<string[] | null>(null);

  useEffect(() => {
    listHistory(5).then((p) => setRecent(p.items)).catch(() => setRecent([]));
    getSuggestions().then((p) => setIdeas(p.items)).catch(() => setIdeas([]));
  }, []);

  function pick(q: string) {
    setPendingQuestion(q);
    router.push("/search");
  }
  const chip = "w-full rounded-xl border border-line bg-surface2 px-4 py-3 text-left hover:border-accent2";

  return (
    <div className="mt-8 grid gap-6 md:grid-cols-2">
      <section className={card} aria-labelledby="h-ideas">
        <h2 id="h-ideas" className="text-lg font-semibold">Ideas to ask</h2>
        <p className="mt-1 text-sm text-muted">Based on the documents you may read.</p>
        {ideas === null ? <div role="status" aria-label="Loading ideas" className="mt-4 h-24 animate-pulse rounded-lg bg-surface2 motion-reduce:animate-none" />
          : ideas.length === 0 ? <p className="mt-4 text-sm text-muted">No documents are available to you yet.</p>
          : <ul className="mt-4 space-y-2">{ideas.map((q) => <li key={q}><button type="button" onClick={() => pick(q)} className={chip}>{q}</button></li>)}</ul>}
      </section>
      <section className={card} aria-labelledby="h-recent">
        <h2 id="h-recent" className="text-lg font-semibold">Your recent questions</h2>
        <p className="mt-1 text-sm text-muted">Only you can see these. You can delete them on the Ask page.</p>
        {recent === null ? <div role="status" aria-label="Loading recent questions" className="mt-4 h-24 animate-pulse rounded-lg bg-surface2 motion-reduce:animate-none" />
          : recent.length === 0 ? <p className="mt-4 text-sm text-muted">You have not asked anything yet.</p>
          : (
            <ul className="mt-4 space-y-2">
              {recent.map((h) => (
                <li key={h.id}>
                  <button type="button" onClick={() => pick(h.question)} className={chip}>
                    <span className="block break-words">{h.question}</span>
                    <span className="mt-1 block text-xs text-muted">{statusText(h.status)} · {ageText(h.created_at)}</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
      </section>
    </div>
  );
}

// Home shell. Questions, answers with sources and ratings live on the Ask page.
export function HomeView() {
  const { user } = useSession();
  if (!user) return null;
  const isAdmin = user.roles.includes("system_admin");

  return (
    <main id="main" className="mx-auto w-full max-w-6xl px-5 py-12">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight">Welcome, {user.full_name}</h1>
          <p className="mt-2 text-muted">You are signed in. <Link href="/search" className="text-accent2 hover:underline">Ask a question about the documents you may read</Link>.</p>
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

      <QuickStart />

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
