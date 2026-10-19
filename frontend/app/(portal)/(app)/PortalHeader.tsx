"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { logout } from "@/lib/session";

const links = [
  { href: "/home", label: "Home" },
  { href: "/profile", label: "Profile" },
];

export function PortalHeader() {
  const router = useRouter();
  const pathname = usePathname();
  const [leaving, setLeaving] = useState(false);

  async function signOut() {
    setLeaving(true);
    await logout();
    router.replace("/login");
  }

  return (
    <header className="border-b border-line bg-bg/90">
      <div className="mx-auto flex h-16 w-full max-w-6xl items-center justify-between gap-4 px-5">
        <Link href="/home" className="font-semibold">SecureSearch AI</Link>
        <nav aria-label="Account" className="flex items-center gap-1 text-sm">
          {links.map((l) => (
            <Link
              key={l.href}
              href={l.href}
              aria-current={pathname === l.href ? "page" : undefined}
              className={`rounded-lg px-3 py-2 ${pathname === l.href ? "bg-surface2 text-text" : "text-muted hover:text-text"}`}
            >
              {l.label}
            </Link>
          ))}
          <button
            onClick={signOut}
            disabled={leaving}
            className="ml-2 rounded-lg border border-line px-4 py-2 hover:border-accent2 disabled:opacity-70"
          >
            {leaving ? "Signing out…" : "Sign out"}
          </button>
        </nav>
      </div>
    </header>
  );
}
