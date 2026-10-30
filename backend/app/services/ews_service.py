# ========================================================
# app/services/ews_service.py
# Early Warning System - Deteksi Lonjakan Harga Pangan
#
# LOGIKA:
# Untuk setiap komoditas di setiap kota:
# 1. Ambil harga hari ini vs rata-rata 7 hari sebelumnya
# 2. Hitung persentase perubahan harga
# 3. Jika lonjakan > threshold (default 15%), catat peringatan
# ========================================================
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

import pandas as pd
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.peringatan import PeringatanDini

logger = logging.getLogger(__name__)


class EWSResult:
    """Hasil deteksi EWS untuk response API."""
    def __init__(self):
        self.n_checked: int = 0
        self.n_alerts_created: int = 0
        self.threshold_used: float = 0.0
        self.alerts_preview: list = []
        self.errors: list[str] = []

    def to_dict(self) -> dict:
        return {
            "n_kombinasi_diperiksa": self.n_checked,
            "n_peringatan_baru": self.n_alerts_created,
            "threshold_persen": self.threshold_used,
            "preview_peringatan": self.alerts_preview[:10],
            "errors": self.errors,
        }


def _fetch_price_changes(
    db: Session,
    tanggal_akhir: Optional[str] = None,
    window_days: int = 7,
) -> pd.DataFrame:
    """
    Query data harga untuk mendeteksi lonjakan.

    Strategi:
    - Ambil harga terbaru (tanggal_akhir atau tanggal max di DB)
    - Bandingkan dengan rata-rata harga window_days hari sebelumnya
    - Hitung persentase perubahan: (harga_baru - harga_lama) / harga_lama * 100

    Returns:
        DataFrame dengan kolom:
        kode_kabkota, nama_kabkota, nama_varian, id_harga,
        tanggal, harga_sekarang, harga_sebelumnya, pct_change
    """
    # Tentukan tanggal referensi
    if tanggal_akhir:
        try:
            ref_date = datetime.strptime(tanggal_akhir, "%Y-%m-%d").date()
        except ValueError:
            logger.warning(f"Format tanggal tidak valid: {tanggal_akhir}. Pakai tanggal max.")
            ref_date = None
    else:
        ref_date = None

    # Query menggunakan window function PostgreSQL untuk efisiensi
    # Jauh lebih cepat daripada join atau subquery berganda
    date_filter = f"AND h.tanggal = '{ref_date}'" if ref_date else ""

    query = text(f"""
        WITH latest_date AS (
            SELECT MAX(tanggal) as max_tgl FROM harga_harian
            {date_filter.replace("AND h.tanggal =", "WHERE tanggal =")}
        ),
        prev_date AS (
            SELECT MAX(tanggal) as prev_tgl FROM harga_harian 
            WHERE tanggal < (SELECT max_tgl FROM latest_date)
        ),
        harga_latest AS (
            SELECT
                h.id_harga,
                h.kode_kabkota,
                k.nama_kabkota,
                ko.nama_varian,
                ko.id_komoditas,
                h.tanggal,
                h.harga AS harga_sekarang
            FROM harga_harian h
            JOIN kabupaten_kota k  ON h.kode_kabkota  = k.kode_kabkota
            JOIN komoditas ko      ON h.id_komoditas   = ko.id_komoditas
            WHERE h.tanggal = (SELECT max_tgl FROM latest_date)
        ),
        harga_baseline AS (
            SELECT
                h.kode_kabkota,
                h.id_komoditas,
                AVG(h.harga) AS harga_sebelumnya
            FROM harga_harian h
            WHERE h.tanggal = (SELECT prev_tgl FROM prev_date)
            GROUP BY h.kode_kabkota, h.id_komoditas
        )
        SELECT
            l.id_harga,
            l.kode_kabkota,
            l.nama_kabkota,
            l.nama_varian,
            l.tanggal,
            l.harga_sekarang,
            b.harga_sebelumnya,
            CASE
                WHEN b.harga_sebelumnya > 0
                THEN ((l.harga_sekarang - b.harga_sebelumnya) / b.harga_sebelumnya) * 100
                ELSE 0
            END AS pct_change
        FROM harga_latest l
        JOIN harga_baseline b
            ON l.kode_kabkota = b.kode_kabkota AND l.id_komoditas = b.id_komoditas
        ORDER BY pct_change DESC
    """)

    result = db.execute(query)
    rows = result.fetchall()

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows, columns=[
        "id_harga", "kode_kabkota", "nama_kabkota", "nama_varian",
        "tanggal", "harga_sekarang", "harga_sebelumnya", "pct_change"
    ])
    return df


