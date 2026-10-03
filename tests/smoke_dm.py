"""ทดสอบข้อความส่วนตัว (DM): ส่ง/รับ, ยังไม่อ่าน, กล่องข้อความ, ค้นหาสมาชิก, แนบรูป, สิทธิ์

    python tests/smoke_dm.py
"""
import io, os, sys, tempfile
db_file = tempfile.mktemp(suffix=".db")
os.environ["DATABASE_URL"] = f"sqlite:///{db_file}"
os.environ.setdefault("SECRET_KEY", "test")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import app.routers.cloud as cloud_mod
cloud_mod.UPLOAD_ROOT = tempfile.mkdtemp()
import app.routers.media as media_mod
media_mod.UPLOAD_ROOT = cloud_mod.UPLOAD_ROOT

from fastapi.testclient import TestClient
from app.main import app

n = 0
def check(name, cond):
    global n
    if not cond:
        raise SystemExit(f"❌ {name}")
    n += 1; print(f"  ✅ {name}")

def client_for(u):
    c = TestClient(app)
    c.post("/members/register", data=dict(full_name=u.title(), username=u, email=f"{u}@t.local", phone="", password="password123", confirm="password123"))
    r = c.post("/members/login", data=dict(username=u, password="password123"), follow_redirects=False)
    c.cookies.set("nrw_token", r.cookies["nrw_token"]); return c

ann, bob, cat = (client_for(u) for u in ("ann", "bob", "cat"))

print("── ส่ง/รับ ──")
check("ไม่ login ใช้ไม่ได้", TestClient(app).get("/dm/inbox").status_code == 401)
check("ค้นหาสมาชิกเจอ (ไม่รวมตัวเอง)", [u["username"] for u in ann.get("/dm/users?q=b").json()["users"]] == ["bob"])
check("ส่งหาตัวเองไม่ได้", ann.post("/dm/with/ann", json={"text": "hi"}).status_code == 404)
check("ส่งหาคนที่ไม่มีอยู่ไม่ได้", ann.post("/dm/with/nobody", json={"text": "hi"}).status_code == 404)
check("ข้อความว่างไม่ได้", ann.post("/dm/with/bob", json={"text": "  "}).status_code == 400)
ann.post("/dm/with/bob", json={"text": "สวัสดี bob"})
ann.post("/dm/with/BOB", json={"text": "ของยังอยู่ไหม"})
check("bob มี 2 ข้อความยังไม่อ่าน", bob.get("/dm/unread").json()["total"] == 2)
inbox = bob.get("/dm/inbox").json()
check("กล่องข้อความ bob แสดง ann + ข้อความล่าสุด", inbox["conversations"][0]["username"] == "ann"
      and inbox["conversations"][0]["last"] == "ของยังอยู่ไหม" and inbox["total_unread"] == 2)
conv = bob.get("/dm/with/ann").json()
check("bob อ่านบทสนทนา เรียงเก่า→ใหม่", [m["text"] for m in conv["messages"]] == ["สวัสดี bob", "ของยังอยู่ไหม"] and not conv["messages"][0]["mine"])
check("อ่านแล้ว → ยังไม่อ่าน = 0", bob.get("/dm/unread").json()["total"] == 0)
check("ข้อความของตัวเองไม่นับเป็นยังไม่อ่าน", ann.get("/dm/unread").json()["total"] == 0)
check("ann เห็น 'คุณ:' นำหน้าข้อความล่าสุดของตัวเอง", ann.get("/dm/inbox").json()["conversations"][0]["last"].startswith("คุณ:"))
last = conv["messages"][-1]["id"]

print("── รูป + ความเป็นส่วนตัว ──")
img = bob.post("/media/images", files={"file": ("a.png", io.BytesIO(b"\x89PNG\r\n\x1a\nxx"), "image/png")}).json()["url"]
bob.post("/dm/with/ann", json={"text": "", "images": [img]})
new = ann.get(f"/dm/with/bob?after={last}").json()["messages"]
check("ส่งรูปอย่างเดียวได้ + after ดึงเฉพาะใหม่", len(new) == 1 and new[0]["images"] == [img])
check("กล่องข้อความแสดง 📷 รูปภาพ", ann.get("/dm/inbox").json()["conversations"][0]["last"] == "📷 รูปภาพ")
check("cat ไม่เห็นบทสนทนาของ ann กับ bob", cat.get("/dm/inbox").json()["conversations"] == [] and cat.get("/dm/unread").json()["total"] == 0)
cat.post("/dm/with/ann", json={"text": "หวัดดี"})
order = [c["username"] for c in ann.get("/dm/inbox").json()["conversations"]]
check("บทสนทนาล่าสุดขึ้นก่อน", order == ["cat", "bob"])
check("ann ยังไม่อ่าน 1 (จาก cat)", ann.get("/dm/unread").json()["total"] == 1)
check("ห้องแชทเดิมเห็น DM เดียวกัน", any(m["text"] == "สวัสดี bob" for m in bob.get("/chat/messages?room=dm:ann").json()["messages"]))

os.remove(db_file)
print(f"\n✅ ผ่านทั้งหมด {n} ข้อ")
