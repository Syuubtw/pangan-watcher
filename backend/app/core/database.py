# ========================================================
# app/core/database.py
# Setup koneksi database menggunakan SQLAlchemy 2.0
# ========================================================
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.core.config import settings


# Engine: koneksi utama ke PostgreSQL
# pool_pre_ping=True: memastikan koneksi masih hidup sebelum dipakai
# pool_size + max_overflow: connection pooling agar tidak kehabisan koneksi
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    echo=settings.DEBUG,  # Print SQL queries saat DEBUG=True
)

# Session factory: dipakai untuk membuat sesi database
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


class Base(DeclarativeBase):
    """
    Base class untuk semua SQLAlchemy models.
    Semua model harus mewarisi class ini.
    """
    pass


def get_db():
    """
    FastAPI Dependency untuk mendapatkan sesi database.
    Pola 'yield' memastikan sesi selalu ditutup setelah request selesai,
    bahkan jika terjadi exception (mencegah connection leak).
    
    Cara pakai di endpoint:
        db: Session = Depends(get_db)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
