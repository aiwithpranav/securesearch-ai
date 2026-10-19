import { AuthProvider } from "./_auth/AuthProvider";

// Everything inside (portal) shares one session: login, home, profile...
// The public landing page and legal pages stay outside, so visitors never trigger a refresh call.
export default function PortalLayout({ children }: { children: React.ReactNode }) {
  return <AuthProvider>{children}</AuthProvider>;
}
