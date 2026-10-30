import math

def clean_float(val):
    if val is None:
        return None
    try:
        f = float(val)
        return None if (math.isnan(f) or math.isinf(f)) else f
    except (ValueError, TypeError):
        return None

# ========================================================
# app/api/v1/endpoints/clusters.py
# Endpoint untuk K-Means Clustering & Elbow Method
# ========================================================
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.database import get_db
from app.ml.clustering import run_kmeans_clustering, compute_elbow_method

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/clusters", tags=["K-Means Clustering"])


@router.post(
    "/run",
    summary="Jalankan K-Means Clustering",
    description=(
        "Menjalankan algoritma K-Means untuk mengelompokkan kota/kab ke dalam "
        "3 zona: Aman (Hijau), Waspada (Kuning), Kritis (Merah). "
        "Hasil disimpan ke tabel `hasil_klaster`. "
        "Proses ini berjalan di server (backend) sehingga tidak lag di browser."
    ),
)
def run_clustering(
    bulan: Optional[str] = Query(
        default=None,
        description="Filter bulan format YYYY-MM (contoh: 2026-01). Kosongkan untuk semua data.",
        example="2026-01",
    ),
    n_clusters: int = Query(
        default=3,
        ge=2, le=10,
        description="Jumlah cluster/zona (default: 3)",
    ),
    db: Session = Depends(get_db),
):
    """
    Endpoint untuk men-trigger proses K-Means Clustering.

    **Kapan dipakai?**
    - Setelah upload file Excel baru
    - Setiap awal bulan untuk data bulan baru
    - Saat demo/sidang untuk menunjukkan proses clustering

    **Output di database:**
    Tabel `hasil_klaster` akan berisi ~514 baris (satu per kota),
    masing-masing dengan label status_zona.
    """
    logger.info(f"Menerima request clustering: bulan={bulan}, k={n_clusters}")

    result = run_kmeans_clustering(
        db=db,
        bulan=bulan,
        n_clusters=n_clusters,
    )

    if result.errors and result.n_cities_processed == 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"message": "Clustering gagal.", "errors": result.errors},
        )

    return {
        "status": "success",
        "message": (
            f"K-Means clustering selesai. "
            f"{result.n_cities_processed} kota berhasil dikelompokkan."
        ),
        "hasil_clustering": result.to_dict(),
    }


