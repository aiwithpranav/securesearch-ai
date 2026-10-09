import type { Metadata, Viewport } from "next";
import "./globals.css";
import { SITE_NAME, SITE_URL } from "@/lib/site";

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: { default: `${SITE_NAME}: permission-aware knowledge search`, template: `%s | ${SITE_NAME}` },
  description: "Answers from your company's documents, with sources, and only from what you have permission to read.",
  openGraph: { title: SITE_NAME, description: "Search everything you're allowed to see. Nothing you're not.", type: "website" },
};
export const viewport: Viewport = { themeColor: "#070B14", colorScheme: "dark" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <a href="#main" className="sr-only focus:not-sr-only focus:fixed focus:left-3 focus:top-3 focus:z-50 focus:rounded-lg focus:bg-accent focus:px-4 focus:py-2 focus:text-bg">Skip to content</a>
        {children}
      </body>
    </html>
  );
}
