// app/peringatan/page.tsx — Alert Center
"use client";
import { useEffect, useState } from "react";
import { getAlerts, AlertItem, runEWS, updateAlertStatus, getClusterMonths, getAlertsExportExcelUrl } from "@/lib/api";

const STATUS_CONFIG: Record<string, { bg: string; color: string; border: string }> = {
  Baru:      { bg: "rgba(239,68,68,0.12)",  color: "#ef4444", border: "rgba(239,68,68,0.3)" },
  Ditinjau:  { bg: "rgba(245,158,11,0.12)", color: "#f59e0b", border: "rgba(245,158,11,0.3)" },
  Ditangani: { bg: "rgba(34,197,94,0.12)",  color: "#22c55e", border: "rgba(34,197,94,0.3)" },
};

export default function PeringatanPage() {
  const [data, setData]               = useState<AlertItem[]>([]);
  const [total, setTotal]             = useState(0);
  const [loading, setLoading]         = useState(true);
  const [running, setRunning]         = useState(false);
  const [statusFilter, setStatusFilter] = useState("");
  const [searchQuery, setSearchQuery]   = useState("");
  const [activeMonth, setActiveMonth]   = useState("");
  const [msg, setMsg]                   = useState("");

  // Modal Dialog Filter Kolom Ekspor Excel (kolom tanggal sudah dihilangkan)
  const [showExportModal, setShowExportModal] = useState(false);
  const [exportCols, setExportCols] = useState<{ key: string; label: string; checked: boolean }[]>([
    { key: "no", label: "Nomor Urut", checked: true },
    { key: "id_peringatan", label: "ID Alert / Peringatan", checked: true },
    { key: "kode_kabkota", label: "Kode Wilayah", checked: true },
    { key: "nama_kabkota", label: "Nama Kabupaten / Kota", checked: true },
    { key: "nama_provinsi", label: "Nama Provinsi", checked: true },
    { key: "nama_komoditas", label: "Komoditas Pangan", checked: true },
    { key: "harga_sebelumnya", label: "Harga Baseline (Rp)", checked: true },
    { key: "harga_sekarang", label: "Harga Lonjakan (Rp)", checked: true },
    { key: "persentase_lonjakan", label: "Persentase Lonjakan (%)", checked: true },
    { key: "status", label: "Status Penanganan", checked: true },
  ]);

  useEffect(() => {
    getClusterMonths()
      .then((r) => {
        const months = r.data?.data || [];
        if (months.length > 0) {
          setActiveMonth(months[months.length - 1]);
        }
      })
      .catch(console.error);

    fetchData(statusFilter);
  }, []);

  const fetchData = (status?: string) => {
    setLoading(true);
    getAlerts({
      status_filter: status || undefined,
      limit: 100,
    })
      .then((r) => {
        setData(r.data.data);
        setTotal(r.data.total);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  };

  const handleStatusChange = async (id_peringatan: number, newStatus: string) => {
    try {
      await updateAlertStatus(id_peringatan, newStatus);
      setData((prev) =>
        prev.map((item) => (item.id_peringatan === id_peringatan ? { ...item, status: newStatus } : item))
      );
    } catch (e: any) {
      alert("Gagal mengubah status: " + (e.response?.data?.detail || e.message));
    }
  };

  const handleRun = async () => {
    setRunning(true);
    setMsg("");
    try {
      const r = await runEWS();
      const n = r.data.hasil_ews?.n_peringatan_baru ?? 0;
      setMsg(`✅ Deteksi EWS selesai! Ditemukan ${n} peringatan lonjakan harga baru.`);
      fetchData(statusFilter);
    } catch (e: any) {
      setMsg("❌ " + (e.response?.data?.detail?.message || e.message));
    } finally {
      setRunning(false);
    }
  };

  // Filter data berdasarkan typing pencarian
  const filteredData = data.filter((item) => {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    return (
      item.nama_kabkota.toLowerCase().includes(q) ||
      item.nama_provinsi.toLowerCase().includes(q) ||
      item.nama_komoditas.toLowerCase().includes(q) ||
      item.status.toLowerCase().includes(q)
    );
  });

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
            <div style={{ display: "inline-flex", alignItems: "center", gap: 6, fontSize: 11, color: "#ef4444", fontWeight: 700, letterSpacing: 1, marginBottom: 6, textTransform: "uppercase" }}>
              <span>🚨</span> Early Warning System (EWS)
            </div>
            <h1 style={{ fontSize: 26, fontWeight: 800, color: "#f0f6ff", letterSpacing: -0.5, lineHeight: 1.2 }}>
              Pusat Peringatan Lonjakan Harga
            </h1>
            <p style={{ color: "#8899bb", marginTop: 6, fontSize: 13 }}>
              Daftar komoditas pangan yang mengalami kenaikan harga di atas ambang batas (threshold &gt; 15%).
            </p>
          </div>

          <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
            <button
              onClick={() => setShowExportModal(true)}
              style={{
                padding: "10px 18px",
                borderRadius: 12,
                fontWeight: 700,
                fontSize: 13,
                background: "rgba(16, 185, 129, 0.15)",
                color: "#34d399",
                border: "1px solid rgba(16, 185, 129, 0.35)",
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                gap: 8,
                transition: "all 0.2s",
              }}
              title="Atur kolom dan unduh laporan Excel (.xlsx)"
            >
              <span>📊</span>
              <span>Ekspor Excel (.xlsx)...</span>
            </button>

            <button
              onClick={handleRun}
              disabled={running}
              style={{
                padding: "10px 20px",
                borderRadius: 12,
                fontWeight: 700,
                fontSize: 13,
                background: running ? "#1e2d4a" : "linear-gradient(135deg,#ef4444,#b91c1c)",
                color: running ? "#8899bb" : "#fff",
                border: "none",
                cursor: running ? "not-allowed" : "pointer",
                boxShadow: running ? "none" : "0 4px 16px rgba(239,68,68,0.35)",
                display: "flex",
                alignItems: "center",
                gap: 8,
                transition: "all 0.2s",
              }}
            >
              <span>{running ? "⏳" : "🔍"}</span>
              <span>{running ? "Mendeteksi Lonjakan..." : "Jalankan Deteksi EWS"}</span>
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

      {/* Control Bar: Status Filter + Periode Dropdown */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: 16,
          marginBottom: 20,
        }}
      >
        {/* Status Pills */}
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          {[
            { key: "", label: "Semua Status" },
            { key: "Baru", label: "Baru" },
            { key: "Ditinjau", label: "Ditinjau" },
            { key: "Ditangani", label: "Ditangani" },
          ].map((s) => {
            const isAct = statusFilter === s.key;
            return (
              <button
                key={s.key}
                onClick={() => {
                  setStatusFilter(s.key);
                  fetchData(s.key);
                }}
                style={{
                  padding: "8px 16px",
                  borderRadius: 20,
                  fontSize: 12,
                  fontWeight: 600,
                  border: isAct ? "1px solid #3b82f6" : "1px solid #1e2d4a",
                  cursor: "pointer",
                  background: isAct ? "rgba(59,130,246,0.15)" : "#111827",
                  color: isAct ? "#93c5fd" : "#8899bb",
                  transition: "all 0.15s",
                }}
              >
                {s.label} {s.key === "" ? `(${total})` : ""}
              </button>
            );
          })}
        </div>

        {/* Status Periode Aktif */}
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
      </div>

      {/* Live Search Input Box */}
      <div style={{ marginBottom: 20 }}>
        <div
          style={{
            position: "relative",
            display: "flex",
            alignItems: "center",
            maxWidth: 480,
          }}
        >
          <span
            style={{
              position: "absolute",
              left: 14,
              fontSize: 14,
              color: "#64748b",
              pointerEvents: "none",
            }}
          >
            🔍
          </span>
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Ketik untuk mencari kota, provinsi, atau komoditas..."
            style={{
              width: "100%",
              padding: "10px 38px 10px 40px",
              background: "#111827",
              border: "1px solid #1e2d4a",
              borderRadius: 12,
              color: "#f0f6ff",
              fontSize: 13,
              outline: "none",
              boxShadow: "0 2px 8px rgba(0,0,0,0.15)",
              transition: "border-color 0.2s",
            }}
            onFocus={(e) => (e.target.style.borderColor = "#3b82f6")}
            onBlur={(e) => (e.target.style.borderColor = "#1e2d4a")}
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery("")}
              style={{
                position: "absolute",
                right: 12,
                background: "transparent",
                border: "none",
                color: "#94a3b8",
                fontSize: 14,
                cursor: "pointer",
                padding: "2px 6px",
              }}
              title="Hapus pencarian"
            >
              ✕
            </button>
          )}
        </div>
      </div>

      {/* Table Card */}
      <div
        style={{
          background: "#111827",
          border: "1px solid #1e2d4a",
          borderRadius: 18,
          overflow: "hidden",
          boxShadow: "0 4px 24px rgba(0,0,0,0.2)",
        }}
      >
        {loading ? (
          <div style={{ padding: 48, textAlign: "center", color: "#8899bb" }}>
            ⏳ Memuat daftar peringatan dini...
          </div>
        ) : !filteredData.length ? (
          <div style={{ padding: 48, textAlign: "center" }}>
            <div style={{ fontSize: 40, marginBottom: 12 }}>🛡️</div>
            <div style={{ color: "#f0f6ff", fontWeight: 700, fontSize: 16 }}>
              {searchQuery ? "Hasil Pencarian Tidak Ditemukan" : "Tidak Ada Peringatan Ditemukan"}
            </div>
            <div style={{ color: "#8899bb", fontSize: 13, marginTop: 6, maxWidth: 460, margin: "6px auto 0" }}>
              {searchQuery
                ? `Tidak ada data peringatan yang cocok dengan kata kunci "${searchQuery}".`
                : statusFilter
                ? "Tidak ada lonjakan harga yang cocok dengan filter status yang dipilih."
                : "Semua harga komoditas dalam kondisi stabil di bawah threshold 15%."}
            </div>
          </div>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
              <thead>
                <tr style={{ background: "#0d1529", borderBottom: "1px solid #1e2d4a" }}>
                  {["#", "Wilayah / Kota", "Komoditas", "Harga Lama", "Harga Baru", "Lonjakan (%)", "Tanggal Kejadian", "Tindakan / Status"].map((h) => (
                    <th
                      key={h}
                      style={{
                        textAlign: "left",
                        padding: "12px 16px",
                        color: "#8899bb",
                        fontWeight: 600,
                        fontSize: 11,
                        textTransform: "uppercase",
                        letterSpacing: 0.5,
                        whiteSpace: "nowrap",
                      }}
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {filteredData.map((a, i) => {
                  const sc = STATUS_CONFIG[a.status] || STATUS_CONFIG.Baru;
                  return (
                    <tr
                      key={a.id_peringatan}
                      style={{
                        borderTop: "1px solid #1a253d",
                        background: i % 2 === 0 ? "transparent" : "rgba(255,255,255,0.01)",
                      }}
                    >
                      <td style={{ padding: "12px 16px", color: "#64748b", fontSize: 12 }}>{i + 1}</td>
                      <td style={{ padding: "12px 16px" }}>
                        <div style={{ color: "#f0f6ff", fontWeight: 600 }}>{a.nama_kabkota}</div>
                        <div style={{ fontSize: 11, color: "#8899bb" }}>{a.nama_provinsi}</div>
                      </td>
                      <td style={{ padding: "12px 16px", color: "#f0f6ff" }}>{a.nama_komoditas}</td>
                      <td style={{ padding: "12px 16px", color: "#94a3b8" }}>
                        Rp {Math.round(a.harga_sebelumnya).toLocaleString("id-ID")}
                      </td>
                      <td style={{ padding: "12px 16px", color: "#f0f6ff", fontWeight: 700 }}>
                        Rp {Math.round(a.harga_sekarang).toLocaleString("id-ID")}
                      </td>
                      <td style={{ padding: "12px 16px" }}>
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
                      <td style={{ padding: "12px 16px", color: "#94a3b8", whiteSpace: "nowrap" }}>
                        {a.tanggal_deteksi.slice(0, 10)}
                      </td>
                      <td style={{ padding: "12px 16px" }}>
                        <select
                          value={a.status}
                          onChange={(e) => handleStatusChange(a.id_peringatan, e.target.value)}
                          style={{
                            background: sc.bg,
                            color: sc.color,
                            border: `1px solid ${sc.border}`,
                            padding: "4px 10px",
                            borderRadius: 12,
                            fontSize: 12,
                            fontWeight: 700,
                            outline: "none",
                            cursor: "pointer",
                          }}
                        >
                          <option value="Baru" style={{ background: "#111827", color: "#ef4444" }}>Baru</option>
                          <option value="Ditinjau" style={{ background: "#111827", color: "#f59e0b" }}>Ditinjau</option>
                          <option value="Ditangani" style={{ background: "#111827", color: "#22c55e" }}>Ditangani</option>
                        </select>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div style={{ marginTop: 14, fontSize: 12, color: "#8899bb", display: "flex", justifyContent: "space-between" }}>
        <span>💡 Anda dapat mengubah status peringatan langsung melalui dropdown pada baris tabel.</span>
        <span>
          Menampilkan {filteredData.length} {searchQuery ? `(dari ${data.length} hasil)` : ""} dari {total} total peringatan
        </span>
      </div>

      {/* Modal Dialog Kustomisasi Ekspor Excel */}
      {showExportModal && (
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: "rgba(0,0,0,0.75)",
            backdropFilter: "blur(4px)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 9999,
          }}
        >
          <div
            style={{
              background: "#0f172a",
              border: "1px solid #1e2d4a",
              borderRadius: 20,
              padding: "28px 32px",
              width: "100%",
              maxWidth: 520,
              boxShadow: "0 20px 40px rgba(0,0,0,0.6)",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
              <div>
                <h3 style={{ fontSize: 18, fontWeight: 700, color: "#f8fafc" }}>⚙️ Kustomisasi Kolom Ekspor</h3>
                <p style={{ fontSize: 12, color: "#94a3b8", marginTop: 4 }}>
                  Centang kolom data yang ingin dimasukkan ke file Excel (.xlsx).
                </p>
              </div>
              <button
                onClick={() => setShowExportModal(false)}
                style={{
                  background: "transparent",
                  border: "none",
                  color: "#94a3b8",
                  fontSize: 20,
                  cursor: "pointer",
                }}
              >
                ✕
              </button>
            </div>

            {/* Quick Actions */}
            <div style={{ display: "flex", gap: 10, marginBottom: 16 }}>
              <button
                onClick={() => setExportCols((prev) => prev.map((c) => ({ ...c, checked: true })))}
                style={{
                  padding: "4px 10px",
                  borderRadius: 6,
                  fontSize: 11,
                  fontWeight: 600,
                  background: "#1e293b",
                  color: "#38bdf8",
                  border: "1px solid #334155",
                  cursor: "pointer",
                }}
              >
                Pilih Semua
              </button>
              <button
                onClick={() => setExportCols((prev) => prev.map((c) => ({ ...c, checked: false })))}
                style={{
                  padding: "4px 10px",
                  borderRadius: 6,
                  fontSize: 11,
                  fontWeight: 600,
                  background: "#1e293b",
                  color: "#94a3b8",
                  border: "1px solid #334155",
                  cursor: "pointer",
                }}
              >
                Hapus Semua
              </button>
            </div>

            {/* List Checkbox Kolom */}
            <div
              style={{
                maxHeight: 280,
                overflowY: "auto",
                background: "#0b1120",
                border: "1px solid #1e293b",
                borderRadius: 12,
                padding: "12px 16px",
                display: "grid",
                gridTemplateColumns: "1fr 1fr",
                gap: "10px 14px",
                marginBottom: 24,
              }}
            >
              {exportCols.map((col) => (
                <label
                  key={col.key}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 8,
                    fontSize: 13,
                    color: col.checked ? "#f1f5f9" : "#64748b",
                    cursor: "pointer",
                    userSelect: "none",
                  }}
                >
                  <input
                    type="checkbox"
                    checked={col.checked}
                    onChange={(e) => {
                      const chk = e.target.checked;
                      setExportCols((prev) =>
                        prev.map((c) => (c.key === col.key ? { ...c, checked: chk } : c))
                      );
                    }}
                    style={{
                      width: 16,
                      height: 16,
                      accentColor: "#10b981",
                      cursor: "pointer",
                    }}
                  />
                  <span>{col.label}</span>
                </label>
              ))}
            </div>

            {/* Tombol Konfirmasi Download */}
            <div style={{ display: "flex", justifyContent: "flex-end", gap: 12 }}>
              <button
                onClick={() => setShowExportModal(false)}
                style={{
                  padding: "10px 18px",
                  borderRadius: 10,
                  fontSize: 13,
                  fontWeight: 600,
                  background: "#1e293b",
                  color: "#cbd5e1",
                  border: "1px solid #334155",
                  cursor: "pointer",
                }}
              >
                Batal
              </button>

              <button
                disabled={!exportCols.some((c) => c.checked)}
                onClick={() => {
                  const selectedKeys = exportCols.filter((c) => c.checked).map((c) => c.key);
                  const downloadUrl = getAlertsExportExcelUrl({
                    status_filter: statusFilter || undefined,
                    columns: selectedKeys,
                  });
                  window.open(downloadUrl, "_blank");
                  setShowExportModal(false);
                }}
                style={{
                  padding: "10px 22px",
                  borderRadius: 10,
                  fontSize: 13,
                  fontWeight: 700,
                  background: !exportCols.some((c) => c.checked)
                    ? "#334155"
                    : "linear-gradient(135deg,#10b981,#059669)",
                  color: "#ffffff",
                  border: "none",
                  cursor: !exportCols.some((c) => c.checked) ? "not-allowed" : "pointer",
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  boxShadow: "0 4px 14px rgba(16,185,129,0.3)",
                }}
              >
                <span>📥</span>
                <span>Unduh File Excel</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
