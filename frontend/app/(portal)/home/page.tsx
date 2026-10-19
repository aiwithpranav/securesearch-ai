import type { Metadata } from "next";
import { RequireAuth } from "../_auth/RequireAuth";
import { HomeView } from "./HomeView";

export const metadata: Metadata = { title: "Home" };

export default function HomePage() {
  return (
    <RequireAuth>
      <HomeView />
    </RequireAuth>
  );
}
