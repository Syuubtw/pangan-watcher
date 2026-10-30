import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import Sidebar from "@/components/layout/Sidebar";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Pangan Watcher - Sistem Peringatan Dini Harga Komoditas",
  description:
    "Sistem Pemetaan Spasial dan Peringatan Dini Kerawanan Harga Komoditas Pangan menggunakan K-Means Clustering. Tugas Akhir Sistem Informasi.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="id">
      <body className={inter.className} style={{ display: "flex", minHeight: "100vh", background: "#0a0f1e" }}>
        <Sidebar />
        <main style={{ marginLeft: 240, flex: 1, minHeight: "100vh", overflowX: "hidden" }}>
          {children}
        </main>
      </body>
    </html>
  );
}
