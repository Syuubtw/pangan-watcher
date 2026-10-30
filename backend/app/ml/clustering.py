# ========================================================
# app/ml/clustering.py
# K-Means Clustering Engine - Inti algoritma pengelompokan
#
# ALUR KERJA:
# 1. Ambil data harga dari DB via query agregasi SQL
# 2. Hitung fitur per kota: rata-rata harga & volatilitas (std)
# 3. Normalisasi fitur dengan StandardScaler
# 4. Jalankan K-Means (k=3)
# 5. Label cluster -> Aman/Waspada/Kritis berdasarkan rata-rata centroid
# 6. Hitung Silhouette Score (untuk bab 4 skripsi)
# 7. Simpan hasil ke tabel hasil_klaster
# ========================================================
import logging
from datetime import datetime, timezone
from typing import Optional

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score
from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.core.config import settings
from app.models.klaster import HasilKlaster

logger = logging.getLogger(__name__)

# ── Konstanta label zona ──────────────────────────────────────────────────────
ZONA_AMAN     = "Aman"      # Hijau  - harga stabil, rendah
ZONA_WASPADA  = "Waspada"   # Kuning - harga menengah / mulai naik
ZONA_KRITIS   = "Kritis"    # Merah  - harga tinggi / melonjak


class ClusteringResult:
    """Hasil komputasi K-Means untuk response API dan logging skripsi."""
    def __init__(self):
        self.n_cities_processed: int = 0
        self.n_aman: int = 0
        self.n_waspada: int = 0
        self.n_kritis: int = 0
        self.silhouette_score: Optional[float] = None
        self.inertia: Optional[float] = None
        self.centroids: list = []
        self.tanggal_proses: Optional[str] = None
        self.errors: list[str] = []

    def to_dict(self) -> dict:
        return {
            "n_cities_processed": self.n_cities_processed,
            "zona_summary": {
                ZONA_AMAN:    self.n_aman,
                ZONA_WASPADA: self.n_waspada,
                ZONA_KRITIS:  self.n_kritis,
            },
            # Silhouette Score: nilai -1 s/d 1, makin dekat 1 makin baik
            # Untuk skripsi: nilai > 0.5 = pengelompokan baik
            "silhouette_score": round(self.silhouette_score, 4) if self.silhouette_score else None,
            "inertia": round(self.inertia, 2) if self.inertia else None,
            "centroids_normalized": self.centroids,
            "tanggal_proses": self.tanggal_proses,
            "errors": self.errors,
        }


def _fetch_aggregated_data(db: Session, bulan: Optional[str] = None) -> pd.DataFrame:
    """
    Mengambil data harga dari DB dan mengagregasikannya per kota.

    Fitur yang dihitung per kota (kode_kabkota):
    - rata_harga    : Rata-rata harga semua komoditas di kota tsb (Rp)
    - std_harga     : Standar deviasi harga = volatilitas (Rp)
    - cv_harga      : Coefficient of Variation = std/mean*100 (%) 
                      -> ukuran volatilitas relatif, lebih adil antar kota

    Args:
        bulan: Filter bulan format 'YYYY-MM' (opsional).
               Jika None, pakai semua data yang ada.
    """
    where_clause = ""
    if bulan:
        # Validasi format bulan
        try:
            datetime.strptime(bulan, "%Y-%m")
            where_clause = f"WHERE TO_CHAR(h.tanggal, 'YYYY-MM') = '{bulan}'"
        except ValueError:
            logger.warning(f"Format bulan tidak valid: {bulan}. Menggunakan semua data.")

    query = text(f"""
        SELECT
            h.kode_kabkota,
            k.nama_kabkota,
            COUNT(h.id_harga)          AS jumlah_data,
            AVG(h.harga)               AS rata_harga,
            STDDEV(h.harga)            AS std_harga,
            CASE
                WHEN AVG(h.harga) > 0
                THEN (STDDEV(h.harga) / AVG(h.harga)) * 100
                ELSE 0
            END                        AS cv_harga
        FROM harga_harian h
        JOIN kabupaten_kota k ON h.kode_kabkota = k.kode_kabkota
        {where_clause}
        GROUP BY h.kode_kabkota, k.nama_kabkota
        HAVING COUNT(h.id_harga) >= 5
        ORDER BY h.kode_kabkota
    """)

    result = db.execute(query)
    rows = result.fetchall()

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows, columns=[
        "kode_kabkota", "nama_kabkota", "jumlah_data",
        "rata_harga", "std_harga", "cv_harga"
    ])

    # Isi NaN pada std_harga (kota dengan hanya 1 jenis data) dengan 0
    df["std_harga"] = df["std_harga"].fillna(0)
    df["cv_harga"]  = df["cv_harga"].fillna(0)

    logger.info(
        f"Data agregasi: {len(df)} kota, "
        f"filter bulan: {bulan or 'semua'}"
    )
    return df


