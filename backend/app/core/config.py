# ========================================================
# app/core/config.py
# Konfigurasi aplikasi menggunakan Pydantic Settings.
# Nilai dibaca dari file .env secara otomatis.
# ========================================================
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from functools import lru_cache
from typing import Any


class Settings(BaseSettings):
    """
    Semua konfigurasi aplikasi. Pydantic Settings akan membaca
    nilai dari environment variables atau file .env secara otomatis.
    """
    # --- App ---
    APP_NAME: str = "Pangan Watcher API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug(cls, v: Any) -> bool:
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            v_lower = v.strip().lower()
            if v_lower in ("true", "1", "t", "yes", "y", "dev", "development"):
                return True
            return False
        return bool(v)

    # --- Database ---
    DATABASE_URL: str

    # --- JWT ---
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # --- Upload ---
    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_SIZE_MB: int = 200

    # --- K-Means ---
    N_CLUSTERS: int = 3
    PRICE_SPIKE_THRESHOLD_PERCENT: float = 15.0

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )


@lru_cache()
def get_settings() -> Settings:
    """
    Menggunakan lru_cache agar objek Settings hanya dibuat sekali
    (singleton pattern). Efisien untuk aplikasi production.
    """
    return Settings()


# Instance tunggal yang dipakai di seluruh aplikasi
settings = get_settings()