def _get_existing_alert_keys(db: Session, tanggal: str) -> set:
    """
    Ambil kombinasi (kode_kabkota + nama_komoditas) yang sudah punya
    peringatan hari ini agar tidak duplikat insert.
    """
    query = text("""
        SELECT kode_kabkota || '|' || nama_komoditas AS alert_key
        FROM peringatan_dini
        WHERE DATE(tanggal_deteksi) = :tanggal
    """)
    result = db.execute(query, {"tanggal": tanggal})
    return {row[0] for row in result.fetchall()}


def run_ews_detection(
    db: Session,
    threshold_pct: Optional[float] = None,
    tanggal_akhir: Optional[str] = None,
    window_days: int = 7,
) -> EWSResult:
    """
    FUNGSI UTAMA: Menjalankan Early Warning System end-to-end.

    Args:
        db            : SQLAlchemy session
        threshold_pct : Persentase lonjakan minimum untuk memicu peringatan
                        (default dari settings = 15.0%)
        tanggal_akhir : Tanggal referensi 'YYYY-MM-DD' (None = tanggal max di DB)
        window_days   : Jumlah hari untuk baseline harga sebelumnya (default: 7)

    Returns:
        EWSResult: Ringkasan hasil deteksi
    """
    ews_result = EWSResult()

    if threshold_pct is None:
        threshold_pct = settings.PRICE_SPIKE_THRESHOLD_PERCENT
    ews_result.threshold_used = threshold_pct

    logger.info("=" * 55)
    logger.info("  MEMULAI EARLY WARNING SYSTEM DETECTION")
    logger.info("=" * 55)
    logger.info(f"Threshold: {threshold_pct}% | Window: {window_days} hari")

    # ── LANGKAH 1: Ambil data perubahan harga ────────────────────────────────
    df = _fetch_price_changes(db, tanggal_akhir, window_days)

    if df.empty:
        msg = (
            "Tidak ada data harga perbandingan. "
            "Pastikan ada minimal 2 periode data (kemarin & sekarang)."
        )
        ews_result.errors.append(msg)
        logger.warning(msg)
        return ews_result

    ews_result.n_checked = len(df)
    logger.info(f"Memeriksa {len(df)} kombinasi kota-komoditas...")

    # ── LANGKAH 2: Filter yang melebihi threshold ────────────────────────────
    df_alerts = df[df["pct_change"] > threshold_pct].copy()

    if df_alerts.empty:
        logger.info(
            f"Tidak ada lonjakan harga > {threshold_pct}% terdeteksi. "
            f"Sistem dalam kondisi aman."
        )
        return ews_result

    logger.info(f"Terdeteksi {len(df_alerts)} lonjakan harga!")

    # ── LANGKAH 3: Hindari duplikat ──────────────────────────────────────────
    today_str = datetime.now().strftime("%Y-%m-%d")
    existing_keys = _get_existing_alert_keys(db, today_str)

    # ── LANGKAH 4: Buat records peringatan ───────────────────────────────────
    new_alerts = []
    tanggal_sekarang = datetime.now(timezone.utc)

    for _, row in df_alerts.iterrows():
        alert_key = f"{row['kode_kabkota']}|{row['nama_varian']}"
        if alert_key in existing_keys:
            logger.debug(f"Skip duplikat: {alert_key}")
            continue

        alert_record = {
            "id_harga":           int(row["id_harga"]) if pd.notna(row["id_harga"]) else None,
            "kode_kabkota":       row["kode_kabkota"],
            "nama_komoditas":     row["nama_varian"],
            "harga_sebelumnya":   float(row["harga_sebelumnya"]),
            "harga_sekarang":     float(row["harga_sekarang"]),
            "persentase_lonjakan": round(float(row["pct_change"]), 2),
            "tanggal_deteksi":    tanggal_sekarang,
            "status":             "Baru",
        }
        new_alerts.append(alert_record)

        # Preview untuk response API (max 10)
        if len(ews_result.alerts_preview) < 10:
            ews_result.alerts_preview.append({
                "kota":         row["nama_kabkota"],
                "komoditas":    row["nama_varian"],
                "harga_lama":   f"Rp {row['harga_sebelumnya']:,.0f}",
                "harga_baru":   f"Rp {row['harga_sekarang']:,.0f}",
                "lonjakan_pct": f"{row['pct_change']:.1f}%",
                "tanggal":      str(row["tanggal"]),
            })

    # ── LANGKAH 5: Bulk insert peringatan baru ───────────────────────────────
    if new_alerts:
        db.execute(pg_insert(PeringatanDini).values(new_alerts))
        db.commit()
        ews_result.n_alerts_created = len(new_alerts)
        logger.info(f"Berhasil mencatat {len(new_alerts)} peringatan baru.")
    else:
        logger.info("Semua peringatan sudah tercatat hari ini (duplikat dihindari).")

    logger.info("=" * 55)
    logger.info("  EWS DETECTION SELESAI")
    logger.info("=" * 55)

    return ews_result
