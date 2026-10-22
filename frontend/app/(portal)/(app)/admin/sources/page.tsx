import type { Metadata } from "next";
import { SourcesView } from "./SourcesView";

export const metadata: Metadata = { title: "Sources" };

export default function SourcesPage() {
  return <SourcesView />;
}