@router.get(
    "/",
    summary="Ambil Hasil Clustering Terbaru",
    description=(
        "Mengambil hasil K-Means clustering terbaru dari database. "
        "Dapat difilter berdasarkan bulan periode atau nama komoditas spesifik."
    ),
)
def get_latest_clusters(
    bulan: Optional[str] = Query(
        default=None,
        description="Filter bulan proses format YYYY-MM",
    ),
    nama_komoditas: Optional[str] = Query(
        default=None,
        description="Filter spesifik varian komoditas pangan (contoh: 'Beras Premium', 'Cabai Rawit Merah')",
    ),
    db: Session = Depends(get_db),
):
    try:
        # Jika ada filter komoditas spesifik, klasterisasi dihitung langsung secara on-the-fly per komoditas
        if nama_komoditas:
            where_conditions = ["k_kom.nama_varian = :komoditas"]
            params = {"komoditas": nama_komoditas}

            if bulan:
                where_conditions.append("TO_CHAR(h.tanggal, 'YYYY-MM') = :bulan")
                params["bulan"] = bulan

            where_str = " AND ".join(where_conditions)

            query = text(f"""
                SELECT
                    h.kode_kabkota,
                    k.nama_kabkota,
                    p.nama_provinsi,
                    k.latitude,
                    k.longitude,
                    AVG(h.harga) as avg_harga,
                    COALESCE(STDDEV(h.harga), 0) as std_harga,
                    COUNT(h.id_harga) as jumlah_data
                FROM harga_harian h
                JOIN komoditas k_kom ON h.id_komoditas = k_kom.id_komoditas
                JOIN kabupaten_kota k ON h.kode_kabkota = k.kode_kabkota
                JOIN provinsi p ON k.kode_provinsi = p.kode_provinsi
                WHERE {where_str}
                GROUP BY h.kode_kabkota, k.nama_kabkota, p.nama_provinsi, k.latitude, k.longitude
                HAVING COUNT(h.id_harga) >= 1
                ORDER BY avg_harga ASC
            """)

            rows = db.execute(query, params).fetchall()

            if not rows:
                return {
                    "status": "empty",
                    "message": f"Tidak ada data transaksi untuk komoditas '{nama_komoditas}'.",
                    "data": [],
                    "summary": {"total": 0, "Aman": 0, "Waspada": 0, "Kritis": 0},
                }

            # Menghitung kuantil/tertile untuk pengelompokan 3 zona komoditas
            import numpy as np
            prices = [float(r[5]) for r in rows if r[5] is not None]
            q33 = np.percentile(prices, 33.33) if prices else 0
            q66 = np.percentile(prices, 66.67) if prices else 0

            data = []
            zona_counts = {"Aman": 0, "Waspada": 0, "Kritis": 0}

            for row in rows:
                price = float(row[5]) if row[5] is not None else 0
                if price <= q33:
                    zona = "Aman"
                    warna = "#22c55e"
                    cid = 0
                elif price <= q66:
                    zona = "Waspada"
                    warna = "#f59e0b"
                    cid = 1
                else:
                    zona = "Kritis"
                    warna = "#ef4444"
                    cid = 2

                zona_counts[zona] += 1

                data.append({
                    "kode_kabkota": str(row[0]),
                    "nama_kabkota": str(row[1]),
                    "nama_provinsi": str(row[2]),
                    "latitude": clean_float(row[3]),
                    "longitude": clean_float(row[4]),
                    "status_zona": zona,
                    "cluster_id": cid,
                    "tanggal_proses": f"Komoditas: {nama_komoditas} (Rata-rata: Rp {price:,.0f})",
                    "warna": warna,
                })

            total_records = sum([int(r[7]) for r in rows])

            return {
                "status": "success",
                "komoditas": nama_komoditas,
                "data": data,
                "summary": {
                    "total": len(data),
                    "total_records": total_records,
                    **zona_counts,
                },
            }

        # Standar (Semua komoditas agregat dari hasil_klaster)
        where_clause = ""
        if bulan:
            where_clause = f"WHERE (hk.periode_bulan = '{bulan}' OR TO_CHAR(hk.tanggal_proses, 'YYYY-MM') = '{bulan}')"
        else:
            where_clause = "WHERE (hk.periode_bulan = 'ALL' OR hk.periode_bulan IS NULL)"

        query = text(f"""
            SELECT DISTINCT ON (hk.kode_kabkota)
                hk.kode_kabkota,
                k.nama_kabkota,
                p.nama_provinsi,
                k.latitude,
                k.longitude,
                hk.status_zona,
                hk.cluster_id,
                hk.tanggal_proses
            FROM hasil_klaster hk
            JOIN kabupaten_kota k  ON hk.kode_kabkota = k.kode_kabkota
            JOIN provinsi p        ON k.kode_provinsi  = p.kode_provinsi
            {where_clause}
            ORDER BY hk.kode_kabkota, hk.tanggal_proses DESC
        """)

        rows = db.execute(query).fetchall()

        if not rows:
            return {
                "status": "empty",
                "message": "Belum ada hasil clustering. Jalankan POST /clusters/run terlebih dahulu.",
                "data": [],
                "summary": {"total": 0, "Aman": 0, "Waspada": 0, "Kritis": 0},
            }

        data = [
            {
                "kode_kabkota":  str(row[0]),
                "nama_kabkota":  str(row[1]),
                "nama_provinsi": str(row[2]),
                "latitude":      clean_float(row[3]),
                "longitude":     clean_float(row[4]),
                "status_zona":   str(row[5]),
                "cluster_id":    int(row[6]) if row[6] is not None else 0,
                "tanggal_proses": str(row[7]),
                "warna": {
                    "Aman":    "#22c55e",
                    "Waspada": "#f59e0b",
                    "Kritis":  "#ef4444",
                }.get(str(row[5]), "#6b7280"),
            }
            for row in rows
        ]

        zona_counts = {"Aman": 0, "Waspada": 0, "Kritis": 0}
        for d in data:
            if d["status_zona"] in zona_counts:
                zona_counts[d["status_zona"]] += 1

        if bulan:
            total_harga_records = db.execute(text(f"SELECT COUNT(*) FROM harga_harian WHERE TO_CHAR(tanggal, 'YYYY-MM') = '{bulan}'")).scalar() or 0
        else:
            total_harga_records = db.execute(text("SELECT COUNT(*) FROM harga_harian")).scalar() or 0

        return {
            "status": "success",
            "data": data,
            "summary": {
                "total": len(data),
                "total_records": total_harga_records,
                **zona_counts,
            },
        }
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        logger.error(f"Error in get_latest_clusters: {tb}")
        raise HTTPException(status_code=500, detail=f"{str(e)}: {tb}")


