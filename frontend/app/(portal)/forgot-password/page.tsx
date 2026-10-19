import type { Metadata } from "next";
import Link from "next/link";
import { ForgotForm } from "./ForgotForm";

export const metadata: Metadata = { title: "Forgot password" };

export default function ForgotPasswordPage() {
  return (
    <main id="main" className="mx-auto flex min-h-screen w-full max-w-md flex-col justify-center px-5 py-12">
      <Link href="/login" className="mb-8 font-semibold text-muted hover:text-text">← Back to sign in</Link>
      <ForgotForm />
    </main>
  );
}
