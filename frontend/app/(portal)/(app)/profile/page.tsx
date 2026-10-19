import type { Metadata } from "next";
import { ProfileView } from "./ProfileView";

export const metadata: Metadata = { title: "Profile and security" };

export default function ProfilePage() {
  return <ProfileView />;
}
