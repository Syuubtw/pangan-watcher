# ========================================================
# app/models/user.py
# Model tabel `users` untuk autentikasi admin
# ========================================================
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from app.core.database import Base


class User(Base):
    """
    Tabel pengguna sistem (admin).
    
    Kolom:
    - id          : Primary key auto-increment
    - username    : Username unik untuk login
    - hashed_password: Password yang sudah di-hash dengan bcrypt
    - role        : Peran pengguna ('admin' atau 'viewer')
    - is_active   : Apakah akun aktif
    - created_at  : Waktu pembuatan akun (otomatis diisi)
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default="viewer")
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', role='{self.role}')>"
