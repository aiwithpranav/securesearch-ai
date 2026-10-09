import Link from "next/link";
import type { Metadata } from "next";
export const metadata: Metadata = { title: "Terms" };
export default function Page() {
  return (
    <main id="main" className="mx-auto min-h-screen max-w-3xl px-5 py-16">
      <Link href="/" className="text-sm text-accent2 underline underline-offset-4">Back to home</Link>
      <h1 className="mt-6 text-4xl font-semibold">Terms</h1>
      <div className="mt-8 space-y-4 text-muted">
<p className="rounded-lg border border-line bg-surface2 p-4 text-sm">Draft for a demo project. Have it reviewed before any real use.</p>
<p>This page describes a product that is still in development. Features shown may change.</p>
<p>Examples and names on this page are fictional sample data. The page is provided as is, without warranties.</p>
      </div>
    </main>
  );
}
