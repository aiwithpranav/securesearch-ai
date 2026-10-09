import Link from "next/link";
import type { Metadata } from "next";
export const metadata: Metadata = { title: "Privacy" };
export default function Page() {
  return (
    <main id="main" className="mx-auto min-h-screen max-w-3xl px-5 py-16">
      <Link href="/" className="text-sm text-accent2 underline underline-offset-4">Back to home</Link>
      <h1 className="mt-6 text-4xl font-semibold">Privacy</h1>
      <div className="mt-8 space-y-4 text-muted">
<p className="rounded-lg border border-line bg-surface2 p-4 text-sm">Draft for a demo project. Have it reviewed before any real use.</p>
<p>This site does not use cookies, analytics or tracking. It collects no personal data itself.</p>
<p>The Request demo button opens an email draft in your own mail app. We receive nothing unless you choose to send that email.</p>
<p>The product examples on this page use synthetic sample data only.</p>
      </div>
    </main>
  );
}