def _assign_zone_labels(
    df: pd.DataFrame,
    cluster_labels: np.ndarray,
    kmeans_model: KMeans,
    scaler: StandardScaler,
) -> pd.Series:
    """
    Memetakan nomor cluster (0, 1, 2) ke label zona yang bermakna.

    Logika pelabelan:
    - Hitung rata-rata `rata_harga` untuk setiap cluster
    - Cluster dengan rata-rata harga TERENDAH  -> Aman (Hijau)
    - Cluster dengan rata-rata harga MENENGAH  -> Waspada (Kuning)
    - Cluster dengan rata-rata harga TERTINGGI -> Kritis (Merah)

    Ini penting agar label zona konsisten meskipun nomor cluster
    dari KMeans berubah-ubah setiap kali dijalankan (KMeans non-deterministik).
    """
    df_temp = df.copy()
    df_temp["cluster_id"] = cluster_labels

    # Hitung rata-rata harga per cluster
    cluster_mean = df_temp.groupby("cluster_id")["rata_harga"].mean()

    # Urutkan cluster berdasarkan rata-rata harga (ascending)
    sorted_clusters = cluster_mean.sort_values().index.tolist()

    # Peta: cluster_id -> label zona
    zona_map = {
        sorted_clusters[0]: ZONA_AMAN,      # Rata-rata terendah
        sorted_clusters[1]: ZONA_WASPADA,   # Rata-rata menengah
        sorted_clusters[2]: ZONA_KRITIS,    # Rata-rata tertinggi
    }

    logger.info("Pemetaan cluster -> zona:")
    for cid, zona in zona_map.items():
        logger.info(
            f"  Cluster {cid} -> {zona} "
            f"(rata-rata harga: Rp {cluster_mean[cid]:,.0f})"
        )

    return df_temp["cluster_id"].map(zona_map), zona_map


def run_kmeans_clustering(
    db: Session,
    bulan: Optional[str] = None,
    n_clusters: int = None,
    random_state: int = 42,
) -> ClusteringResult:
    """
    FUNGSI UTAMA: Menjalankan K-Means clustering end-to-end.

    Args:
        db          : SQLAlchemy database session
        bulan       : Filter bulan 'YYYY-MM' (None = semua data)
        n_clusters  : Jumlah cluster (default dari settings = 3)
        random_state: Seed untuk reproducibility (penting untuk skripsi!)

    Returns:
        ClusteringResult: Ringkasan hasil untuk response API
    """
    result = ClusteringResult()
    result.tanggal_proses = datetime.now(timezone.utc).isoformat()

    if n_clusters is None:
        n_clusters = settings.N_CLUSTERS  # Default: 3

    # ── LANGKAH 1: Ambil & Validasi Data ─────────────────────────────────────
    logger.info("=" * 55)
    logger.info("  MEMULAI K-MEANS CLUSTERING")
    logger.info("=" * 55)
    logger.info(f"Parameter: k={n_clusters}, bulan={bulan or 'semua'}")

    df = _fetch_aggregated_data(db, bulan)

    if df.empty:
        msg = "Tidak ada data harga di database. Upload file Excel terlebih dahulu."
        result.errors.append(msg)
        logger.error(msg)
        return result

    if len(df) < n_clusters:
        msg = (
            f"Jumlah kota ({len(df)}) lebih sedikit dari jumlah cluster ({n_clusters}). "
            f"Tambahkan lebih banyak data."
        )
        result.errors.append(msg)
        logger.error(msg)
        return result

    result.n_cities_processed = len(df)
    logger.info(f"Data siap: {len(df)} kota akan dicluster.")

    # ── LANGKAH 2: Siapkan Fitur untuk K-Means ───────────────────────────────
    # Fitur yang digunakan:
    # - rata_harga : Level harga absolute
    # - cv_harga   : Volatilitas relatif (%) - lebih adil antar kota
    feature_cols = ["rata_harga", "cv_harga"]
    X = df[feature_cols].values

    # ── LANGKAH 3: Normalisasi Fitur (StandardScaler) ─────────────────────────
    # WAJIB dilakukan sebelum K-Means karena:
    # - rata_harga bisa jutaan Rupiah
    # - cv_harga hanya 0-100%
    # Tanpa normalisasi, K-Means akan didominasi fitur dengan skala besar.
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    logger.info(
        f"Fitur ternormalisasi: mean={scaler.mean_.tolist()}, "
        f"std={scaler.scale_.tolist()}"
    )

    # ── LANGKAH 4: Jalankan K-Means ──────────────────────────────────────────
    logger.info(f"Menjalankan KMeans(n_clusters={n_clusters}, random_state={random_state})...")
    kmeans = KMeans(
        n_clusters=n_clusters,
        init="k-means++",    # Inisialisasi cerdas untuk konvergensi lebih cepat
        n_init=20,           # Coba 20 inisialisasi berbeda, ambil yang terbaik
        max_iter=500,        # Maksimal iterasi per run
        random_state=random_state,
    )
    cluster_labels = kmeans.fit_predict(X_scaled)
    result.inertia = float(kmeans.inertia_)
    logger.info(f"KMeans selesai. Inertia: {result.inertia:.2f}")

    # ── LANGKAH 5: Hitung Silhouette Score ───────────────────────────────────
    # Silhouette Score: ukuran kualitas clustering
    # Range: -1 (buruk) s/d +1 (sempurna)
    # Interpretasi untuk skripsi:
    # > 0.7 : Sangat baik    | 0.5-0.7 : Baik
    # 0.25-0.5 : Cukup       | < 0.25  : Lemah
    if len(df) > n_clusters:
        sil_score = silhouette_score(X_scaled, cluster_labels)
        result.silhouette_score = float(sil_score)
        logger.info(f"Silhouette Score: {sil_score:.4f}")

    # ── LANGKAH 6: Label Zona ─────────────────────────────────────────────────
    zona_series, zona_map = _assign_zone_labels(df, cluster_labels, kmeans, scaler)
    df["status_zona"] = zona_series
    df["cluster_id"]  = cluster_labels

    # Hitung distribusi zona
    result.n_aman    = int((df["status_zona"] == ZONA_AMAN).sum())
    result.n_waspada = int((df["status_zona"] == ZONA_WASPADA).sum())
    result.n_kritis  = int((df["status_zona"] == ZONA_KRITIS).sum())

    # Simpan info centroid (dalam skala ternormalisasi)
    result.centroids = kmeans.cluster_centers_.tolist()

    logger.info(
        f"Distribusi zona: "
        f"Aman={result.n_aman}, "
        f"Waspada={result.n_waspada}, "
        f"Kritis={result.n_kritis}"
    )

    # ── LANGKAH 7: Simpan ke Database ─────────────────────────────────────────
    logger.info("Menyimpan hasil clustering ke database...")
    tanggal_proses = datetime.now(timezone.utc)

    records = [
        {
            "kode_kabkota":   row["kode_kabkota"],
            "tanggal_proses":  tanggal_proses,
            "periode_bulan":   bulan if bulan else "ALL",
            "status_zona":    row["status_zona"],
            "cluster_id":     int(row["cluster_id"]),
        }
        for _, row in df.iterrows()
    ]

    # Bulk insert hasil clustering
    db.execute(pg_insert(HasilKlaster).values(records))
    db.commit()

    logger.info(f"Berhasil menyimpan {len(records)} hasil clustering.")
    logger.info("=" * 55)
    logger.info("  K-MEANS CLUSTERING SELESAI")
    logger.info("=" * 55)

    return result


