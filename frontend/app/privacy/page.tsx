import Link from "next/link";
import type { Metadata } from "next";

export const metadata: Metadata = { title: "Privacy" };

export default function Page() {
  return (
    <main id="main" className="mx-auto min-h-screen max-w-3xl px-5 py-16">
      <Link href="/" className="text-sm text-accent2 underline underline-offset-4">Back to home</Link>
      <h1 className="mt-6 text-4xl font-semibold">Privacy</h1>
      <div className="mt-8 space-y-6 text-muted">
        <p className="rounded-lg border border-line bg-surface2 p-4 text-sm">
          This is a demonstration project that uses invented data only. This text describes what the software really does. It is not legal advice: have it reviewed before any real use.
        </p>

        <section aria-labelledby="p-visit">
          <h2 id="p-visit" className="text-xl font-semibold text-text">Visiting this site</h2>
          <p className="mt-2">The public pages (home, privacy, terms, security, status) set no cookies and use no analytics, advertising or tracking. They collect no personal data. The &ldquo;View on GitHub&rdquo; button is an ordinary link to the project&apos;s repository.</p>
        </section>

        <section aria-labelledby="p-account">
          <h2 id="p-account" className="text-xl font-semibold text-text">When you sign in</h2>
          <ul className="mt-2 list-disc space-y-2 pl-6">
            <li><b className="text-text">One cookie.</b> After you sign in, the server sets one cookie, <code>refresh_token</code>. It only keeps you signed in, JavaScript cannot read it, and it is removed when you sign out or it expires (1 day, or 7 days if you choose &ldquo;Remember me&rdquo;). There are no other cookies.</li>
            <li><b className="text-text">One note in your browser.</b> The browser remembers that you skipped the welcome tour. It holds no personal data.</li>
            <li><b className="text-text">Your account.</b> Name, email, department, roles, clearance level and country, set by an administrator. Your password is stored only as a salted Argon2id hash; nobody can read it.</li>
          </ul>
        </section>

        <section aria-labelledby="p-ask">
          <h2 id="p-ask" className="text-xl font-semibold text-text">When you ask a question</h2>
          <ul className="mt-2 list-disc space-y-2 pl-6">
            <li><b className="text-text">What is kept for you.</b> Your recent questions, the answer&apos;s status and which sources it cited (not the answer text), so you can ask again. Only you can see this list, and you can delete any entry.</li>
            <li><b className="text-text">What the audit trail keeps.</b> For security, one record per question: who asked, the question, how many documents you could read, which passages were found and cited (as ids), the outcome and the time. Never the answer and never document text. Only security staff and auditors can read it. It is removed after 365 days by default.</li>
            <li><b className="text-text">What leaves the server.</b> To write an answer, the server sends your question and a few short passages, only passages you are allowed to read, to the AI provider (OpenAI). Nothing else about you is sent. Searching, understanding meaning and ranking run on the server itself. If no provider key is set, no answer is written and nothing is sent.</li>
          </ul>
        </section>

        <section aria-labelledby="p-docs">
          <h2 id="p-docs" className="text-xl font-semibold text-text">Documents and sources</h2>
          <p className="mt-2">Documents are uploaded by administrators, who manage them but cannot read their content. A connected source (for example a GitHub folder) is read with a read-only key kept on the server; nothing is written back. All documents in this project are invented.</p>
        </section>

        <section aria-labelledby="p-rights">
          <h2 id="p-rights" className="text-xl font-semibold text-text">Your choices</h2>
          <p className="mt-2">Delete your question history on the Ask page. Ask an administrator to correct or deactivate your account. Security events (such as sign-ins) are kept in the audit trail for the retention period.</p>
        </section>

        <p>Questions or concerns: see the <a className="text-accent2 underline underline-offset-4" href="https://github.com/aiwithpranav/securesearch-ai/blob/main/SECURITY.md">security policy</a>.</p>
      </div>
    </main>
  );
}
