// app/peta/page.tsx — Halaman WebGIS Peta Interaktif Kerawanan Pangan
"use client";
import { useEffect, useState } from "react";
import { getClusters, runClustering, getClusterMonths, getKomoditas, KlasterItem, KlasterResponse, KomoditasItem } from "@/lib/api";
import dynamic from "next/dynamic";

// Load map hanya di client (no SSR) — WAJIB untuk Leaflet
const MapComponent = dynamic(() => import("@/components/map/MapComponent"), { ssr: false });

const ZONA_COLORS: Record<string, string> = {
  Aman: "#22c55e",
  Waspada: "#f59e0b",
  Kritis: "#ef4444",
};

export default function PetaPage() {
  const [clusterData, setClusterData] = useState<KlasterResponse | null>(null);
  const [selectedCity, setSelectedCity] = useState<KlasterItem | null>(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [msg, setMsg] = useState("");

  // Filter Komoditas & Info Bulan Aktif
  const [activeMonth, setActiveMonth] = useState<string>("");
  const [komoditasList, setKomoditasList] = useState<KomoditasItem[]>([]);
  const [selectedKomoditas, setSelectedKomoditas] = useState<string>("");

  useEffect(() => {
    // Ambil info bulan dari dataset aktif
    getClusterMonths()
      .then((res) => {
        const months = res.data?.data || [];
        if (months.length > 0) {
          setActiveMonth(months[months.length - 1]);
        }
      })
      .catch(console.error);

    // Ambil daftar komoditas pangan untuk filter spesifik
    getKomoditas()
      .then((res) => {
        setKomoditasList(res.data?.data || []);
      })
      .catch(console.error);

    fetchData(selectedKomoditas);
  }, []);

  const fetchData = (komoditas?: string) => {
    setLoading(true);
    getClusters(undefined, komoditas || undefined)
      .then((r) => setClusterData(r.data))
      .catch(console.error)
      .finally(() => setLoading(false));
  };

  const handleKomoditasChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const val = e.target.value;
    setSelectedKomoditas(val);
    fetchData(val);
  };

  const handleRun = async () => {
    setRunning(true);
    setMsg("");
    try {
      await runClustering();
      setMsg("✅ K-Means Clustering selesai! Zonasi peta berhasil diperbarui.");
      fetchData(selectedKomoditas);
    } catch (e: any) {
      setMsg("❌ " + (e.response?.data?.detail?.message || e.message));
    } finally {
      setRunning(false);
    }
  };

  const s = clusterData?.summary;

  return (
    <div style={{ display: "flex", height: "100vh", flexDirection: "column" }}>
      {/* Top Bar */}
      <div
        style={{
          padding: "16px 28px",
          background: "#0d1529",
          borderBottom: "1px solid #1e2d4a",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: 12,
          zIndex: 10,
        }}
      >
        <div>
          <div style={{ display: "inline-flex", alignItems: "center", gap: 6, fontSize: 11, color: "#3b82f6", fontWeight: 700, letterSpacing: 1, textTransform: "uppercase" }}>
            <span>🗺️</span> WebGIS Pemetaan Spasial
          </div>
          <h1 style={{ fontSize: 20, fontWeight: 800, color: "#f0f6ff", letterSpacing: -0.3, marginTop: 2 }}>
            Peta Kerawanan Harga Pangan Seluruh Indonesia
          </h1>
        </div>

        <div style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
          {/* Dropdown Filter Komoditas */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              background: "#111827",
              padding: "7px 14px",
              borderRadius: 12,
              border: "1px solid #233554",
            }}
          >
            <span style={{ fontSize: 12, color: "#8899bb" }}>🌾 Komoditas:</span>
            <select
              value={selectedKomoditas}
              onChange={handleKomoditasChange}
              style={{
                background: "transparent",
                color: "#f0f6ff",
                border: "none",
                fontSize: 12,
                fontWeight: 600,
                outline: "none",
                cursor: "pointer",
                maxWidth: 160,
              }}
            >
              <option value="" style={{ background: "#111827", color: "#f0f6ff" }}>
                Semua Komoditas (Agregat)
              </option>
              {komoditasList.map((k) => (
                <option key={k.id} value={k.nama_varian} style={{ background: "#111827", color: "#f0f6ff" }}>
                  {k.nama_varian}
                </option>
              ))}
            </select>
          </div>

          {/* Status Periode Aktif */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              background: "rgba(59, 130, 246, 0.12)",
              padding: "7px 14px",
              borderRadius: 12,
              border: "1px solid rgba(59, 130, 246, 0.3)",
            }}
          >
            <span style={{ fontSize: 12 }}>📅</span>
            <span style={{ fontSize: 12, color: "#93c5fd", fontWeight: 600 }}>
              {activeMonth ? `Periode Aktif: ${activeMonth}` : "Dataset Aktif"}
            </span>
          </div>

          {/* Summary pills */}
          {s && (
            <div style={{ display: "flex", gap: 8 }}>
              {(["Aman", "Waspada", "Kritis"] as const).map((z) => (
                <div
                  key={z}
                  style={{
                    padding: "6px 14px",
                    borderRadius: 20,
                    fontSize: 12,
                    fontWeight: 700,
                    background: `${ZONA_COLORS[z]}22`,
                    color: ZONA_COLORS[z],
                    border: `1px solid ${ZONA_COLORS[z]}44`,
                  }}
                >
                  {z}: {s[z]}
                </div>
              ))}
            </div>
          )}

          <button
            onClick={handleRun}
            disabled={running}
            style={{
              padding: "8px 18px",
              borderRadius: 10,
              fontWeight: 700,
              fontSize: 12,
              background: running ? "#1e2d4a" : "linear-gradient(135deg,#3b82f6,#1d4ed8)",
              color: running ? "#8899bb" : "#fff",
              border: "none",
              cursor: running ? "not-allowed" : "pointer",
              boxShadow: running ? "none" : "0 4px 12px rgba(59,130,246,0.35)",
              display: "flex",
              alignItems: "center",
              gap: 6,
            }}
          >
            <span>{running ? "⏳" : "▶"}</span>
            <span>{running ? "Memproses..." : "Hitung Ulang Klaster"}</span>
          </button>
        </div>
      </div>

      {msg && (
        <div
          style={{
            padding: "8px 24px",
            fontSize: 12,
            background: msg.startsWith("✅") ? "rgba(34,197,94,0.12)" : "rgba(239,68,68,0.12)",
            color: msg.startsWith("✅") ? "#86efac" : "#fca5a5",
            borderBottom: "1px solid #1e2d4a",
          }}
        >
          {msg}
        </div>
      )}

      {/* Map + Side Panel */}
      <div style={{ flex: 1, display: "flex", overflow: "hidden" }}>
        {/* Map Viewport */}
        <div style={{ flex: 1, padding: 16, minHeight: 0 }}>
          {loading ? (
            <div
              style={{
                width: "100%",
                height: "100%",
                borderRadius: 16,
                background: "#111827",
                border: "1px solid #1e2d4a",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                flexDirection: "column",
                gap: 12,
              }}
            >
              <div style={{ fontSize: 36 }}>🗺️</div>
              <div style={{ color: "#8899bb", fontSize: 13 }}>Memuat koordinat geografis wilayah...</div>
            </div>
          ) : (
            <MapComponent data={clusterData?.data || []} onCityClick={setSelectedCity} />
          )}
        </div>

        {/* Side Panel: Detail Kota */}
        <div
          style={{
            width: 300,
            background: "#0d1529",
            borderLeft: "1px solid #1e2d4a",
            padding: 22,
            overflowY: "auto",
            display: "flex",
            flexDirection: "column",
          }}
        >
          <div
            style={{
              fontSize: 11,
              color: "#8899bb",
              fontWeight: 700,
              marginBottom: 16,
              textTransform: "uppercase",
              letterSpacing: 1,
            }}
          >
            Informasi Wilayah
          </div>

          {!selectedCity ? (
            <div
              style={{
                color: "#8899bb",
                fontSize: 13,
                textAlign: "center",
                padding: "48px 12px",
                background: "#111827",
                borderRadius: 14,
                border: "1px dashed #233554",
              }}
            >
              <div style={{ fontSize: 28, marginBottom: 8 }}>👆</div>
              Klik salah satu titik lingkaran pada peta untuk melihat detail zonasi wilayah.
            </div>
          ) : (
            <div>
              <div
                style={{
                  background: "#111827",
                  borderRadius: 14,
                  padding: 16,
                  border: `1px solid ${ZONA_COLORS[selectedCity.status_zona]}44`,
                  marginBottom: 14,
                }}
              >
                <div style={{ fontWeight: 800, fontSize: 16, color: "#f0f6ff", marginBottom: 4 }}>
                  {selectedCity.nama_kabkota}
                </div>
                <div style={{ fontSize: 12, color: "#8899bb", marginBottom: 12 }}>
                  Provinsi {selectedCity.nama_provinsi}
                </div>
                <div
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: 6,
                    padding: "6px 14px",
                    borderRadius: 20,
                    fontSize: 12,
                    fontWeight: 800,
                    background: `${ZONA_COLORS[selectedCity.status_zona]}22`,
                    color: ZONA_COLORS[selectedCity.status_zona],
                    border: `1px solid ${ZONA_COLORS[selectedCity.status_zona]}44`,
                  }}
                >
                  {selectedCity.status_zona === "Aman" ? "✅" : selectedCity.status_zona === "Waspada" ? "⚠️" : "🔴"}
                  {" "}
                  {selectedCity.status_zona}
                </div>
              </div>

              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {[
                  { label: "Kode Wilayah", val: selectedCity.kode_kabkota },
                  { label: "Cluster Model", val: `Klaster #${selectedCity.cluster_id}` },
                  { label: "Latitude", val: selectedCity.latitude?.toFixed(4) || "-" },
                  { label: "Longitude", val: selectedCity.longitude?.toFixed(4) || "-" },
                  { label: "Tanggal Evaluasi", val: selectedCity.tanggal_proses?.slice(0, 10) || "-" },
                ].map(({ label, val }) => (
                  <div
                    key={label}
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      padding: "8px 12px",
                      background: "#111827",
                      borderRadius: 8,
                      border: "1px solid #1a253d",
                    }}
                  >
                    <span style={{ fontSize: 11, color: "#8899bb" }}>{label}</span>
                    <span style={{ fontSize: 11, color: "#f0f6ff", fontWeight: 600 }}>{val}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* List Kota Kritis Cepat */}
          <div style={{ marginTop: 24, flex: 1 }}>
            <div
              style={{
                fontSize: 11,
                color: "#f87171",
                fontWeight: 700,
                marginBottom: 10,
                textTransform: "uppercase",
                letterSpacing: 0.8,
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
              }}
            >
              <span>🔴 Daftar Wilayah Kritis</span>
              <span style={{ fontSize: 10, color: "#8899bb" }}>
                ({clusterData?.data.filter((d) => d.status_zona === "Kritis").length || 0})
              </span>
            </div>

            <div style={{ maxHeight: 280, overflowY: "auto", display: "flex", flexDirection: "column", gap: 6 }}>
              {clusterData?.data.filter((d) => d.status_zona === "Kritis").map((city) => (
                <div
                  key={city.kode_kabkota}
                  onClick={() => setSelectedCity(city)}
                  style={{
                    padding: "8px 12px",
                    borderRadius: 8,
                    cursor: "pointer",
                    background: selectedCity?.kode_kabkota === city.kode_kabkota ? "rgba(239,68,68,0.2)" : "#111827",
                    border: "1px solid rgba(239,68,68,0.3)",
                    transition: "all 0.15s",
                  }}
                >
                  <div style={{ fontSize: 12, color: "#f0f6ff", fontWeight: 600 }}>{city.nama_kabkota}</div>
                  <div style={{ fontSize: 10, color: "#8899bb" }}>{city.nama_provinsi}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
