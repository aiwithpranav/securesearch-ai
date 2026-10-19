import type { Metadata } from "next";
import Link from "next/link";
import { LoginForm } from "./LoginForm";

export const metadata: Metadata = { title: "Sign in" };

export default function LoginPage() {
  return (
    <main id="main" className="mx-auto flex min-h-screen w-full max-w-md flex-col justify-center px-5 py-12">
      <Link href="/" className="mb-8 font-semibold text-muted hover:text-text">← SecureSearch AI</Link>
      <LoginForm />
    </main>
  );
}
