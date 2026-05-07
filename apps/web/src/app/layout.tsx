import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "LLM YouTube Landscape Tracker",
  description: "Transcript-grounded tracker for LLM-focused YouTube channels."
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
