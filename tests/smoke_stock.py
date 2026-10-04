"""ทดสอบจัดการสต็อก: ประวัติทุกการเปลี่ยน (ลงสินค้า/ขาย/ยกเลิก/รับเข้า/เบิก/ตรวจนับ), สถานะใกล้หมด, สิทธิ์, CSV

    python tests/smoke_stock.py
"""
import os, sys, tempfile
db_file = tempfile.mktemp(suffix=".db")
os.environ["DATABASE_URL"] = f"sqlite:///{db_file}"
os.environ.setdefault("SECRET_KEY", "test")
os.environ["MODERATION"] = "off"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app.models.user import User
from app.services.wallet_ops import move_money

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

boss, sam, kim, buyer = (client_for(u) for u in ("boss", "sam", "kim", "buyer"))
db = SessionLocal(); db.query(User).filter(User.username == "boss").update({"is_admin": True})
move_money(db, db.query(User).filter(User.username == "buyer").first().id, 5000, "admin", "seed"); db.commit(); db.close()

print("── ประวัติอัตโนมัติ ──")
p = sam.post("/shop/my/products", json={"name": "เสื้อ", "price": 100, "stock": 10}).json()
check("ลงสินค้า → ประวัติ 'ลงสินค้า' +10", sam.get(f"/stock/{p['id']}/history").json()["moves"][0]["change"] == 10)
o = buyer.post("/shop/orders", json={"items": [{"product_id": p["id"], "qty": 3}], "address": "99 ถนนทดสอบ"}).json()
h = sam.get(f"/stock/{p['id']}/history").json()["moves"]
check("ขาย 3 → ประวัติ 'ขาย' -3 เหลือ 7", h[0]["kind"] == "sale" and h[0]["change"] == -3 and h[0]["balance"] == 7)
sam.post(f"/logistics/orders/{o['id']}/status", json={"status": "cancelled"})
h = sam.get(f"/stock/{p['id']}/history").json()["moves"]
check("ยกเลิกออเดอร์ → 'คืนจากยกเลิก' +3 เหลือ 10", h[0]["kind"] == "return" and h[0]["balance"] == 10)

print("── รับเข้า / เบิกออก / ตรวจนับ ──")
r = sam.post(f"/stock/{p['id']}/move", json={"kind": "in", "qty": 20, "note": "ล็อตใหม่"}).json()
check("รับเข้า 20 → 30", r["stock"] == 30)
check("เบิกเกินที่มี → 400", sam.post(f"/stock/{p['id']}/move", json={"kind": "out", "qty": 31}).status_code == 400)
r = sam.post(f"/stock/{p['id']}/move", json={"kind": "out", "qty": 2, "note": "ชำรุด"}).json()
check("เบิกออก 2 (ชำรุด) → 28", r["stock"] == 28)
r = sam.post(f"/stock/{p['id']}/move", json={"kind": "count", "qty": 4}).json()
check("ตรวจนับเหลือจริง 4 → สถานะ 'ใกล้หมด' (ค่าเริ่มต้นเตือนที่ 5)", r["stock"] == 4 and r["status"] == "low")
r = sam.put(f"/stock/{p['id']}/settings", json={"low_at": 2}).json()
check("ตั้งเตือนที่ 2 → ปกติ", r["status"] == "ok" and r["low_at"] == 2)
sam.post(f"/stock/{p['id']}/move", json={"kind": "count", "qty": 0})
lst = sam.get("/stock").json()
check("สรุป: 1 รายการ หมด 1", lst["summary"]["skus"] == 1 and lst["summary"]["out"] == 1 and lst["products"][0]["status"] == "out")
check("ขาย 30 วัน = 0 (ขายแล้วถูกยกเลิก)", lst["products"][0]["sold_30d"] == 0)
check("ฟอร์มแก้สินค้าบันทึกประวัติ 'แก้ในฟอร์ม'",
      sam.put(f"/shop/my/products/{p['id']}", json={"name": "เสื้อ", "price": 100, "stock": 12}).status_code == 200
      and sam.get(f"/stock/{p['id']}/history").json()["moves"][0]["kind"] == "edit")

buyer.post("/shop/orders", json={"items": [{"product_id": p["id"], "qty": 2}], "address": "99 ถนนทดสอบ"})
r = sam.get("/stock").json()["products"][0]
check("ขาย 30 วัน = 2 + ประมาณวันที่พอขาย", r["sold_30d"] == 2 and r["days_left"] == 150.0)

print("── สิทธิ์ + ผู้ดูแล + CSV ──")
check("kim จัดการสต็อกร้าน sam ไม่ได้", kim.post(f"/stock/{p['id']}/move", json={"kind": "in", "qty": 1}).status_code == 403)
check("kim ดูประวัติร้าน sam ไม่ได้", kim.get(f"/stock/{p['id']}/history").status_code == 403)
check("สมาชิกดูสต็อกทั้งระบบไม่ได้", sam.get("/stock?scope=all").status_code == 403)
pp = boss.post("/manage/api/products", json={"name": "ของแพลตฟอร์ม", "price": 50, "stock": 7}).json()
check("ผู้ดูแลเห็นสินค้าแพลตฟอร์ม", [x["name"] for x in boss.get("/stock?scope=platform").json()["products"]] == ["ของแพลตฟอร์ม"])
check("ผู้ดูแลจัดการสต็อกร้านสมาชิกได้", boss.post(f"/stock/{p['id']}/move", json={"kind": "in", "qty": 1}).status_code == 200)
check("ความเคลื่อนไหวล่าสุด (ทั้งระบบ)", len(boss.get("/stock/moves?scope=all").json()["moves"]) >= 8)
csv = sam.get("/stock/export.csv")
check("ส่งออก CSV ภาษาไทย", csv.status_code == 200 and "เสื้อ" in csv.text and csv.text.startswith("﻿"))
check("API เก่า /logistics/inventory ยังใช้ได้ + บันทึกประวัติ",
      boss.post(f"/logistics/inventory/{pp['id']}", json={"delta": -2}).json()["stock"] == 5
      and boss.get(f"/stock/{pp['id']}/history").json()["moves"][0]["kind"] == "out")

os.remove(db_file)
print(f"\n✅ ผ่านทั้งหมด {n} ข้อ")
