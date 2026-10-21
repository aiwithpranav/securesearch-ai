import type { Metadata } from "next";
import { ResetForm } from "./ResetForm";
import { AuthShell } from "../_auth/AuthShell";

export const metadata: Metadata = { title: "Set a new password" };

// The reset link looks like /reset-password#token=...  The part after "#" never reaches the server.
export default function ResetPasswordPage() {
  return (
    <AuthShell>
      <ResetForm />
    </AuthShell>
  );
}
