# ========================================================
# backend/scripts/seed_koordinat.py
# Script seeder untuk mengisi kolom latitude & longitude
# pada tabel kabupaten_kota dari file data/koordinat_kabkota.json
# ========================================================
import os
import sys
import json
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))
os.chdir(str(backend_dir))

from app.core.database import SessionLocal
from app.models.wilayah import KabupatenKota

def seed_koordinat():
    json_path = backend_dir / "app" / "data" / "koordinat_kabkota.json"
    if not json_path.exists():
        print(f"[ERROR] File koordinat tidak ditemukan: {json_path}")
        return

    with open(json_path, "r", encoding="utf-8") as f:
        coords_data = json.load(f)

    db = SessionLocal()
    try:
        updated = 0
        total_in_db = db.query(KabupatenKota).count()
        print(f"Total Kabupaten/Kota di database: {total_in_db}")

        for kode, data in coords_data.items():
            kabkota = db.query(KabupatenKota).filter(
                (KabupatenKota.kode_kabkota == kode) | 
                (KabupatenKota.kode_kabkota == kode.lstrip("0"))
            ).first()

            if kabkota:
                kabkota.latitude = data["latitude"]
                kabkota.longitude = data["longitude"]
                updated += 1

        db.commit()
        print(f"[OK] Berhasil memperbarui koordinat {updated} kabupaten/kota.")
    except Exception as e:
        db.rollback()
        print(f"[ERROR] Gagal seeding koordinat: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_koordinat()
