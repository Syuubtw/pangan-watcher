# ========================================================
# app/models/peringatan.py
# Model tabel `peringatan_dini` - Output Early Warning System
# ========================================================
from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class PeringatanDini(Base):
    """
    Tabel log peringatan dini ketika harga komoditas di suatu kota
    mengalami lonjakan melebihi threshold yang ditentukan.
    
    Peringatan dibangkitkan oleh EWS (Early Warning System) di backend
    dan ditampilkan di halaman Alert Center frontend.
    
    Contoh data:
    "Peringatan: Beras Premium di Kota Semarang melonjak 15.3% pada 28 Jan 2026"
    
    Kolom:
    - id_peringatan        : Primary key auto-increment
    - id_harga             : FK ke harga_harian (record harga yang memicu peringatan)
    - kode_kabkota         : Kode wilayah (denormalized untuk query cepat)
    - nama_komoditas       : Nama komoditas (denormalized untuk query cepat)
    - harga_sebelumnya     : Harga pada periode sebelumnya (Rp)
    - harga_sekarang       : Harga saat peringatan terdeteksi (Rp)
    - persentase_lonjakan  : Persentase kenaikan harga (%)
    - tanggal_deteksi      : Waktu peringatan dicatat (otomatis)
    - status               : Status penanganan ('Baru', 'Ditinjau', 'Ditangani')
    """
    __tablename__ = "peringatan_dini"

    id_peringatan = Column(Integer, primary_key=True, autoincrement=True, index=True)
    id_harga = Column(
        Integer,
        ForeignKey("harga_harian.id_harga", ondelete="SET NULL"),
        nullable=True,
    )
    kode_kabkota = Column(String(10), nullable=False, index=True)
    nama_komoditas = Column(String(200), nullable=False)
    harga_sebelumnya = Column(Float, nullable=False)
    harga_sekarang = Column(Float, nullable=False)
    persentase_lonjakan = Column(Float, nullable=False)
    tanggal_deteksi = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    status = Column(String(20), nullable=False, default="Baru")  # Baru/Ditinjau/Ditangani

    # Relasi
    harga = relationship("HargaHarian", back_populates="peringatan_dini")

    def __repr__(self):
        return (
            f"<PeringatanDini(id={self.id_peringatan}, "
            f"komoditas='{self.nama_komoditas}', "
            f"lonjakan={self.persentase_lonjakan:.1f}%)>"
        )
