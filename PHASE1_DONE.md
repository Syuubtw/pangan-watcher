# Phase 1 Complete - Database & Backend Setup

Semua file backend berhasil dibuat di:
C:\Users\andir\Desktop\pangan-watcher\backend\

STRUKTUR:

- app/main.py (Entry point FastAPI)
- app/core/config.py, database.py, security.py
- app/models/ (7 tabel: users, provinsi, kabkota, komoditas, harga_harian, hasil_klaster, peringatan_dini)
- app/services/ingestion_service.py (Pandas Excel processor)
- app/api/v1/endpoints/upload.py (POST endpoint)
- scripts/seed_admin.py

CARA JALANKAN:

1. Buat DB: CREATE DATABASE pangan_watcher_db; (di pgAdmin)
2. Edit backend\.env -> isi password PostgreSQL
3. cd backend && python -m venv venv && .\venv\Scripts\Activate.ps1
4. pip install -r requirements.txt
5. python scripts/seed_admin.py
6. uvicorn app.main:app --reload --port 8000
7. Buka http://localhost:8000/docs

.\venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
