import "./globals.css";
import { UserProvider } from "@/lib/auth/user-context";
import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Voice Survey Console",
  description: "Configure campaigns and monitor survey outcomes."
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <UserProvider>
          <div className="min-h-screen bg-slate-50">
            <header className="border-b border-slate-200 bg-white">
              <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
                <Link href="/" className="text-lg font-semibold text-brand-700">
                  VoiceSurveyAgent
                </Link>
                <nav className="flex items-center gap-4 text-sm text-slate-700">
                  <Link href="/campaigns">Campaigns</Link>
                </nav>
              </div>
            </header>
            <main className="mx-auto max-w-6xl px-6 py-8">{children}</main>
          </div>
        </UserProvider>
      </body>
    </html>
  );
}