def compute_elbow_method(
    db: Session,
    bulan: Optional[str] = None,
    k_range: range = range(2, 9),
) -> dict:
    """
    Menghitung Elbow Method untuk menentukan jumlah cluster optimal.
    
    Digunakan untuk VALIDASI di Bab 4 Skripsi:
    - Plot inertia vs k
    - Titik 'siku' (elbow) = nilai k optimal
    - Diharapkan k=3 memang optimal untuk data ini

    Args:
        db     : SQLAlchemy session
        bulan  : Filter bulan (opsional)
        k_range: Range nilai k yang dicoba (default: 2-8)
    
    Returns:
        Dict berisi list inertia per k dan rekomendasi k optimal
    """
    df = _fetch_aggregated_data(db, bulan)

    if df.empty:
        return {"error": "Tidak ada data. Upload Excel terlebih dahulu."}

    feature_cols = ["rata_harga", "cv_harga"]
    X = df[feature_cols].values
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    inertias = []
    silhouette_scores = []

    logger.info(f"Menghitung Elbow Method untuk k={list(k_range)}...")
    for k in k_range:
        if k >= len(df):
            break
        km = KMeans(n_clusters=k, init="k-means++", n_init=10, random_state=42)
        labels = km.fit_predict(X_scaled)
        inertias.append(float(km.inertia_))

        if k > 1 and len(df) > k:
            sil = silhouette_score(X_scaled, labels)
            silhouette_scores.append({"k": k, "silhouette": round(float(sil), 4)})

    result = {
        "elbow_data": [
            {"k": k, "inertia": round(inertia, 2)}
            for k, inertia in zip(k_range, inertias)
        ],
        "silhouette_data": silhouette_scores,
        "n_cities": len(df),
        "catatan": (
            "Pilih nilai k di titik 'siku' kurva inertia. "
            "k dengan silhouette_score tertinggi adalah pilihan optimal."
        ),
    }

    logger.info("Elbow Method selesai.")
    return result
