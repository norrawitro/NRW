"""ตั้ง/เปลี่ยนรหัสผ่าน AI Agent (ศูนย์ AI → 🛠️ AI Agent) — เก็บเป็นค่า hash ใน .env ไม่เก็บรหัสจริง

    python set_agent_password.py            # ถามรหัส 2 ครั้ง แล้วเขียน AGENT_PASSWORD_HASH ลง .env
    python set_agent_password.py --off      # ปิด AI Agent (ลบรหัสออก)
แล้วรัน: bash restart.sh"""
import getpass
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app.routers.agent import make_hash  # noqa: E402

ENV = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")


def write_env(key: str, value: str | None) -> None:
    lines = open(ENV, encoding="utf-8").read().splitlines() if os.path.exists(ENV) else []
    lines = [l for l in lines if not re.match(rf"^\s*{key}\s*=", l)]
    if value is not None:
        lines.append(f"{key}={value}")
    with open(ENV, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    os.chmod(ENV, 0o600)


if "--off" in sys.argv:
    write_env("AGENT_PASSWORD_HASH", None)
    print("ปิด AI Agent แล้ว — รัน bash restart.sh")
    sys.exit(0)

p1 = getpass.getpass("ตั้งรหัสผ่าน AI Agent (อย่างน้อย 10 ตัวอักษร): ")
if len(p1) < 10:
    sys.exit("❌ รหัสสั้นเกินไป (ต้องอย่างน้อย 10 ตัวอักษร)")
if getpass.getpass("พิมพ์อีกครั้ง: ") != p1:
    sys.exit("❌ รหัสไม่ตรงกัน")
write_env("AGENT_PASSWORD_HASH", make_hash(p1))
print("✅ ตั้งรหัสผ่านแล้ว (เก็บเป็น hash ใน .env) — รัน bash restart.sh แล้วเข้า ศูนย์ AI → 🛠️ AI Agent")
