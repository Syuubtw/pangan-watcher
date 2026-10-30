# ========================================================
# app/models/wilayah.py
# Model tabel `provinsi` dan `kabupaten_kota`
# ========================================================
from sqlalchemy import Column, String, Float, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class Provinsi(Base):
    """
    Tabel referensi data provinsi Indonesia.
    
    Kolom:
    - kode_provinsi : Kode BPS provinsi (PK, e.g., "33" untuk Jawa Tengah)
    - nama_provinsi : Nama lengkap provinsi
    """
    __tablename__ = "provinsi"

    kode_provinsi = Column(String(10), primary_key=True)
    nama_provinsi = Column(String(100), nullable=False)

    # Relasi: satu provinsi memiliki banyak kabupaten/kota
    kabupaten_kota = relationship(
        "KabupatenKota",
        back_populates="provinsi",
        lazy="select"
    )

    def __repr__(self):
        return f"<Provinsi(kode='{self.kode_provinsi}', nama='{self.nama_provinsi}')>"


class KabupatenKota(Base):
    """
    Tabel referensi data kabupaten/kota Indonesia.
    latitude & longitude digunakan untuk pin marker pada peta Leaflet.
    
    Kolom:
    - kode_kabkota  : Kode BPS kabkota (PK, e.g., "3374" untuk Semarang)
    - kode_provinsi : Foreign key ke tabel provinsi
    - nama_kabkota  : Nama lengkap kabupaten/kota
    - latitude      : Koordinat lintang (untuk Leaflet map)
    - longitude     : Koordinat bujur (untuk Leaflet map)
    """
    __tablename__ = "kabupaten_kota"

    kode_kabkota = Column(String(10), primary_key=True)
    kode_provinsi = Column(
        String(10),
        ForeignKey("provinsi.kode_provinsi", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    nama_kabkota = Column(String(150), nullable=False)
    latitude = Column(Float, nullable=True)   # Diisi dari GeoJSON/script seeder
    longitude = Column(Float, nullable=True)  # Diisi dari GeoJSON/script seeder

    # Relasi ke induk (provinsi)
    provinsi = relationship("Provinsi", back_populates="kabupaten_kota")

    # Relasi ke tabel data harga
    harga_harian = relationship("HargaHarian", back_populates="kabupaten_kota")

    # Relasi ke tabel hasil clustering
    hasil_klaster = relationship("HasilKlaster", back_populates="kabupaten_kota")

    def __repr__(self):
        return f"<KabupatenKota(kode='{self.kode_kabkota}', nama='{self.nama_kabkota}')>"
