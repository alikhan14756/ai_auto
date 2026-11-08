import type { Metadata } from "next";
import "./globals.css";
import { AppShell } from "@/components/layout/AppShell";

export const metadata: Metadata = {
  title: "Creator Studio AI — Autonomous YouTube Production",
  description:
    "Autonomous, Full-Lifecycle Faceless YouTube Production Platform engineered for Solo Builders and Creators.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className="bg-canvas-base text-zinc-100 antialiased selection:bg-ember/30 selection:text-ember">
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
