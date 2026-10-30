// app/page.tsx — Dashboard Utama Ringkasan Analitik Spasial
"use client";
import { useEffect, useState } from "react";
import StatCard from "@/components/ui/StatCard";
import {
  getClusters,
  getAlerts,
  runClustering,
  runEWS,
  getClusterMonths,
  KlasterResponse,
  AlertResponse,
} from "@/lib/api";
import Link from "next/link";

export default function DashboardPage() {
  const [clusters, setClusters] = useState<KlasterResponse | null>(null);
  const [alerts, setAlerts] = useState<AlertResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [msg, setMsg] = useState("");
  const [activeMonth, setActiveMonth] = useState<string>("");

  useEffect(() => {
    getClusterMonths()
      .then((res) => {
        const months = res.data?.data || [];
        if (months.length > 0) {
          setActiveMonth(months[months.length - 1]);
        }
      })
      .catch(console.error);

    fetchDashboardData();
  }, []);

  const fetchDashboardData = () => {
    setLoading(true);
    Promise.all([
      getClusters(),
      getAlerts({ limit: 6 }),
    ])
      .then(([c, a]) => {
        setClusters(c.data);
        setAlerts(a.data);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  };

  const handleRunAll = async () => {
    setRunning(true);
    setMsg("");
    try {
      await runClustering();
      await runEWS();
      setMsg("✅ K-Means Clustering & EWS berhasil dihitung ulang untuk dataset aktif!");
      fetchDashboardData();
    } catch (e: any) {
      setMsg("❌ " + (e.response?.data?.detail?.message || e.message));
    } finally {
      setRunning(false);
    }
  };

  const s = clusters?.summary;

  return (
    <div style={{ padding: "32px 36px 48px", maxWidth: 1300 }}>
      {/* Top Header Card */}
      <div
        style={{
          background: "linear-gradient(135deg, rgba(13, 21, 41, 0.8) 0%, rgba(19, 28, 49, 0.9) 100%)",
          border: "1px solid #1e2d4a",
          borderRadius: 20,
          padding: "24px 28px",
          marginBottom: 28,
          boxShadow: "0 8px 32px rgba(0,0,0,0.25)",
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 16 }}>
          <div>
            <div style={{ display: "inline-flex", alignItems: "center", gap: 6, fontSize: 11, color: "#3b82f6", fontWeight: 700, letterSpacing: 1, marginBottom: 6, textTransform: "uppercase" }}>
              <span>🌾</span> Tugas Akhir Sistem Informasi · 2026
            </div>
            <h1 style={{ fontSize: 26, fontWeight: 800, color: "#f0f6ff", letterSpacing: -0.5, lineHeight: 1.2 }}>
              Dashboard Pemantauan Kerawanan Pangan
            </h1>
            <p style={{ color: "#8899bb", marginTop: 6, fontSize: 13 }}>
              Sistem peringatan dini spasial berbasis algoritma <strong style={{ color: "#93c5fd" }}>K-Means Clustering</strong> dengan analisis multivariat komoditas pangan.
            </p>
          </div>

          <div style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
            {/* Status Dataset Aktif */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                background: "rgba(59, 130, 246, 0.12)",
                padding: "8px 16px",
                borderRadius: 12,
                border: "1px solid rgba(59, 130, 246, 0.3)",
              }}
            >
              <span style={{ fontSize: 13 }}>📅</span>
              <span style={{ fontSize: 12, color: "#93c5fd", fontWeight: 600 }}>
                {activeMonth ? `Periode Aktif: ${activeMonth}` : "Dataset Aktif"}
              </span>
            </div>

            <button
              onClick={handleRunAll}
              disabled={running}
              style={{
                padding: "10px 20px",
                borderRadius: 12,
                fontWeight: 700,
                fontSize: 13,
                background: running ? "#1e2d4a" : "linear-gradient(135deg,#3b82f6,#1d4ed8)",
                color: running ? "#8899bb" : "#fff",
                border: "none",
                cursor: running ? "not-allowed" : "pointer",
                boxShadow: running ? "none" : "0 4px 16px rgba(59,130,246,0.35)",
                display: "flex",
                alignItems: "center",
                gap: 8,
                transition: "all 0.2s",
              }}
            >
              <span>{running ? "⏳" : "⚡"}</span>
              <span>{running ? "Menghitung K-Means..." : "Jalankan Analisis"}</span>
            </button>
          </div>
        </div>

        {msg && (
          <div
            style={{
              marginTop: 16,
              padding: "10px 16px",
              borderRadius: 10,
              fontSize: 13,
              background: msg.startsWith("✅") ? "rgba(34,197,94,0.12)" : "rgba(239,68,68,0.12)",
              border: `1px solid ${msg.startsWith("✅") ? "rgba(34,197,94,0.3)" : "rgba(239,68,68,0.3)"}`,
              color: msg.startsWith("✅") ? "#86efac" : "#fca5a5",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
            }}
          >
            <span>{msg}</span>
            <button onClick={() => setMsg("")} style={{ background: "transparent", border: "none", color: "inherit", cursor: "pointer", fontWeight: 700 }}>✕</button>
          </div>
        )}
      </div>

      {/* Stat Cards Grid */}
      {loading ? (
        <div style={{ padding: "40px 0", textAlign: "center", color: "#8899bb", fontSize: 14 }}>
          ⏳ Memuat data analisis wilayah...
        </div>
      ) : (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(190px, 1fr))",
            gap: 16,
            marginBottom: 32,
          }}
        >
          <StatCard
            label="Riwayat Harga"
            value={s?.total_records?.toLocaleString("id-ID") ?? "0"}
            icon="📚"
            color="blue"
            sub={activeMonth ? `Data periode ${activeMonth}` : "Total tersimpan di DB"}
          />
          <StatCard
            label="Kota Terpantau"
            value={s?.total ?? 0}
            icon="🏙️"
            color="purple"
            sub="Kabupaten/Kota se-Indonesia"
          />
          <StatCard
            label="Zona AMAN"
            value={s?.Aman ?? 0}
            icon="✅"
            color="green"
            sub="Harga stabil & terkendali"
          />
          <StatCard
            label="Zona WASPADA"
            value={s?.Waspada ?? 0}
            icon="⚠️"
            color="yellow"
            sub="Harga mulai bergejolak"
          />
          <StatCard
            label="Zona KRITIS"
            value={s?.Kritis ?? 0}
            icon="🔴"
            color="red"
            sub="Fluktuasi harga tinggi"
          />
          <StatCard
            label="Peringatan Lonjakan"
            value={alerts?.total ?? 0}
            icon="🚨"
            color="red"
            sub="Lonjakan harga > 15%"
          />
        </div>
      )}

      {/* Grid: Alert Preview & Shortcut Nav */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr", gap: 24 }}>
        {/* Alert Table Card */}
        <div
          style={{
            background: "#111827",
            border: "1px solid #1e2d4a",
            borderRadius: 18,
            padding: "24px 26px",
            boxShadow: "0 4px 24px rgba(0,0,0,0.2)",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
            <div>
              <h2 style={{ fontSize: 16, fontWeight: 700, color: "#f0f6ff", display: "flex", alignItems: "center", gap: 8 }}>
                <span>🚨</span> Deteksi Peringatan Lonjakan Harga Terbaru
              </h2>
              <p style={{ fontSize: 12, color: "#8899bb", marginTop: 4 }}>
                Komoditas pangan dengan kenaikan harga signifikan melebihi batas toleransi 15%.
              </p>
            </div>
            <Link
              href="/peringatan"
              style={{
                fontSize: 12,
                fontWeight: 600,
                color: "#3b82f6",
                textDecoration: "none",
                padding: "6px 12px",
                borderRadius: 8,
                background: "rgba(59,130,246,0.1)",
                border: "1px solid rgba(59,130,246,0.2)",
              }}
            >
              Buka Alert Center ({alerts?.total ?? 0}) →
            </Link>
          </div>

          {!alerts?.data.length ? (
            <div style={{ color: "#8899bb", fontSize: 13, textAlign: "center", padding: "40px 0" }}>
              Tidak ada lonjakan harga yang terdeteksi untuk periode ini.
            </div>
          ) : (
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                <thead>
                  <tr style={{ borderBottom: "1px solid #1e2d4a", background: "#0d1529" }}>
                    {["Wilayah / Kota", "Komoditas", "Harga Sebelumnya", "Harga Baru", "Lonjakan (%)", "Tanggal Kejadian", "Status"].map((h) => (
                      <th
                        key={h}
                        style={{
                          textAlign: "left",
                          padding: "10px 14px",
                          color: "#8899bb",
                          fontWeight: 600,
                          fontSize: 11,
                          textTransform: "uppercase",
                          letterSpacing: 0.5,
                        }}
                      >
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {alerts.data.map((a) => (
                    <tr key={a.id_peringatan} style={{ borderBottom: "1px solid #1a253d" }}>
                      <td style={{ padding: "12px 14px", color: "#f0f6ff", fontWeight: 600 }}>
                        <div>{a.nama_kabkota}</div>
                        <div style={{ fontSize: 11, color: "#8899bb", fontWeight: 400 }}>{a.nama_provinsi}</div>
                      </td>
                      <td style={{ padding: "12px 14px", color: "#e2e8f0" }}>{a.nama_komoditas}</td>
                      <td style={{ padding: "12px 14px", color: "#94a3b8" }}>
                        Rp {Math.round(a.harga_sebelumnya).toLocaleString("id-ID")}
                      </td>
                      <td style={{ padding: "12px 14px", color: "#f0f6ff", fontWeight: 700 }}>
                        Rp {Math.round(a.harga_sekarang).toLocaleString("id-ID")}
                      </td>
                      <td style={{ padding: "12px 14px" }}>
                        <span
                          style={{
                            background: "rgba(239,68,68,0.15)",
                            color: "#ef4444",
                            padding: "3px 10px",
                            borderRadius: 20,
                            fontSize: 12,
                            fontWeight: 800,
                            display: "inline-block",
                          }}
                        >
                          +{a.persentase_lonjakan.toFixed(1)}%
                        </span>
                      </td>
                      <td style={{ padding: "12px 14px", color: "#94a3b8", whiteSpace: "nowrap" }}>
                        {a.tanggal_deteksi.slice(0, 10)}
                      </td>
                      <td style={{ padding: "12px 14px" }}>
                        <span
                          style={{
                            padding: "3px 10px",
                            borderRadius: 12,
                            fontSize: 11,
                            fontWeight: 700,
                            background: a.status === "Ditangani" ? "rgba(34,197,94,0.15)" : a.status === "Ditinjau" ? "rgba(245,158,11,0.15)" : "rgba(239,68,68,0.15)",
                            color: a.status === "Ditangani" ? "#22c55e" : a.status === "Ditinjau" ? "#f59e0b" : "#ef4444",
                          }}
                        >
                          {a.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
