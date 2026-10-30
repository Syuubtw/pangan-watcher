import sys
from pathlib import Path

# Tambahkan direktori backend ke sys.path agar modul app bisa di-import oleh Vercel
backend_dir = Path(__file__).resolve().parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.main import app