@router.get(
    "/elbow",
    summary="Hitung Elbow Method (untuk Skripsi Bab 4)",
    description=(
        "Menghitung inertia dan silhouette score untuk berbagai nilai k (2-8). "
        "Digunakan untuk membuktikan bahwa k=3 adalah jumlah cluster optimal "
        "pada Bab 4 skripsi (Hasil & Pembahasan)."
    ),
)
def get_elbow_data(
    bulan: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
):
    """
    Endpoint untuk data visualisasi Elbow Method.
    Gunakan data ini untuk membuat grafik elbow di skripsi.
    """
    result = compute_elbow_method(db=db, bulan=bulan)

    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=result["error"],
        )

    return {
        "status": "success",
        "hasil_elbow_method": result,
    }

@router.get(
    "/centroids",
    summary="Karakteristik & Profil Centroid Tiap Klaster",
    description="Mengambil profil rata-rata harga, volatilitas, dan jumlah kota per zona klaster (Aman, Waspada, Kritis) untuk tabel bab 4 skripsi.",
)
def get_cluster_centroids(db: Session = Depends(get_db)):
    try:
        query = text("""
            SELECT 
                hk.status_zona,
                COUNT(DISTINCT hk.kode_kabkota) as total_kota,
                AVG(sub.avg_harga) as mean_harga,
                AVG(sub.cv_harga) as mean_cv
            FROM hasil_klaster hk
            JOIN (
                SELECT 
                    kode_kabkota,
                    AVG(harga) as avg_harga,
                    CASE WHEN AVG(harga) > 0 THEN (STDDEV(harga)/AVG(harga))*100 ELSE 0 END as cv_harga
                FROM harga_harian
                GROUP BY kode_kabkota
            ) sub ON hk.kode_kabkota = sub.kode_kabkota
            GROUP BY hk.status_zona
            ORDER BY mean_harga ASC
        """)
        rows = db.execute(query).fetchall()

        characteristics = []
        for r in rows:
            zona = str(r[0])
            total_kota = int(r[1])
            mean_harga = float(r[2]) if r[2] is not None else 0.0
            mean_cv = float(r[3]) if r[3] is not None else 0.0

            desc = ""
            if zona == "Aman":
                desc = "Harga komoditas relatif murah dan stabil di tingkat konsumen."
            elif zona == "Waspada":
                desc = "Harga berada pada level menengah atau mulai menunjukkan fluktuasi harga."
            else:
                desc = "Harga rata-rata tinggi di atas rata-rata nasional dan rawan lonjakan pasokan."

            characteristics.append({
                "status_zona": zona,
                "total_kota": total_kota,
                "mean_harga": round(mean_harga, 2),
                "mean_volatilitas_cv": round(mean_cv, 2),
                "warna": "#22c55e" if zona == "Aman" else ("#f59e0b" if zona == "Waspada" else "#ef4444"),
                "interpretasi": desc,
            })

        return {"status": "success", "data": characteristics}
    except Exception as e:
        logger.error(f"Error fetching centroids: {e}")
        return {"status": "error", "message": str(e), "data": []}


@router.get(
    "/months",
    summary="Ambil Daftar Bulan yang Tersedia",
    description="Mengambil daftar bulan (YYYY-MM) dari data harga harian dan hasil klaster untuk dropdown filter tanggal.",
)
def get_available_months(db: Session = Depends(get_db)):
    try:
        query = text("""
            SELECT DISTINCT TO_CHAR(tanggal, 'YYYY-MM') as bulan
            FROM harga_harian
            ORDER BY bulan ASC
        """)
        rows = db.execute(query).fetchall()
        months = [r[0] for r in rows if r[0] is not None]
        return {"status": "success", "data": months}
    except Exception as e:
        logger.error(f"Error fetching months: {e}")
        return {"status": "success", "data": []}
