import type { Metadata } from "next";
import type { ReactNode } from "react";

import { SessionProvider } from "@/auth/SessionProvider";

import "./globals.css";

export const metadata: Metadata = {
  title: "Ripple",
  description: "Your beliefs, why they are held, and what changed.",
  robots: { index: false, follow: false },
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <SessionProvider>{children}</SessionProvider>
      </body>
    </html>
  );
}
