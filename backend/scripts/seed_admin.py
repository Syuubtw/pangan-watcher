import sys
import os
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal, engine, Base
from app.core.security import get_password_hash
from app.models.user import User
import app.models  # noqa

def seed_admin():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.username == "admin").first()
        if existing:
            print("[OK] Akun admin sudah ada. Tidak perlu dibuat ulang.")
            return
        admin_user = User(
            username="admin",
            hashed_password=get_password_hash("admin123"),
            role="admin",
            is_active=True,
        )
        db.add(admin_user)
        db.commit()
        print("[OK] Akun admin berhasil dibuat:")
        print("  Username : admin")
        print("  Password : admin123")
        print("  [!] GANTI PASSWORD setelah login pertama kali!")
    except Exception as e:
        print(f"[ERROR] {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_admin()
