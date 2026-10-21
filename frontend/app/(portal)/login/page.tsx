import type { Metadata } from "next";
import Link from "next/link";
import { LoginForm } from "./LoginForm";
import { AuthShell } from "../_auth/AuthShell";

export const metadata: Metadata = { title: "Sign in" };

export default function LoginPage() {
  return (
    <AuthShell>
      <Link href="/" className="mb-8 font-semibold text-muted hover:text-text">← SecureSearch AI</Link>
      <LoginForm />
    </AuthShell>
  );
}
