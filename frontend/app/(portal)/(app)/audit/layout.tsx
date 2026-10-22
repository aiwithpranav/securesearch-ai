"use client";

import { canSeeAudit } from "@/lib/roles";
import { useSession } from "../../_auth/AuthProvider";
import { NoAccess } from "../admin/_components/ui";

// The audit trail is for security_admin and auditor only (not even the system administrator).
// This decides what the page SHOWS: the API checks the role again on every request.
export default function AuditLayout({ children }: { children: React.ReactNode }) {
  const { user } = useSession();
  if (!user || !canSeeAudit(user.roles)) return <NoAccess />;
  return <>{children}</>;
}
