# ========================================================
# app/services/ingestion_service.py
# Layanan untuk memproses file Excel harga pangan dan
# menyimpan data bersih ke PostgreSQL via SQLAlchemy.
#
# ALUR KERJA:
# 1. Baca file Excel dengan Pandas (chunking untuk efisiensi memori)
# 2. Bersihkan data (hapus NaN, validasi tipe data)
# 3. Upsert data master (Provinsi, KabupatenKota, Komoditas) + koordinat
# 4. Bulk insert data harga_harian
# 5. Jalankan Early Warning System (EWS)
# ========================================================
import os
import json
import logging
from pathlib import Path
from datetime import date
from typing import Optional

import pandas as pd
import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy import select

from app.models.wilayah import Provinsi, KabupatenKota
from app.models.komoditas import Komoditas
from app.models.harga import HargaHarian
from app.models.klaster import HasilKlaster
from app.models.peringatan import PeringatanDini
from app.core.config import settings

logger = logging.getLogger(__name__)

# Nama kolom Excel
COL_KODE_PROV    = "Kode Provinsi"
COL_NAMA_PROV    = "Nama Provinsi"
COL_KODE_KABKOTA = "Kode Kab/Kota"
COL_NAMA_KABKOTA = "Nama Kab/Kota"
COL_NAMA_VARIAN  = "Nama Varian"
COL_TANGGAL      = "Tanggal"
COL_HARGA        = "Harga"
COL_SATUAN       = "Satuan"

REQUIRED_COLUMNS = [
    COL_KODE_PROV, COL_NAMA_PROV, COL_KODE_KABKOTA, COL_NAMA_KABKOTA,
    COL_NAMA_VARIAN, COL_TANGGAL, COL_HARGA, COL_SATUAN,
]

CHUNK_SIZE = 50_000


class IngestionResult:
    """Hasil ringkasan proses ingestion untuk response API."""
    def __init__(self):
        self.total_rows_read: int = 0
        self.rows_inserted: int = 0
        self.rows_skipped: int = 0
        self.provinsi_upserted: int = 0
        self.kabkota_upserted: int = 0
        self.komoditas_upserted: int = 0
        self.errors: list[str] = []

    def to_dict(self) -> dict:
        return {
            "total_rows_read": self.total_rows_read,
            "rows_inserted": self.rows_inserted,
            "rows_skipped": self.rows_skipped,
            "provinsi_upserted": self.provinsi_upserted,
            "kabkota_upserted": self.kabkota_upserted,
            "komoditas_upserted": self.komoditas_upserted,
            "errors": self.errors,
            "status": "success" if not self.errors else "partial_success",
        }


def _validate_columns(df: pd.DataFrame) -> list[str]:
    """Validasi apakah semua kolom wajib ada di file Excel."""
    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    return missing


