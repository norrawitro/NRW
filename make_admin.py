"""ตั้ง/ถอดสิทธิ์ผู้ดูแลระบบ (เข้า /manage ได้)

    python make_admin.py <username>           # ตั้งเป็น admin
    python make_admin.py <username> --remove  # ถอดสิทธิ์
"""
import sys

from app.database import SessionLocal
import app.models  # noqa: F401
from app.models.user import User

if len(sys.argv) < 2:
    sys.exit(__doc__)

db = SessionLocal()
try:
    user = db.query(User).filter(User.username == sys.argv[1].strip().lower()).first()
    if not user:
        sys.exit(f"ไม่พบ user: {sys.argv[1]}")
    user.is_admin = "--remove" not in sys.argv
    db.commit()
    print(f"{user.username}: is_admin = {user.is_admin}")
finally:
    db.close()
