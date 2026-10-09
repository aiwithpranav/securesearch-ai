import Link from "next/link";
export default function NotFound() {
  return (
    <main id="main" className="mx-auto flex min-h-screen max-w-xl flex-col items-start justify-center px-5">
      <h1 className="text-4xl font-semibold">This page does not exist.</h1>
      <p className="mt-4 text-muted">The link may be wrong, or the page may not be built yet. Go back to the home page and try again.</p>
      <Link href="/" className="mt-8 rounded-lg bg-accent px-5 py-3 font-medium text-bg">Back to home</Link>
    </main>
  );
}
