import "./globals.css";
import Link from "next/link";
import type { ReactNode } from "react";
import { ToastProvider } from "@/components/ToastProvider";

export const metadata = {
  title: "Research Scout",
  description: "Personal research workspace for sources, evidence, notes, and update history.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <ToastProvider>
          <div className="min-h-screen">
            <header className="border-b border-stone-200/80 bg-white/80 backdrop-blur">
              <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
                <Link href="/" className="text-lg font-semibold">
                  Research Scout
                </Link>
                <nav className="flex items-center gap-3 text-sm text-slate-600">
                  <Link href="/">Dashboard</Link>
                  <Link href="/digests">Digests</Link>
                  <Link href="/papers">Papers</Link>
                  <Link href="/projects">Projects</Link>
                  <Link href="/projects/new">New Project</Link>
                  <Link href="/login">Login</Link>
                </nav>
              </div>
            </header>
            <main className="mx-auto max-w-7xl px-6 py-8">{children}</main>
          </div>
        </ToastProvider>
      </body>
    </html>
  );
}
