import type { Metadata } from "next";
import { SearchView } from "./SearchView";

export const metadata: Metadata = { title: "Ask" };

export default function SearchPage() {
  return <SearchView />;
}
