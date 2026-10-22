"use client";

import { canSeeGaps } from "@/lib/roles";
import { useSession } from "../../_auth/AuthProvider";
import { NoAccess } from "../admin/_components/ui";

// Knowledge gaps are for system_admin and security_admin. The API checks the role again on every request.
export default function GapsLayout({ children }: { children: React.ReactNode }) {
  const { user } = useSession();
  if (!user || !canSeeGaps(user.roles)) return <NoAccess />;
  return <>{children}</>;
}
