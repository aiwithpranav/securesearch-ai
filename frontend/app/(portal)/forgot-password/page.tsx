import type { Metadata } from "next";
import Link from "next/link";
import { ForgotForm } from "./ForgotForm";
import { AuthShell } from "../_auth/AuthShell";

export const metadata: Metadata = { title: "Forgot password" };

export default function ForgotPasswordPage() {
  return (
    <AuthShell>
      <Link href="/login" className="mb-8 font-semibold text-muted hover:text-text">← Back to sign in</Link>
      <ForgotForm />
    </AuthShell>
  );
}
