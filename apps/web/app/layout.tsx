import "./globals.css";
import type { ReactNode } from "react";

export const metadata = {
  title: "Clip Engine",
  description: "Authorized video clipping engine scaffold.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
