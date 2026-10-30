// components/layout/Sidebar.tsx
"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";

const navItems = [
  { href: "/",          icon: "📊", label: "Dashboard"        },
  { href: "/peta",      icon: "🗺️",  label: "Peta WebGIS"     },
  { href: "/peringatan",icon: "🚨", label: "Alert Center"     },
  { href: "/analitik",  icon: "📈", label: "Analitik Tren"    },
  { href: "/upload",    icon: "📤", label: "Upload Data"      },
];

export default function Sidebar() {
  const pathname = usePathname();
  return (
    <aside style={{
      width: 240, minHeight: "100vh", background: "#0d1529",
      borderRight: "1px solid #1e2d4a", display: "flex",
      flexDirection: "column", padding: "0",
      position: "fixed", top: 0, left: 0, zIndex: 100,
    }}>
      {/* Logo */}
      <div style={{ padding: "24px 20px 20px", borderBottom: "1px solid #1e2d4a" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <div style={{
            width: 38, height: 38, borderRadius: 10,
            background: "linear-gradient(135deg,#3b82f6,#1d4ed8)",
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: 18, boxShadow: "0 4px 12px rgba(59,130,246,0.4)",
          }}>🌾</div>
          <div>
            <div style={{ fontWeight: 800, fontSize: 14, color: "#f0f6ff", lineHeight: 1.2 }}>
              PANGAN
            </div>
            <div style={{ fontWeight: 800, fontSize: 14, color: "#3b82f6", lineHeight: 1.2 }}>
              WATCHER
            </div>
          </div>
        </div>
        <div style={{ marginTop: 8, fontSize: 10, color: "#8899bb", lineHeight: 1.4 }}>
          Sistem Peringatan Dini<br />Kerawanan Harga Pangan
        </div>
      </div>

      {/* Nav Items */}
      <nav style={{ flex: 1, padding: "16px 12px" }}>
        <div style={{ fontSize: 10, color: "#8899bb", padding: "0 8px 8px", letterSpacing: 1, textTransform: "uppercase" }}>
          Menu Utama
        </div>
        {navItems.map((item) => {
          const isActive = pathname === item.href;
          return (
            <Link key={item.href} href={item.href} style={{
              display: "flex", alignItems: "center", gap: 12,
              padding: "10px 12px", borderRadius: 10, marginBottom: 4,
              textDecoration: "none", transition: "all 0.2s",
              background: isActive
                ? "linear-gradient(135deg,rgba(59,130,246,0.2),rgba(29,78,216,0.1))"
                : "transparent",
              border: isActive ? "1px solid rgba(59,130,246,0.3)" : "1px solid transparent",
              color: isActive ? "#f0f6ff" : "#8899bb",
            }}>
              <span style={{ fontSize: 16 }}>{item.icon}</span>
              <span style={{ fontSize: 13, fontWeight: isActive ? 600 : 400 }}>{item.label}</span>
              {isActive && (
                <div style={{
                  marginLeft: "auto", width: 6, height: 6,
                  borderRadius: "50%", background: "#3b82f6",
                  boxShadow: "0 0 8px #3b82f6",
                }} />
              )}
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div style={{ padding: "16px 20px", borderTop: "1px solid #1e2d4a", fontSize: 10, color: "#8899bb" }}>
        <div style={{ fontWeight: 600, color: "#f0f6ff", marginBottom: 2 }}>Tugas Akhir 2026</div>
        <div>Sistem Informasi</div>
        <div style={{ marginTop: 4, color: "#3b82f6" }}>K-Means Clustering</div>
      </div>
    </aside>
  );
}
