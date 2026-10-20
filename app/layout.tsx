import type { Metadata, Viewport } from "next";
import "./globals.css";

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: "#2B102B",
};

export const metadata: Metadata = {
  title: "UtsavAI — Celebration & Event Planner",
  description:
    "Editable, budget-balanced celebration plans for weddings, birthdays, and community events with deterministic accounting and Plan Rescue.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="min-h-screen antialiased bg-[#FCFAF6] text-[#2B102B]">
        {children}
      </body>
    </html>
  );
}
