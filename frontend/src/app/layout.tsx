import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Carrot Sketches - Etsy Assistant",
  description: "Process pen & ink sketches into print-ready digital downloads",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
