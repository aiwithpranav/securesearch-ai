import type { Metadata } from "next";
import { ResetForm } from "./ResetForm";

export const metadata: Metadata = { title: "Set a new password" };

// The reset link looks like /reset-password#token=...  The part after "#" never reaches the server.
export default function ResetPasswordPage() {
  return (
    <main id="main" className="mx-auto flex min-h-screen w-full max-w-md flex-col justify-center px-5 py-12">
      <ResetForm />
    </main>
  );
}
