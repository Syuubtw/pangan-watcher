# ========================================================
# app/models/klaster.py
# Model tabel `hasil_klaster` - Output K-Means
# ========================================================
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class HasilKlaster(Base):
    """
    Tabel hasil komputasi K-Means Clustering.
    Setelah algoritma berjalan, tiap baris menyimpan status zona
    untuk satu kabupaten/kota pada satu periode proses tertentu.
    
    Inilah data yang akan di-fetch oleh Leaflet.js untuk 
    mewarnai peta (Choropleth) tanpa lag!
    
    Status Zona:
    - 'Aman'    : Cluster dengan harga rata-rata terendah (hijau)
    - 'Waspada' : Cluster dengan harga rata-rata menengah (kuning)
    - 'Kritis'  : Cluster dengan harga rata-rata tertinggi (merah)
    
    Kolom:
    - id_klaster    : Primary key auto-increment
    - kode_kabkota  : FK ke kabupaten_kota
    - tanggal_proses: Kapan K-Means dijalankan (stempel waktu)
    - status_zona   : Label cluster ('Aman', 'Waspada', 'Kritis')
    - cluster_id    : Nomor cluster asli dari scikit-learn (0, 1, 2)
    """
    __tablename__ = "hasil_klaster"

    id_klaster = Column(Integer, primary_key=True, autoincrement=True, index=True)
    kode_kabkota = Column(
        String(10),
        ForeignKey("kabupaten_kota.kode_kabkota", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tanggal_proses = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    status_zona = Column(String(20), nullable=False)  # 'Aman', 'Waspada', 'Kritis'
    cluster_id = Column(Integer, nullable=False)       # 0, 1, atau 2
    periode_bulan = Column(String(7), nullable=True, index=True) # '2026-01', dll

    # Relasi
    kabupaten_kota = relationship("KabupatenKota", back_populates="hasil_klaster")

    def __repr__(self):
        return (
            f"<HasilKlaster(id={self.id_klaster}, "
            f"kabkota='{self.kode_kabkota}', "
            f"zona='{self.status_zona}')>"
        )
