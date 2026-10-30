# ========================================================
# app/models/komoditas.py
# Model tabel `komoditas`
# ========================================================
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from app.core.database import Base


class Komoditas(Base):
    """
    Tabel referensi master komoditas pangan.
    Setiap varian komoditas (e.g., 'Beras Premium', 'Beras Medium')
    diperlakukan sebagai entitas terpisah.
    
    Kolom:
    - id_komoditas : Primary key auto-increment
    - nama_varian  : Nama komoditas/varian (e.g., "Beras Premium", "Minyak Goreng")
    - satuan       : Satuan ukuran (e.g., "Kg", "Liter", "Butir")
    """
    __tablename__ = "komoditas"

    id_komoditas = Column(Integer, primary_key=True, autoincrement=True, index=True)
    nama_varian = Column(String(200), nullable=False, unique=True)
    satuan = Column(String(30), nullable=True)

    # Relasi ke tabel data harga
    harga_harian = relationship("HargaHarian", back_populates="komoditas")

    def __repr__(self):
        return f"<Komoditas(id={self.id_komoditas}, nama='{self.nama_varian}')>"
