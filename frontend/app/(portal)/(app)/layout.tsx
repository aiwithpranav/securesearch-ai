import { RequireAuth } from "../_auth/RequireAuth";
import { PortalHeader } from "./PortalHeader";
import { WelcomeTour } from "./WelcomeTour";

// Every page in (app) needs a signed-in user. The header and the first-login tour live here once.
export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <RequireAuth>
      <div className="min-h-screen">
        <PortalHeader />
        {children}
      </div>
      <WelcomeTour />
    </RequireAuth>
  );
}
