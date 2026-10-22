"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { manageLinks } from "@/lib/roles";
import { logout } from "@/lib/session";
import { useSession } from "../_auth/AuthProvider";
import { NotificationBell } from "./NotificationBell";

const linkClass = (current: boolean) => `rounded-lg px-3 py-2 ${current ? "bg-surface2 text-text" : "text-muted hover:text-text"}`;

/** The "Manage" menu: only the screens this person's roles allow. The API checks the role again on every request. */
function ManageMenu({ links, pathname }: { links: { href: string; label: string }[]; pathname: string }) {
  const [open, setOpen] = useState(false);
  const box = useRef<HTMLDivElement>(null);
  const button = useRef<HTMLButtonElement>(null);

  useEffect(() => setOpen(false), [pathname]);
  useEffect(() => {
    if (!open) return;
    const onClick = (e: MouseEvent) => { if (!box.current?.contains(e.target as Node)) setOpen(false); };
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") { setOpen(false); button.current?.focus(); } };
    document.addEventListener("mousedown", onClick);
    document.addEventListener("keydown", onKey);
    return () => { document.removeEventListener("mousedown", onClick); document.removeEventListener("keydown", onKey); };
  }, [open]);

  const inside = links.some((l) => pathname.startsWith(l.href));
  return (
    <div ref={box} className="relative">
      <button
        ref={button}
        type="button"
        aria-haspopup="true"
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
        className={`flex items-center gap-1 ${linkClass(inside)}`}
      >
        Manage
        <svg aria-hidden="true" viewBox="0 0 24 24" className={`h-3.5 w-3.5 transition-transform motion-reduce:transition-none ${open ? "rotate-180" : ""}`}>
          <path d="M6 9l6 6 6-6" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </button>
      {open && (
        <ul className="absolute right-0 z-20 mt-2 w-52 rounded-xl border border-line bg-surface p-1 shadow-lg">
          {links.map((l) => {
            const current = pathname === l.href || pathname.startsWith(`${l.href}/`);
            return (
              <li key={l.href}>
                <Link href={l.href} aria-current={current ? "page" : undefined} className={`block ${linkClass(current)}`}>
                  {l.label}
                </Link>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

export function PortalHeader() {
  const router = useRouter();
  const pathname = usePathname();
  const { user } = useSession();
  const [leaving, setLeaving] = useState(false);

  const isAdmin = user?.roles.includes("system_admin") ?? false;
  const manage = manageLinks(user?.roles ?? []);
  const links = [
    { href: "/home", label: "Home" },
    { href: "/search", label: "Ask" },
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
              <Link key={l.href} href={l.href} aria-current={current ? "page" : undefined} className={linkClass(current)}>
                {l.label}
              </Link>
            );
          })}
          {manage.length > 0 && <ManageMenu links={manage} pathname={pathname} />}
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
