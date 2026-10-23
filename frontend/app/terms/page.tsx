import Link from "next/link";
import type { Metadata } from "next";

export const metadata: Metadata = { title: "Terms" };

export default function Page() {
  return (
    <main id="main" className="mx-auto min-h-screen max-w-3xl px-5 py-16">
      <Link href="/" className="text-sm text-accent2 underline underline-offset-4">Back to home</Link>
      <h1 className="mt-6 text-4xl font-semibold">Terms</h1>
      <div className="mt-8 space-y-6 text-muted">
        <p className="rounded-lg border border-line bg-surface2 p-4 text-sm">
          This is a demonstration project, not a commercial service. These terms are plain-language and are not legal advice: have them reviewed before any real use.
        </p>

        <section aria-labelledby="t-what">
          <h2 id="t-what" className="text-xl font-semibold text-text">What this is</h2>
          <p className="mt-2">SecureSearch AI is a portfolio project that shows how an AI knowledge search can check permissions before it searches. Every document, person and company in it is invented.</p>
        </section>

        <section aria-labelledby="t-use">
          <h2 id="t-use" className="text-xl font-semibold text-text">Using it</h2>
          <ul className="mt-2 list-disc space-y-2 pl-6">
            <li>Use it only with synthetic data. Do not upload real personal, confidential or regulated information.</li>
            <li>Do not try to break into accounts, overload the service or access data you were not given access to. Report weaknesses through the <a className="text-accent2 underline underline-offset-4" href="https://github.com/aiwithpranav/securesearch-ai/blob/main/SECURITY.md">security policy</a> instead.</li>
          </ul>
        </section>

        <section aria-labelledby="t-ai">
          <h2 id="t-ai" className="text-xl font-semibold text-text">Answers can be wrong</h2>
          <p className="mt-2">Answers are written by an AI model from the passages you may read. They can be incomplete or mistaken. Every answer lists its sources so you can check the original text; do not rely on an answer alone for anything important.</p>
        </section>

        <section aria-labelledby="t-asis">
          <h2 id="t-asis" className="text-xl font-semibold text-text">No warranty</h2>
          <p className="mt-2">The software is provided &ldquo;as is&rdquo;, without warranty of any kind, and may change or be switched off at any time. The authors are not liable for any loss arising from its use. The source code is available under the MIT licence.</p>
        </section>

        <p>How personal data is handled is described on the <Link href="/privacy" className="text-accent2 underline underline-offset-4">Privacy page</Link>.</p>
      </div>
    </main>
  );
}
