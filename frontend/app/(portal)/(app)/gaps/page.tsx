import type { Metadata } from "next";
import { GapsView } from "./GapsView";

export const metadata: Metadata = { title: "Knowledge gaps" };

export default function GapsPage() {
  return <GapsView />;
}
