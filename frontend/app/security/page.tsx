import Link from "next/link";
import type { Metadata } from "next";
export const metadata: Metadata = { title: "Security overview" };
export default function Page() {
  return (
    <main id="main" className="mx-auto min-h-screen max-w-3xl px-5 py-16">
      <Link href="/" className="text-sm text-accent2 underline underline-offset-4">Back to home</Link>
      <h1 className="mt-6 text-4xl font-semibold">Security overview</h1>
      <div className="mt-8 space-y-4 text-muted">
<p>SecureSearch AI is designed so the language model never sees text a user may not read. These are the design rules:</p>
<ul className="list-disc space-y-2 pl-6">
<li>Deny by default: no matching rule means no access.</li>
<li>Deny beats allow: one deny rule removes access.</li>
<li>The server decides: roles are read from the database on every request, never from the browser.</li>
<li>Administrators manage access but do not automatically read document content.</li>
<li>Refusals look the same whether a topic is restricted or simply missing.</li>
<li>The audit log stores IDs and outcomes, not document text.</li>
</ul>
<p>These are design goals for a product in development. Test results will be published once the evaluation exists.</p>
<p>To report a security concern, use the Request demo email link on the home page until a dedicated contact exists.</p>
      </div>
    </main>
  );
}
