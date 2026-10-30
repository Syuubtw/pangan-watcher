# ========================================================
# app/models/harga.py
# Model tabel `harga_harian` - tabel FAKTA utama sistem
# ========================================================
from sqlalchemy import Column, Integer, String, Float, Date, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.core.database import Base


class HargaHarian(Base):
    """
    Tabel fakta utama yang menyimpan data harga komoditas per hari per kota.
    Ini adalah tabel terbesar dalam sistem (potensial ratusan ribu baris per bulan).
    
    Index komposit pada (kode_kabkota, id_komoditas, tanggal) 
    sangat penting untuk performa query agregasi K-Means.
    
    Kolom:
    - id_harga      : Primary key auto-increment
    - kode_kabkota  : FK ke kabupaten_kota
    - id_komoditas  : FK ke komoditas
    - tanggal       : Tanggal pencatatan harga
    - harga         : Harga dalam Rupiah
    """
    __tablename__ = "harga_harian"

    id_harga = Column(Integer, primary_key=True, autoincrement=True, index=True)
    kode_kabkota = Column(
        String(10),
        ForeignKey("kabupaten_kota.kode_kabkota", ondelete="CASCADE"),
        nullable=False,
    )
    id_komoditas = Column(
        Integer,
        ForeignKey("komoditas.id_komoditas", ondelete="CASCADE"),
        nullable=False,
    )
    tanggal = Column(Date, nullable=False)
    harga = Column(Float, nullable=False)

    # Relasi
    kabupaten_kota = relationship("KabupatenKota", back_populates="harga_harian")
    komoditas = relationship("Komoditas", back_populates="harga_harian")

    # Relasi ke tabel peringatan dini
    peringatan_dini = relationship("PeringatanDini", back_populates="harga")

    # Index komposit untuk mempercepat query analitik
    __table_args__ = (
        Index(
            "idx_harga_kabkota_komoditas_tanggal",
            "kode_kabkota",
            "id_komoditas",
            "tanggal",
        ),
        Index("idx_harga_tanggal", "tanggal"),
    )

    def __repr__(self):
        return (
            f"<HargaHarian(id={self.id_harga}, "
            f"kabkota='{self.kode_kabkota}', "
            f"komoditas={self.id_komoditas}, "
            f"tanggal={self.tanggal}, "
            f"harga={self.harga})>"
        )
