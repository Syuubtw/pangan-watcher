// app/upload/page.tsx — Halaman Upload Data Excel & Manajemen Data
"use client";
import { useState, useRef } from "react";
import { uploadExcel, resetAllData } from "@/lib/api";
import Link from "next/link";

export default function UploadPage() {
  const fileRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [drag, setDrag] = useState(false);

  // State untuk Reset Data
  const [resetting, setResetting] = useState(false);
  const [resetMessage, setResetMessage] = useState<string | null>(null);
  const [showConfirmModal, setShowConfirmModal] = useState(false);
  const [confirmInput, setConfirmInput] = useState("");

  const handleFile = (f: File) => {
    if (!f.name.endsWith(".xlsx") && !f.name.endsWith(".xls")) {
      alert("Format tidak valid! Hanya file spreadsheet Excel (.xlsx atau .xls) yang didukung.");
      return;
    }
    setFile(f);
    setResult(null);
  };

  const handleUpload = async () => {
    if (!file) return;
    setLoading(true);
    setResult(null);
    try {
      const r = await uploadExcel(file);
      setResult({ success: true, data: r.data });
    } catch (e: any) {
      setResult({ success: false, error: e.response?.data?.detail || e.message });
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setConfirmInput("");
    setShowConfirmModal(true);
  };

  const executeReset = async () => {
    setShowConfirmModal(false);
    setResetting(true);
    setResetMessage(null);
    setResult(null);
    try {
      const res = await resetAllData();
      setResetMessage(res.data?.message || "Seluruh data transaksi harga berhasil direset ke 0.");
      setFile(null);
      if (fileRef.current) fileRef.current.value = "";
    } catch (e: any) {
      alert("Gagal melakukan reset: " + (e.response?.data?.detail || e.message));
    } finally {
      setResetting(false);
    }
  };

  const fileSizeMb = file ? Math.round((file.size / (1024 * 1024)) * 10) / 10 : 0;

  return (
    <div style={{ padding: "32px 36px 48px", maxWidth: 1000 }}>
      {/* Header Card */}
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
        <div style={{ display: "inline-flex", alignItems: "center", gap: 6, fontSize: 11, color: "#3b82f6", fontWeight: 700, letterSpacing: 1, marginBottom: 6, textTransform: "uppercase" }}>
          <span>📤</span> Data Ingestion Pipeline
        </div>
        <h1 style={{ fontSize: 26, fontWeight: 800, color: "#f0f6ff", letterSpacing: -0.5, lineHeight: 1.2 }}>
          Unggah & Kelola Dataset Harga Pangan
        </h1>
        <p style={{ color: "#8899bb", marginTop: 6, fontSize: 13 }}>
          Impor file spreadsheet Excel (.xlsx) untuk menambahkan data harga harian secara akumulatif. Sistem akan menjalankan algoritma K-Means Clustering dan deteksi EWS secara otomatis setelah upload.
        </p>
      </div>

      {/* Alert Notifikasi Reset Berhasil */}
      {resetMessage && (
        <div
          style={{
            background: "rgba(34,197,94,0.12)",
            border: "1px solid rgba(34,197,94,0.3)",
            borderRadius: 14,
            padding: "16px 20px",
            marginBottom: 24,
            color: "#86efac",
            fontSize: 13,
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <span style={{ fontSize: 18 }}>🧹</span>
            <span>{resetMessage} Database saat ini dalam kondisi kosong (0 data) dan siap menerima upload baru.</span>
          </div>
          <button
            onClick={() => setResetMessage(null)}
            style={{
              background: "transparent",
              border: "none",
              color: "#86efac",
              cursor: "pointer",
              fontWeight: 700,
              fontSize: 16,
            }}
          >
            ✕
          </button>
        </div>
      )}

      {/* Drag & Drop Upload Zone */}
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDrag(true);
        }}
        onDragLeave={() => setDrag(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDrag(false);
          const f = e.dataTransfer.files[0];
          if (f) handleFile(f);
        }}
        onClick={() => fileRef.current?.click()}
        style={{
          border: `2px dashed ${drag ? "#3b82f6" : "#233554"}`,
          borderRadius: 20,
          padding: "48px 24px",
          textAlign: "center",
          background: drag ? "rgba(59,130,246,0.08)" : "#111827",
          cursor: "pointer",
          transition: "all 0.2s ease",
          marginBottom: 24,
          boxShadow: "0 4px 20px rgba(0,0,0,0.15)",
        }}
      >
        <input
          ref={fileRef}
          type="file"
          accept=".xlsx,.xls"
          style={{ display: "none" }}
          onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
        />
        <div style={{ fontSize: 44, marginBottom: 12 }}>📁</div>
        <div style={{ fontSize: 16, fontWeight: 700, color: "#f0f6ff", marginBottom: 6 }}>
          {file ? file.name : "Tarik & Lepaskan File Excel atau Klik untuk Memilih"}
        </div>
        <div style={{ fontSize: 12, color: "#8899bb" }}>
          {file
            ? `${fileSizeMb} MB — File siap diunggah dan dianalisis`
            : "Format file: .xlsx atau .xls | Ukuran maksimal hingga 200 MB"}
        </div>
      </div>

      {/* Format Kolom Standar */}
      <div
        style={{
          background: "rgba(59,130,246,0.06)",
          border: "1px solid rgba(59,130,246,0.2)",
          borderRadius: 14,
          padding: "16px 20px",
          marginBottom: 24,
        }}
      >
        <div style={{ fontSize: 12, fontWeight: 700, color: "#93c5fd", marginBottom: 10, display: "flex", alignItems: "center", gap: 6 }}>
          <span>📋</span> Format Kolom Dataset yang Dikenali Sistem
        </div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          {[
            "Kode Provinsi",
            "Nama Provinsi",
            "Kode Kab/Kota",
            "Nama Kab/Kota",
            "Nama Varian",
            "Tanggal (DD-MM-YYYY)",
            "Harga",
            "Satuan",
          ].map((c) => (
            <span
              key={c}
              style={{
                padding: "4px 10px",
                borderRadius: 6,
                fontSize: 11,
                fontWeight: 600,
                background: "rgba(59,130,246,0.12)",
                color: "#93c5fd",
                border: "1px solid rgba(59,130,246,0.25)",
              }}
            >
              {c}
            </span>
          ))}
        </div>
      </div>

      {/* Tombol Upload */}
      {file && !result && (
        <button
          onClick={handleUpload}
          disabled={loading}
          style={{
            width: "100%",
            padding: "16px",
            borderRadius: 12,
            fontWeight: 700,
            fontSize: 14,
            background: loading ? "#1e2d4a" : "linear-gradient(135deg,#3b82f6,#1d4ed8)",
            color: loading ? "#8899bb" : "#fff",
            border: "none",
            cursor: loading ? "not-allowed" : "pointer",
            boxShadow: loading ? "none" : "0 4px 20px rgba(59,130,246,0.4)",
            marginBottom: 28,
            transition: "all 0.2s",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: 10,
          }}
        >
          <span>{loading ? "⏳" : "🚀"}</span>
          <span>{loading ? "Memproses Data & Menghitung K-Means + EWS..." : "Unggah & Jalankan Analisis Otomatis"}</span>
        </button>
      )}

      {/* Result Card */}
      {result && (
        <div
          style={{
            background: result.success ? "rgba(34,197,94,0.06)" : "rgba(239,68,68,0.06)",
            border: `1px solid ${result.success ? "rgba(34,197,94,0.3)" : "rgba(239,68,68,0.3)"}`,
            borderRadius: 18,
            padding: 24,
            marginBottom: 32,
          }}
        >
          {result.success ? (
            <>
              <div style={{ fontSize: 16, fontWeight: 700, color: "#4ade80", marginBottom: 16, display: "flex", alignItems: "center", gap: 8 }}>
                <span>✅</span> Proses Ingestion & Pemodelan Berhasil!
              </div>

              {/* Status Ringkasan */}
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))",
                  gap: 12,
                  marginBottom: 16,
                }}
              >
                {[
                  { label: "Baris File Dibaca", val: result.data.ingestion_summary?.total_rows_read?.toLocaleString() },
                  { label: "Data File Disimpan", val: result.data.ingestion_summary?.rows_inserted?.toLocaleString() },
                  { label: "Total Akumulasi DB", val: result.data.ingestion_summary?.total_records_in_db?.toLocaleString() },
                  { label: "Provinsi Masuk", val: result.data.ingestion_summary?.provinsi_upserted },
                  { label: "Kab/Kota Masuk", val: result.data.ingestion_summary?.kabkota_upserted },
                  { label: "Komoditas Masuk", val: result.data.ingestion_summary?.komoditas_upserted },
                ].map(({ label, val }) => (
                  <div
                    key={label}
                    style={{
                      background: "#111827",
                      borderRadius: 12,
                      padding: "12px 16px",
                      border: "1px solid #1e2d4a",
                    }}
                  >
                    <div style={{ fontSize: 10, color: "#8899bb", marginBottom: 4, textTransform: "uppercase", fontWeight: 600 }}>
                      {label}
                    </div>
                    <div style={{ fontSize: 20, fontWeight: 800, color: "#f0f6ff" }}>{val ?? "-"}</div>
                  </div>
                ))}
              </div>

              {/* Status Auto-Analysis K-Means & EWS */}
              {result.data.auto_analysis && (
                <div
                  style={{
                    background: "rgba(59,130,246,0.1)",
                    border: "1px solid rgba(59,130,246,0.25)",
                    borderRadius: 12,
                    padding: "14px 18px",
                    marginBottom: 18,
                    fontSize: 13,
                    color: "#93c5fd",
                  }}
                >
                  <div style={{ fontWeight: 700, marginBottom: 6 }}>🤖 Status Eksekusi Otomatis:</div>
                  <div style={{ marginBottom: 4 }}>• <strong>K-Means Clustering:</strong> {result.data.auto_analysis.kmeans || "Selesai"}</div>
                  <div>• <strong>Early Warning System (EWS):</strong> {result.data.auto_analysis.ews || "Selesai"}</div>
                </div>
              )}

              {/* Tombol Akses Cepat */}
              <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
                <Link
                  href="/"
                  style={{
                    padding: "10px 18px",
                    borderRadius: 10,
                    fontSize: 13,
                    fontWeight: 700,
                    background: "#3b82f6",
                    color: "#fff",
                    textDecoration: "none",
                  }}
                >
                  📊 Buka Dashboard Utama
                </Link>
                <Link
                  href="/peta"
                  style={{
                    padding: "10px 18px",
                    borderRadius: 10,
                    fontSize: 13,
                    fontWeight: 700,
                    background: "#10b981",
                    color: "#fff",
                    textDecoration: "none",
                  }}
                >
                  🗺️ Buka Peta WebGIS
                </Link>
              </div>
            </>
          ) : (
            <div>
              <div style={{ fontSize: 16, fontWeight: 700, color: "#ef4444", marginBottom: 8 }}>❌ Proses Upload Gagal</div>
              <pre style={{ fontSize: 12, color: "#8899bb", whiteSpace: "pre-wrap", background: "#111827", padding: 12, borderRadius: 8 }}>
                {JSON.stringify(result.error, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}

      {/* Danger Zone: Reset Data */}
      <div
        style={{
          marginTop: 36,
          background: "rgba(239,68,68,0.04)",
          border: "1px solid rgba(239,68,68,0.25)",
          borderRadius: 18,
          padding: 24,
        }}
      >
        <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 16, flexWrap: "wrap" }}>
          <div>
            <div style={{ fontSize: 15, fontWeight: 700, color: "#f87171", marginBottom: 4, display: "flex", alignItems: "center", gap: 8 }}>
              ⚠️ Zona Bahaya: Reset Database ke Kondisi Bersih
            </div>
            <p style={{ fontSize: 13, color: "#9ca3af", margin: 0, maxWidth: 560, lineHeight: 1.5 }}>
              Mengosongkan seluruh riwayat harga harian, zonasi klaster K-Means, dan catatan log lonjakan harga (EWS). Gunakan fungsi ini jika Anda ingin melakukan pengujian demo sidang skripsi dari kondisi awal tanpa data transaksi lama.
            </p>
          </div>
          <button
            onClick={handleReset}
            disabled={resetting}
            style={{
              padding: "12px 20px",
              borderRadius: 10,
              fontSize: 13,
              fontWeight: 700,
              background: resetting ? "#374151" : "rgba(239,68,68,0.15)",
              color: resetting ? "#9ca3af" : "#ef4444",
              border: "1px solid #ef4444",
              cursor: resetting ? "not-allowed" : "pointer",
              transition: "all 0.2s",
              whiteSpace: "nowrap",
            }}
          >
            {resetting ? "⏳ Sedang Mengosongkan..." : "🗑️ Reset Database ke 0"}
          </button>
        </div>
      </div>

      {/* Modal Dialog Konfirmasi Reset Bertingkat */}
      {showConfirmModal && (
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: "rgba(0,0,0,0.8)",
            backdropFilter: "blur(5px)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 9999,
          }}
        >
          <div
            style={{
              background: "#0f172a",
              border: "1px solid rgba(239,68,68,0.4)",
              borderRadius: 20,
              padding: "28px 32px",
              maxWidth: 480,
              width: "100%",
              boxShadow: "0 24px 48px rgba(239,68,68,0.2)",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 16 }}>
              <div
                style={{
                  width: 44,
                  height: 44,
                  borderRadius: 12,
                  background: "rgba(239,68,68,0.15)",
                  color: "#ef4444",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontSize: 22,
                }}
              >
                ⚠️
              </div>
              <div>
                <h3 style={{ fontSize: 18, fontWeight: 800, color: "#f87171", margin: 0 }}>
                  Konfirmasi Pengosongan Data
                </h3>
                <span style={{ fontSize: 12, color: "#94a3b8" }}>Aksi ini bersifat permanen & tidak dapat dibatalkan</span>
              </div>
            </div>

            <div
              style={{
                background: "rgba(239,68,68,0.08)",
                border: "1px solid rgba(239,68,68,0.2)",
                borderRadius: 12,
                padding: "12px 16px",
                fontSize: 13,
                color: "#cbd5e1",
                lineHeight: 1.6,
                marginBottom: 20,
              }}
            >
              Data yang akan dikosongkan ke 0:
              <ul style={{ margin: "6px 0 0 18px", padding: 0 }}>
                <li>Semua riwayat transaksi harga harian</li>
                <li>Semua hasil klasterisasi spasial K-Means</li>
                <li>Semua log peringatan dini (EWS)</li>
              </ul>
              <div style={{ marginTop: 8, fontSize: 11, color: "#94a3b8" }}>
                ℹ️ Data master wilayah (514 kabupaten/kota) dan koordinat peta tidak akan terhapus.
              </div>
            </div>

            <p style={{ fontSize: 12, color: "#94a3b8", marginBottom: 8 }}>
              Ketik kata <strong style={{ color: "#ef4444", letterSpacing: 0.5 }}>RESET</strong> di bawah untuk melanjutkan:
            </p>

            <input
              type="text"
              value={confirmInput}
              onChange={(e) => setConfirmInput(e.target.value)}
              placeholder="Ketik RESET"
              style={{
                width: "100%",
                padding: "10px 14px",
                background: "#0b1120",
                border: "1px solid #334155",
                borderRadius: 10,
                color: "#ffffff",
                fontSize: 14,
                fontWeight: 700,
                letterSpacing: 1,
                outline: "none",
                marginBottom: 24,
                boxSizing: "border-box",
              }}
            />

            <div style={{ display: "flex", justifyContent: "flex-end", gap: 12 }}>
              <button
                onClick={() => setShowConfirmModal(false)}
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
                disabled={confirmInput.trim().toUpperCase() !== "RESET"}
                onClick={executeReset}
                style={{
                  padding: "10px 22px",
                  borderRadius: 10,
                  fontSize: 13,
                  fontWeight: 700,
                  background:
                    confirmInput.trim().toUpperCase() === "RESET"
                      ? "linear-gradient(135deg,#ef4444,#b91c1c)"
                      : "#374151",
                  color: confirmInput.trim().toUpperCase() === "RESET" ? "#ffffff" : "#9ca3af",
                  border: "none",
                  cursor: confirmInput.trim().toUpperCase() === "RESET" ? "pointer" : "not-allowed",
                  boxShadow:
                    confirmInput.trim().toUpperCase() === "RESET"
                      ? "0 4px 14px rgba(239,68,68,0.35)"
                      : "none",
                }}
              >
                Ya, Hapus Data
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
