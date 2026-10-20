"use client";

import { useSession } from "../../_auth/AuthProvider";
import { NoAccess } from "./_components/ui";

// Everything under /admin needs the system_admin role. This only decides what the page SHOWS:
// the API checks the role again on every request (roles are read from the database).
export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const { user } = useSession();
  if (!user || !user.roles.includes("system_admin")) return <NoAccess />;
  return <>{children}</>;
}
