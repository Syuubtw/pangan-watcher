// lib/api.ts
// Axios instance terpusat untuk semua request ke backend FastAPI Pangan Watcher

import axios from "axios";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export const api = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
  headers: { "Content-Type": "application/json" },
});

// ── Types & Interfaces ────────────────────────────────────────────
export interface KlasterItem {
  kode_kabkota: string;
  nama_kabkota: string;
  nama_provinsi: string;
  latitude: number | null;
  longitude: number | null;
  status_zona: "Aman" | "Waspada" | "Kritis";
  cluster_id: number;
  warna: string;
  tanggal_proses: string;
}

export interface KlasterSummary {
  total: number;
  total_records?: number;
  Aman: number;
  Waspada: number;
  Kritis: number;
}

export interface KlasterResponse {
  status: string;
  data: KlasterItem[];
  summary: KlasterSummary;
}

export interface AlertItem {
  id_peringatan: number;
  kode_kabkota: string;
  nama_kabkota: string;
  nama_provinsi: string;
  nama_komoditas: string;
  harga_sebelumnya: number;
  harga_sekarang: number;
  persentase_lonjakan: number;
  tanggal_deteksi: string; // Berisi tanggal riil kejadian harga dari dataset
  status: "Baru" | "Ditinjau" | "Ditangani" | string;
  pesan: string;
}

export interface AlertResponse {
  status: string;
  total: number;
  limit: number;
  offset: number;
  data: AlertItem[];
}

export interface TrendItem {
  tanggal: string;
  nama_komoditas: string;
  kode_kabkota: string;
  nama_kabkota: string;
  rata_harga: number;
  min_harga?: number;
  max_harga?: number;
}

export interface KomoditasItem {
  id: number;
  nama_varian: string;
  satuan: string;
}

export interface KabkotaItem {
  kode: string;
  nama: string;
  provinsi: string;
}

export interface CentroidItem {
  status_zona: string;
  total_kota: number;
  mean_harga: number;
  mean_volatilitas_cv: number;
  warna: string;
  interpretasi: string;
}

export interface ElbowDataPoint {
  k: number;
  inertia: number;
}

export interface SilhouetteDataPoint {
  k: number;
  silhouette: number;
}

export interface ElbowResponse {
  status: string;
  hasil_elbow_method: {
    elbow_data: ElbowDataPoint[];
    silhouette_data: SilhouetteDataPoint[];
    n_cities: number;
    catatan: string;
  };
}

// ── API Functions ────────────────────────────────────────────────

/** Mengambil hasil klaster K-Means (bisa filter per bulan dan komoditas spesifik) */
export const getClusters = (bulan?: string, nama_komoditas?: string) =>
  api.get<KlasterResponse>("/clusters/", {
    params: {
      ...(bulan ? { bulan } : {}),
      ...(nama_komoditas ? { nama_komoditas } : {}),
    },
  });

/** URL endpoint ekspor Excel (.xlsx) peringatan dini berformat rapi dengan filter kolom kustom */
export const getAlertsExportExcelUrl = (params?: { status_filter?: string; bulan?: string; columns?: string[] }) => {
  const query = new URLSearchParams();
  if (params?.status_filter) query.append("status_filter", params.status_filter);
  if (params?.bulan) query.append("bulan", params.bulan);
  if (params?.columns && params.columns.length > 0) {
    query.append("columns", params.columns.join(","));
  }
  const qStr = query.toString();
  return `${API_BASE}/alerts/export/excel${qStr ? `?${qStr}` : ""}`;
};

/** URL endpoint ekspor CSV peringatan dini */
export const getAlertsExportCsvUrl = (params?: { status_filter?: string; bulan?: string }) => {
  const query = new URLSearchParams();
  if (params?.status_filter) query.append("status_filter", params.status_filter);
  if (params?.bulan) query.append("bulan", params.bulan);
  const qStr = query.toString();
  return `${API_BASE}/alerts/export/csv${qStr ? `?${qStr}` : ""}`;
};

/** Menjalankan K-Means clustering di server */
export const runClustering = (bulan?: string) =>
  api.post("/clusters/run", null, { params: bulan ? { bulan } : {} });

/** Mengambil evaluasi Elbow Method & Silhouette score untuk Bab 4 skripsi */
export const getElbow = () => api.get<ElbowResponse>("/clusters/elbow");

/** Mengambil profil karakteristik centroid tiap klaster (Aman, Waspada, Kritis) */
export const getCentroids = () => api.get<{ status: string; data: CentroidItem[] }>("/clusters/centroids");

/** Mengambil daftar bulan yang murni ada di dataset harga_harian */
export const getClusterMonths = () => api.get<{ status: string; data: string[] }>("/clusters/months");

/** Mengambil data peringatan dini (EWS) dengan filter status & periode bulan */
export const getAlerts = (params?: { status_filter?: string; kode_kabkota?: string; bulan?: string; limit?: number; offset?: number }) =>
  api.get<AlertResponse>("/alerts/", { params });

/** Menjalankan deteksi lonjakan harga EWS */
export const runEWS = () => api.post("/alerts/run");

/** Mengupdate status penanganan peringatan (Baru -> Ditinjau -> Ditangani) */
export const updateAlertStatus = (id_peringatan: number, status: string) =>
  api.patch(`/alerts/${id_peringatan}/status`, null, { params: { new_status: status } });

/** Mengambil data tren harga komoditas untuk grafik Chart.js */
export const getTrends = (params: { kode_kabkota?: string; nama_komoditas?: string; bulan?: string }) =>
  api.get<{ status: string; data: TrendItem[] }>("/trends/", { params });

/** Mengambil daftar master komoditas untuk dropdown */
export const getKomoditas = () => api.get<{ status: string; data: KomoditasItem[] }>("/trends/komoditas");

/** Mengambil daftar master kabupaten/kota untuk dropdown */
export const getKabkota = () => api.get<{ status: string; data: KabkotaItem[] }>("/trends/kabkota");

/** Mengunggah file Excel harga pangan */
export const uploadExcel = (file: File) => {
  const formData = new FormData();
  formData.append("file", file);
  return api.post("/upload/", formData, {
    headers: { "Content-Type": "multipart/form-data" },
    timeout: 600000, // 10 menit untuk dataset besar
  });
};

/** Mengosongkan data transaksi database ke 0 */
export const resetAllData = () => api.delete<{ status: string; message: string }>("/upload/reset");
