"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { logout } from "@/lib/session";
import { useSession } from "../_auth/AuthProvider";
import { NotificationBell } from "./NotificationBell";

export function PortalHeader() {
  const router = useRouter();
  const pathname = usePathname();
  const { user } = useSession();
  const [leaving, setLeaving] = useState(false);

  // Admin links are only shown to administrators. The API checks the role again on every request.
  const isAdmin = user?.roles.includes("system_admin") ?? false;
  const links = [
    { href: "/home", label: "Home" },
    ...(isAdmin ? [{ href: "/admin/documents", label: "Documents" }] : []),
    { href: "/profile", label: "Profile" },
  ];

  async function signOut() {
    setLeaving(true);
    await logout();
    router.replace("/login");
  }

  return (
    <header className="border-b border-line bg-bg/90">
      {/* flex-wrap: on a narrow phone the menu drops under the brand instead of overflowing */}
      <div className="mx-auto flex min-h-16 w-full max-w-6xl flex-wrap items-center justify-between gap-x-4 gap-y-1 px-5 py-2">
        <Link href="/home" className="font-semibold">SecureSearch AI</Link>
        <nav aria-label="Account" className="flex flex-wrap items-center gap-1 text-sm">
          {links.map((l) => {
            const current = pathname === l.href || (l.href !== "/home" && pathname.startsWith(l.href));
            return (
              <Link
                key={l.href}
                href={l.href}
                aria-current={current ? "page" : undefined}
                className={`rounded-lg px-3 py-2 ${current ? "bg-surface2 text-text" : "text-muted hover:text-text"}`}
              >
                {l.label}
              </Link>
            );
          })}
          {isAdmin && <NotificationBell />}
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
