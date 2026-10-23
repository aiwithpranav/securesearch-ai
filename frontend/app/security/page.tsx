import Link from "next/link";
import type { Metadata } from "next";

export const metadata: Metadata = { title: "Security overview" };

const WALLS = [
  ["Endpoint check", "Every route checks who you are and what role you hold, on the server, on every request."],
  ["Access context", "Search and answer code cannot run without knowing who is asking."],
  ["Rules in the database", "The list of documents you may read is part of the database query itself. Text you may not read is never searched, ranked or sent to the model."],
  ["Second look", "After searching, every passage is checked again against that list before it goes any further."],
  ["Citation check", "Every source in an answer is checked against what you may read; an answer that cites anything else is refused."],
  ["Leak tests on every change", "Secret marker words are planted in restricted documents, and the build fails if one ever appears for someone who may not see it."],
] as const;

export default function Page() {
  return (
    <main id="main" className="mx-auto min-h-screen max-w-3xl px-5 py-16">
      <Link href="/" className="text-sm text-accent2 underline underline-offset-4">Back to home</Link>
      <h1 className="mt-6 text-4xl font-semibold">Security overview</h1>
      <div className="mt-8 space-y-6 text-muted">
        <p>SecureSearch AI is built so the language model never sees text a person may not read. The rules:</p>
        <ul className="list-disc space-y-2 pl-6">
          <li>Deny by default: no matching rule means no access, and a document with no rules is invisible.</li>
          <li>Deny beats allow: one deny rule removes access.</li>
          <li>The server decides: roles and attributes are read from the database on every request, never from the browser.</li>
          <li>Administrators manage access but do not automatically read document content.</li>
          <li>Refusals look the same whether a topic is restricted or simply missing.</li>
          <li>The audit trail stores ids and outcomes, never answers or document text. The database refuses to change it, and only the scheduled retention job removes records, after the retention period.</li>
          <li>The model is a writer, never a guard: it has no tools, and its output is validated before anyone sees it.</li>
        </ul>

        <section aria-labelledby="s-walls">
          <h2 id="s-walls" className="text-xl font-semibold text-text">Six walls</h2>
          <p className="mt-2">If one wall had a bug, the next would still stop a leak.</p>
          <ol className="mt-3 list-decimal space-y-2 pl-6">
            {WALLS.map(([name, text]) => (
              <li key={name}><b className="text-text">{name}.</b> {text}</li>
            ))}
          </ol>
        </section>

        <section aria-labelledby="s-proof">
          <h2 id="s-proof" className="text-xl font-semibold text-text">Evidence, not claims</h2>
          <p className="mt-2">An evaluation asks 62 questions as 8 different people over 48 invented documents, including prompt-injection attempts and 14 situations where access changes. On this set it found <b className="text-text">0 leaks</b>. That is a result for this test set, not a promise for any other; the full report and its limits are in the project&apos;s repository.</p>
        </section>

        <section aria-labelledby="s-report">
          <h2 id="s-report" className="text-xl font-semibold text-text">Report a weakness</h2>
          <p className="mt-2">Please do not open a public issue. Use <a className="text-accent2 underline underline-offset-4" href="https://github.com/aiwithpranav/securesearch-ai/security/advisories/new">private vulnerability reporting</a> on the repository, and read the <a className="text-accent2 underline underline-offset-4" href="https://github.com/aiwithpranav/securesearch-ai/blob/main/SECURITY.md">security policy</a>.</p>
        </section>
      </div>
    </main>
  );
}