def _clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Membersihkan DataFrame mentah dari Excel."""
    original_len = len(df)
    df = df.dropna(subset=[COL_KODE_PROV, COL_KODE_KABKOTA, COL_NAMA_VARIAN, COL_TANGGAL, COL_HARGA])
    
    df[COL_KODE_PROV]    = df[COL_KODE_PROV].astype(str).str.strip()
    df[COL_NAMA_PROV]    = df[COL_NAMA_PROV].astype(str).str.strip()
    df[COL_KODE_KABKOTA] = df[COL_KODE_KABKOTA].astype(str).str.strip().str.zfill(4)
    df[COL_NAMA_KABKOTA] = df[COL_NAMA_KABKOTA].astype(str).str.strip()
    df[COL_NAMA_VARIAN]  = df[COL_NAMA_VARIAN].astype(str).str.strip()
    df[COL_SATUAN]       = df[COL_SATUAN].astype(str).str.strip()
    
    df[COL_TANGGAL] = pd.to_datetime(df[COL_TANGGAL], dayfirst=True, errors="coerce")
    df = df.dropna(subset=[COL_TANGGAL])
    
    df[COL_HARGA] = pd.to_numeric(df[COL_HARGA], errors="coerce")
    df = df.dropna(subset=[COL_HARGA])
    df = df[df[COL_HARGA] > 0]
    
    df = df.drop_duplicates(
        subset=[COL_KODE_KABKOTA, COL_NAMA_VARIAN, COL_TANGGAL]
    )
    
    cleaned_len = len(df)
    logger.info(
        f"Data cleaning: {original_len} -> {cleaned_len} baris "
        f"(dihapus: {original_len - cleaned_len})"
    )
    return df


def _upsert_master_data(df: pd.DataFrame, db: Session) -> dict:
    """Upsert data master (Provinsi, KabupatenKota, Komoditas) + koordinat."""
    counts = {"provinsi": 0, "kabkota": 0, "komoditas": 0}
    
    # 1. Provinsi
    provinsi_data = (
        df[[COL_KODE_PROV, COL_NAMA_PROV]]
        .drop_duplicates(subset=[COL_KODE_PROV])
        .rename(columns={COL_KODE_PROV: "kode_provinsi", COL_NAMA_PROV: "nama_provinsi"})
        .to_dict("records")
    )
    if provinsi_data:
        stmt = pg_insert(Provinsi).values(provinsi_data)
        stmt = stmt.on_conflict_do_nothing(index_elements=["kode_provinsi"])
        result = db.execute(stmt)
        counts["provinsi"] = result.rowcount
        logger.info(f"Provinsi: {counts['provinsi']} baris di-upsert")

    # Load koordinat jika ada
    coords_dict = {}
    coords_file = Path(__file__).resolve().parent.parent / "data" / "koordinat_kabkota.json"
    if coords_file.exists():
        try:
            with open(coords_file, "r", encoding="utf-8") as f:
                coords_dict = json.load(f)
        except Exception as e:
            logger.warning(f"Tidak dapat membaca file koordinat: {e}")

    # 2. KabupatenKota
    unique_kab = (
        df[[COL_KODE_KABKOTA, COL_KODE_PROV, COL_NAMA_KABKOTA]]
        .drop_duplicates(subset=[COL_KODE_KABKOTA])
    )
    kabkota_data = []
    for _, row in unique_kab.iterrows():
        k_code = str(row[COL_KODE_KABKOTA]).strip().zfill(4)
        c_info = coords_dict.get(k_code, {})
        kabkota_data.append({
            "kode_kabkota": k_code,
            "kode_provinsi": str(row[COL_KODE_PROV]).strip(),
            "nama_kabkota": str(row[COL_NAMA_KABKOTA]).strip(),
            "latitude": c_info.get("latitude"),
            "longitude": c_info.get("longitude"),
        })

    if kabkota_data:
        stmt = pg_insert(KabupatenKota).values(kabkota_data)
        stmt = stmt.on_conflict_do_update(
            index_elements=["kode_kabkota"],
            set_={
                "nama_kabkota": stmt.excluded.nama_kabkota,
                "latitude": stmt.excluded.latitude,
                "longitude": stmt.excluded.longitude,
            }
        )
        result = db.execute(stmt)
        counts["kabkota"] = result.rowcount
        logger.info(f"KabupatenKota: {counts['kabkota']} baris di-upsert")

    # 3. Komoditas
    komoditas_data = (
        df[[COL_NAMA_VARIAN, COL_SATUAN]]
        .drop_duplicates(subset=[COL_NAMA_VARIAN])
        .rename(columns={COL_NAMA_VARIAN: "nama_varian", COL_SATUAN: "satuan"})
        .to_dict("records")
    )
    if komoditas_data:
        stmt = pg_insert(Komoditas).values(komoditas_data)
        stmt = stmt.on_conflict_do_nothing(index_elements=["nama_varian"])
        result = db.execute(stmt)
        counts["komoditas"] = result.rowcount
        logger.info(f"Komoditas: {counts['komoditas']} baris di-upsert")

    db.commit()
    return counts


def _build_lookup_maps(db: Session) -> tuple[dict, dict]:
    """Membangun dictionary lookup untuk memetakan nama ke ID/kode di database."""
    kabkota_rows = db.execute(select(KabupatenKota.kode_kabkota)).fetchall()
    kabkota_set = {row[0] for row in kabkota_rows}

    komoditas_rows = db.execute(
        select(Komoditas.nama_varian, Komoditas.id_komoditas)
    ).fetchall()
    komoditas_map = {row[0]: row[1] for row in komoditas_rows}

    return kabkota_set, komoditas_map


from psycopg2.extras import execute_values

def _insert_harga_chunk(
    chunk_df: pd.DataFrame,
    kabkota_set: set,
    komoditas_map: dict,
    db: Session,
) -> tuple[int, int]:
    """High-performance bulk insert menggunakan raw SQL execute_values (10x lebih cepat)."""
    tuples = []
    skipped = 0

    for _, row in chunk_df.iterrows():
        kode_kabkota = str(row[COL_KODE_KABKOTA]).strip().zfill(4)
        nama_varian  = str(row[COL_NAMA_VARIAN]).strip()

        if kode_kabkota not in kabkota_set or nama_varian not in komoditas_map:
            skipped += 1
            continue

        tuples.append((
            kode_kabkota,
            komoditas_map[nama_varian],
            row[COL_TANGGAL].date(),
            float(row[COL_HARGA]),
        ))

    if not tuples:
        return 0, skipped

    # Gunakan raw connection psycopg2 untuk execute_values berkecepatan tinggi
    raw_conn = db.connection().connection
    with raw_conn.cursor() as cur:
        query = """
            INSERT INTO harga_harian (kode_kabkota, id_komoditas, tanggal, harga)
            VALUES %s
            ON CONFLICT DO NOTHING
        """
        execute_values(cur, query, tuples, page_size=10000)
    raw_conn.commit()

    inserted = len(tuples)
    logger.info(f"  Chunk: {inserted} inserted, {skipped} skipped")
    return inserted, skipped


def process_excel_file(file_path: str, db: Session) -> IngestionResult:
    """FUNGSI UTAMA: Memproses file Excel harga pangan end-to-end."""
    result = IngestionResult()
    path = Path(file_path)

    if not path.exists():
        result.errors.append(f"File tidak ditemukan: {file_path}")
        return result

    logger.info(f"Mulai membaca file: {path.name}")

    try:
        # Deteksi sheet yang berisi data
        excel_file = pd.ExcelFile(file_path, engine="openpyxl")
        sheet_to_use = excel_file.sheet_names[0]
        
        if "Harga Harian" in excel_file.sheet_names:
            sheet_to_use = "Harga Harian"
        else:
            for sname in excel_file.sheet_names:
                try:
                    preview = pd.read_excel(excel_file, sheet_name=sname, nrows=2)
                    if any(col in preview.columns for col in REQUIRED_COLUMNS):
                        sheet_to_use = sname
                        break
                except Exception:
                    continue

        logger.info(f"Membaca Excel sheet '{sheet_to_use}' ke DataFrame...")
        df_full = pd.read_excel(
            excel_file,
            sheet_name=sheet_to_use,
            dtype={
                COL_KODE_PROV:    str,
                COL_KODE_KABKOTA: str,
            },
        )
        result.total_rows_read = len(df_full)
        logger.info(f"Total baris dibaca: {result.total_rows_read:,}")

        # Validasi Kolom
        missing_cols = _validate_columns(df_full)
        if missing_cols:
            msg = f"Kolom wajib tidak ditemukan: {missing_cols}"
            result.errors.append(msg)
            logger.error(msg)
            return result

        # Bersihkan Data
        logger.info("Membersihkan data...")
        df_clean = _clean_dataframe(df_full)
        del df_full

        if df_clean.empty:
            result.errors.append("Tidak ada data valid setelah proses pembersihan.")
            return result

        # Upsert Data Master
        logger.info("Menyimpan data master (provinsi, kabkota, komoditas)...")
        master_counts = _upsert_master_data(df_clean, db)
        result.provinsi_upserted  = master_counts["provinsi"]
        result.kabkota_upserted   = master_counts["kabkota"]
        result.komoditas_upserted = master_counts["komoditas"]

        # Bangun Lookup Map
        logger.info("Membangun lookup map dari database...")
        kabkota_set, komoditas_map = _build_lookup_maps(db)

        # Bulk Insert Harga dalam Chunk
        logger.info(f"Mulai bulk insert harga dalam chunk {CHUNK_SIZE:,} baris...")
        total_rows = len(df_clean)
        
        for chunk_start in range(0, total_rows, CHUNK_SIZE):
            chunk_end = min(chunk_start + CHUNK_SIZE, total_rows)
            chunk_df  = df_clean.iloc[chunk_start:chunk_end]
            
            logger.info(
                f"Memproses chunk [{chunk_start:,} - {chunk_end:,}] "
                f"dari {total_rows:,}..."
            )
            
            inserted, skipped = _insert_harga_chunk(
                chunk_df, kabkota_set, komoditas_map, db
            )
            result.rows_inserted += inserted
            result.rows_skipped  += skipped

        logger.info(
            f"Ingestion selesai: "
            f"{result.rows_inserted:,} inserted, "
            f"{result.rows_skipped:,} skipped"
        )

    except Exception as e:
        logger.exception(f"Error kritis saat ingestion: {e}")
        result.errors.append(f"Error: {str(e)}")
        db.rollback()

    return result
