"use client";

import { useEffect, useSyncExternalStore } from "react";
import { bootstrapSession, getServerSnapshot, getSnapshot, subscribe, type SessionState } from "@/lib/session";

/** Restores the session once when the portal opens (login, home, profile...). */
export function AuthProvider({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    bootstrapSession();
  }, []);
  return <>{children}</>;
}

export function useSession(): SessionState {
  return useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
}
