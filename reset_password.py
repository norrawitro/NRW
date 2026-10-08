"""ตั้งรหัสผ่านใหม่ให้บัญชีสมาชิก (ใช้เมื่อลืมรหัส เช่นบัญชีผู้ดูแล) — รันบนเครื่องเซิร์ฟเวอร์เท่านั้น

    python reset_password.py <username>              # ถามรหัสใหม่ 2 ครั้ง (ไม่แสดงบนจอ)
    python reset_password.py --list-admins           # ดูว่าบัญชีไหนเป็นผู้ดูแล
รหัสเก็บเป็น bcrypt hash — ไม่มีใครอ่านรหัสเดิมได้ จึงต้องตั้งใหม่แทน"""
import getpass
import sys

from app.database import SessionLocal
import app.models  # noqa: F401
from app.models.user import User
from app.auth import hash_password

if len(sys.argv) < 2:
    sys.exit(__doc__)

db = SessionLocal()
try:
    if sys.argv[1] == "--list-admins":
        admins = db.query(User).filter(User.is_admin == True).order_by(User.username).all()
        print("ผู้ดูแลระบบ:", ", ".join(f"{u.username} ({u.email})" for u in admins) or "— ยังไม่มี — ใช้ python make_admin.py <username>")
        sys.exit(0)
    user = db.query(User).filter(User.username == sys.argv[1].strip().lower()).first()
    if not user:
        sys.exit(f"❌ ไม่พบบัญชี: {sys.argv[1]}  (ดูรายชื่อผู้ดูแล: python reset_password.py --list-admins)")
    p1 = getpass.getpass(f"รหัสผ่านใหม่ของ {user.username} (อย่างน้อย 8 ตัวอักษร): ")
    if len(p1) < 8:
        sys.exit("❌ รหัสสั้นเกินไป")
    if getpass.getpass("พิมพ์อีกครั้ง: ") != p1:
        sys.exit("❌ รหัสไม่ตรงกัน")
    user.hashed_pw = hash_password(p1)
    db.commit()
    print(f"✅ ตั้งรหัสใหม่ให้ {user.username} แล้ว{' (ผู้ดูแลระบบ)' if user.is_admin else ''} — ล็อกอินได้ที่ /members/login")
finally:
    db.close()
