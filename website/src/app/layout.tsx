import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Prick & Care | India's Leading Phlebotomy Partner",
  description:
    "Partner with India's leading B2B phlebotomy service provider for diagnostic labs and hospitals.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <head>
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap"
          rel="stylesheet"
        />
        <link
          href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="bg-background-light text-slate-900 antialiased">
        <Navbar />
        <main>{children}</main>
        <Footer />
        <MobileTabBar />
      </body>
    </html>
  );
}

import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import MobileTabBar from "@/components/MobileTabBar";
