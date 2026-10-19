"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useSession } from "./AuthProvider";

/** Client-side guard. NOTE: this only decides what the page shows. Real protection is the API,
 *  which checks the token and the user's permissions on every request. */
export function RequireAuth({ children }: { children: React.ReactNode }) {
  const { status } = useSession();
  const router = useRouter();

  useEffect(() => {
    if (status === "signed-out") router.replace("/login");
  }, [status, router]);

  if (status !== "signed-in") {
    return (
      <main id="main" className="mx-auto flex min-h-screen max-w-xl items-center justify-center px-5" aria-busy="true">
        <p role="status" className="text-muted">Checking your session…</p>
      </main>
    );
  }
  return <>{children}</>;
}
