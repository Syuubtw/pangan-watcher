# ========================================================
# app/api/v1/endpoints/trends.py
# Endpoint untuk data tren harga (Analytics Dashboard)
# ========================================================
import logging
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.database import get_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/trends", tags=["Analytics & Trends"])


@router.get(
    "/",
    summary="Tren Harga Komoditas",
    description=(
        "Mengambil data tren harga komoditas tertentu di kota tertentu "
        "sepanjang periode. Digunakan untuk Line Chart di halaman Analytics Dashboard."
    ),
)
def get_price_trends(
    kode_kabkota: Optional[str] = Query(
        default=None,
        description="Kode kabupaten/kota (kosongkan untuk semua kota)",
        example="3374",
    ),
    nama_komoditas: Optional[str] = Query(
        default=None,
        description="Nama komoditas (kosongkan untuk semua)",
        example="Beras Premium",
    ),
    bulan: Optional[str] = Query(
        default=None,
        description="Filter bulan YYYY-MM (kosongkan untuk 3 bulan terakhir)",
        example="2026-01",
    ),
    db: Session = Depends(get_db),
):
    """
    Data untuk Chart.js Line Chart di frontend.
    Setiap titik data = rata-rata harga per tanggal per kota per komoditas.
    """
    conditions = ["1=1"]
    params = {}

    if kode_kabkota:
        conditions.append("h.kode_kabkota = :kode_kabkota")
        params["kode_kabkota"] = kode_kabkota

    if nama_komoditas:
        conditions.append("ko.nama_varian ILIKE :nama_komoditas")
        params["nama_komoditas"] = f"%{nama_komoditas}%"

    if bulan:
        conditions.append("TO_CHAR(h.tanggal, 'YYYY-MM') = :bulan")
        params["bulan"] = bulan
    # Jika bulan kosong, tampilkan semua rentang riwayat tanpa filter buatan agar grafik multi-periode langsung terlihat

    where = " AND ".join(conditions)

    query = text(f"""
        SELECT
            h.tanggal,
            ko.nama_varian    AS nama_komoditas,
            h.kode_kabkota,
            k.nama_kabkota,
            AVG(h.harga)      AS rata_harga,
            MIN(h.harga)      AS min_harga,
            MAX(h.harga)      AS max_harga
        FROM harga_harian h
        JOIN komoditas ko      ON h.id_komoditas  = ko.id_komoditas
        JOIN kabupaten_kota k  ON h.kode_kabkota  = k.kode_kabkota
        WHERE {where}
        GROUP BY h.tanggal, ko.nama_varian, h.kode_kabkota, k.nama_kabkota
        ORDER BY h.tanggal ASC
        LIMIT 5000
    """)

    rows = db.execute(query, params).fetchall()

    data = [
        {
            "tanggal":       str(row[0]),
            "nama_komoditas": row[1],
            "kode_kabkota":  row[2],
            "nama_kabkota":  row[3],
            "rata_harga":    round(float(row[4]), 2),
            "min_harga":     float(row[5]),
            "max_harga":     float(row[6]),
        }
        for row in rows
    ]

    return {
        "status": "success",
        "total_titik_data": len(data),
        "filter": {
            "kode_kabkota":   kode_kabkota,
            "nama_komoditas": nama_komoditas,
            "bulan":          bulan or "3 bulan terakhir",
        },
        "data": data,
    }


@router.get(
    "/komoditas",
    summary="Daftar Semua Komoditas",
    description="Mengambil daftar semua komoditas yang ada di database. Untuk dropdown filter frontend.",
)
def get_all_komoditas(db: Session = Depends(get_db)):
    rows = db.execute(
        text("SELECT id_komoditas, nama_varian, satuan FROM komoditas ORDER BY nama_varian")
    ).fetchall()
    return {
        "status": "success",
        "data": [
            {"id": row[0], "nama_varian": row[1], "satuan": row[2]}
            for row in rows
        ],
    }


@router.get(
    "/kabkota",
    summary="Daftar Semua Kabupaten/Kota",
    description="Mengambil daftar semua kabupaten/kota. Untuk dropdown filter frontend.",
)
def get_all_kabkota(db: Session = Depends(get_db)):
    rows = db.execute(
        text("""
            SELECT k.kode_kabkota, k.nama_kabkota, p.nama_provinsi
            FROM kabupaten_kota k
            JOIN provinsi p ON k.kode_provinsi = p.kode_provinsi
            ORDER BY p.nama_provinsi, k.nama_kabkota
        """)
    ).fetchall()
    return {
        "status": "success",
        "data": [
            {"kode": row[0], "nama": row[1], "provinsi": row[2]}
            for row in rows
        ],
    }
