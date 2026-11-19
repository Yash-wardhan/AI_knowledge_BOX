import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { Suspense } from "react";
import "./globals.css";
import Sidebar, { SidebarFallback } from "@/components/Sidebar";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Knowledge Inbox",
  description: "Your personal AI knowledge assistant",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    // suppressHydrationWarning: browser extensions inject attributes on <html>/<body>
    // (e.g. ColorZilla adds cz-shortcut-listen, another adds data-qb-installed).
    // Only affects these two elements' own attributes, not their children.
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full`}
      suppressHydrationWarning
    >
      <body className="h-full flex font-sans antialiased" suppressHydrationWarning>
        {/* Sidebar reads usePathname(); on dynamic routes (/c/[sessionId]) that
            suspends during prerendering under cacheComponents, so it needs a boundary. */}
        <Suspense fallback={<SidebarFallback />}>
          <Sidebar />
        </Suspense>
        <main className="flex-1 overflow-y-auto pb-16 md:pb-0">{children}</main>
      </body>
    </html>
  );
}
