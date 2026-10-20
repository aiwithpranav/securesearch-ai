import type { Metadata } from "next";
import { DocumentDetail } from "./DocumentDetail";

export const metadata: Metadata = { title: "Document" };

export default function DocumentPage() {
  return <DocumentDetail />;
}
