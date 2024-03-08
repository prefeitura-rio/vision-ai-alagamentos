import type { Metadata } from "next";
import { Inter } from "next/font/google";

import "./globals.css";
import SideMenu from "@/components/SideMenu";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Vision AI",
  description: "Desenvolvido pelo Escritório de Dados",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <SideMenu />
      <body className={inter.className}>{children}</body>
    </html>
  );
}
