from app.ml.clustering import run_kmeans_clustering
from app.services.ews_service import run_ews_detection
# ========================================================
# app/api/v1/endpoints/upload.py
# Endpoint untuk upload file Excel & trigger ingestion
# ========================================================
import os
import logging
import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.services.ingestion_service import process_excel_file, IngestionResult

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/upload", tags=["Data Ingestion"])

ALLOWED_EXTENSIONS = {".xlsx", ".xls"}


@router.post(
    "/",
    summary="Upload File Excel Harga Pangan",
    description=(
        "Upload file Excel (.xlsx) data harga harian komoditas pangan. "
        "Backend akan otomatis memproses, membersihkan, dan menyimpan data ke database."
    ),
    response_description="Ringkasan hasil proses ingestion.",
)
async def upload_harga_excel(
    file: UploadFile = File(..., description="File Excel harga pangan (.xlsx)"),
    db: Session = Depends(get_db),
):
    """
    Endpoint upload file Excel.
    
    Proses:
    1. Validasi tipe file (.xlsx / .xls)
    2. Validasi ukuran file (max setting MAX_UPLOAD_SIZE_MB)
    3. Simpan file ke folder uploads/
    4. Panggil ingestion_service untuk proses data
    5. Kembalikan ringkasan hasil
    """
    # ── Validasi ekstensi file ───────────────────────────────────────────────
    file_suffix = Path(file.filename).suffix.lower()
    if file_suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Format file tidak didukung: '{file_suffix}'. Gunakan .xlsx atau .xls",
        )

    # ── Pastikan folder upload ada ───────────────────────────────────────────
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)

    # ── Simpan file ke disk ──────────────────────────────────────────────────
    # Nama file dibuat unik menggunakan timestamp untuk menghindari konflik
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_filename = f"{timestamp}_{file.filename}"
    file_path = upload_dir / safe_filename

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        logger.info(f"File disimpan: {file_path}")
    except Exception as e:
        logger.error(f"Gagal menyimpan file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Gagal menyimpan file. Coba lagi.",
        )

    # ── Validasi ukuran file ─────────────────────────────────────────────────
    file_size_mb = file_path.stat().st_size / (1024 * 1024)
    max_size_mb = settings.MAX_UPLOAD_SIZE_MB
    if file_size_mb > max_size_mb:
        file_path.unlink()  # Hapus file yang terlalu besar
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Ukuran file ({file_size_mb:.1f} MB) melebihi batas maksimal ({max_size_mb} MB).",
        )

    # ── Proses ingestion ─────────────────────────────────────────────────────
    logger.info(f"Memulai ingestion untuk file: {safe_filename}")
    
    result: IngestionResult = process_excel_file(str(file_path), db)

    if result.errors and result.rows_inserted == 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": "Ingestion gagal. Periksa format file.",
                "errors": result.errors,
            },
        )

    # ── Otomatis Jalankan K-Means Clustering & EWS ───────────────────────────
    auto_analysis = {"kmeans": None, "ews": None}
    if result.rows_inserted > 0:
        try:
            # 1. Jalankan clustering untuk ALL (akumulasi)
            logger.info("Otomatis menjalankan K-Means Clustering (ALL) setelah upload...")
            km_res = run_kmeans_clustering(db=db, bulan=None, n_clusters=3)

            # 2. Ambil semua bulan yang ada di database harga_harian dan jalankan clustering per bulan
            from sqlalchemy import text
            month_rows = db.execute(text("SELECT DISTINCT TO_CHAR(tanggal, 'YYYY-MM') FROM harga_harian ORDER BY 1")).fetchall()
            active_months = [r[0] for r in month_rows if r[0]]
            for m in active_months:
                run_kmeans_clustering(db=db, bulan=m, n_clusters=3)

            auto_analysis["kmeans"] = f"{km_res.n_cities_processed} kota diklasterkan (Semua periode & {len(active_months)} periode bulanan)."
        except Exception as e:
            logger.warning(f"Gagal auto run K-Means: {e}")
            auto_analysis["kmeans"] = f"Gagal: {e}"

        try:
            logger.info("Otomatis menjalankan Early Warning System (EWS)...")
            ews_res = run_ews_detection(db=db)
            auto_analysis["ews"] = f"{ews_res.new_alerts_count} peringatan lonjakan harga terdeteksi."
        except Exception as e:
            logger.warning(f"Gagal auto run EWS: {e}")
            auto_analysis["ews"] = f"Gagal: {e}"

    # Hitung total kumulatif rekod di database
    from sqlalchemy import text
    total_records = db.execute(text("SELECT COUNT(*) FROM harga_harian")).scalar() or 0

    return {
        "status": "success" if not result.errors else "partial_success",
        "message": (
            f"File '{file.filename}' berhasil diproses. "
            f"{result.rows_inserted:,} data harga disimpan. Analisis K-Means dan EWS otomatis diperbarui."
        ),
        "file_saved_as": safe_filename,
        "ingestion_summary": {
            **result.to_dict(),
            "total_records_in_db": total_records,
        },
        "auto_analysis": auto_analysis,
    }


@router.delete(
    "/reset",
    summary="Reset Semua Data Transaksional Harga & Analisis",
    description=(
        "Mengosongkan tabel transaksi (harga_harian, hasil_klaster, peringatan_dini) "
        "agar sistem kembali bersih ke titik 0 dan siap diinput ulang oleh pengguna. "
        "Tabel master wilayah dan koordinat tetap aman."
    ),
)
def reset_database_data(db: Session = Depends(get_db)):
    from sqlalchemy import text
    try:
        # Hapus data transaksional
        db.execute(text("TRUNCATE TABLE peringatan_dini CASCADE;"))
        db.execute(text("TRUNCATE TABLE hasil_klaster CASCADE;"))
        db.execute(text("TRUNCATE TABLE harga_harian CASCADE;"))
        db.commit()

        logger.info("Database transaksional berhasil direset ke 0.")
        return {
            "status": "success",
            "message": "Semua data harga, hasil klaster, dan peringatan dini berhasil direset ke 0.",
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Gagal melakukan reset data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Gagal reset database: {str(e)}",
        )
