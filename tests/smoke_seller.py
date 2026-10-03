"""ทดสอบร้านค้าของสมาชิก (ลงสินค้า, แยกออเดอร์ตามร้าน, พักเงินจนผู้ซื้อได้รับของ)

    python tests/smoke_seller.py
"""
import io, os, sys, tempfile
db_file = tempfile.mktemp(suffix=".db")
os.environ["DATABASE_URL"] = f"sqlite:///{db_file}"
os.environ.setdefault("SECRET_KEY", "test")
os.environ["MODERATION"] = "off"          # ทดสอบระบบซื้อขาย — การอนุมัติทดสอบใน smoke_moderation.py
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import app.routers.cloud as cloud_mod
cloud_mod.UPLOAD_ROOT = tempfile.mkdtemp()
import app.routers.shop as shop_mod
shop_mod.UPLOAD_ROOT = cloud_mod.UPLOAD_ROOT

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
move_money(db, db.query(User).filter(User.username == "buyer").first().id, 2000, "admin", "seed"); db.commit(); db.close()
bal = lambda c: c.get("/wallet").json()["balance"]

print("── ลงสินค้า ──")
img = sam.post("/shop/images", files={"file": ("a.png", io.BytesIO(b"\x89PNG\r\n\x1a\nxx"), "image/png")}).json()["url"]
check("อัปโหลดรูปสินค้า", sam.get(img).status_code == 200)
check("ไฟล์ไม่ใช่รูป → 400", sam.post("/shop/images", files={"file": ("a.exe", b"MZ")}).status_code == 400)
p1 = sam.post("/shop/my/products", json={"name": "เสื้อยืด", "price": 300, "stock": 5, "image_url": img}).json()
p2 = kim.post("/shop/my/products", json={"name": "หมวก", "price": 200, "stock": 2}).json()
check("ลิงก์รูป javascript: ถูกปฏิเสธ", kim.post("/shop/my/products", json={"name": "x", "price": 1, "stock": 1, "image_url": "javascript:alert(1)"}).status_code == 400)
check("สินค้าขึ้นหน้าร้านพร้อมชื่อร้าน", {p["seller"] for p in buyer.get("/shop/products").json()["products"]} == {"Sam", "Kim"})
check("แก้สินค้าคนอื่นไม่ได้", kim.put(f"/shop/my/products/{p1['id']}", json={"name": "x", "price": 1, "stock": 1}).status_code == 404)
check("ซื้อของร้านตัวเองไม่ได้", sam.post("/shop/orders", json={"items": [{"product_id": p1["id"], "qty": 1}], "address": "ที่อยู่ทดสอบ"}).status_code == 400)

print("── สั่งซื้อหลายร้าน ──")
r = buyer.post("/shop/orders", json={"items": [{"product_id": p1["id"], "qty": 2}, {"product_id": p2["id"], "qty": 1}], "address": "99 ถนนทดสอบ"}).json()
check("แยกเป็น 2 ออเดอร์ + หักเงิน 800", len(r["orders"]) == 2 and bal(buyer) == 1200)
check("ผู้ขายยังไม่ได้เงิน (พักไว้)", bal(sam) == 0 and bal(kim) == 0)
sales = sam.get("/shop/my/sales").json()["orders"]
check("sam เห็นเฉพาะออเดอร์ร้านตัวเอง", len(sales) == 1 and sales[0]["items"][0]["name"] == "เสื้อยืด")
oid_sam = sales[0]["id"]; oid_kim = kim.get("/shop/my/sales").json()["orders"][0]["id"]

print("── จัดส่ง + ปล่อยเงิน ──")
check("kim จัดการออเดอร์ของ sam ไม่ได้", kim.post(f"/logistics/orders/{oid_sam}/status", json={"status": "packed"}).status_code == 403)
sam.post(f"/logistics/orders/{oid_sam}/status", json={"status": "packed"})
sam.post(f"/logistics/orders/{oid_sam}/status", json={"status": "shipped", "tracking": "TH999"})
check("ผู้ขายกด 'ได้รับแล้ว' เองไม่ได้", sam.post(f"/logistics/orders/{oid_sam}/status", json={"status": "delivered"}).status_code == 400)
check("คนอื่นกดได้รับแทนผู้ซื้อไม่ได้", kim.post(f"/logistics/orders/{oid_sam}/received").status_code == 404)
buyer.post(f"/logistics/orders/{oid_sam}/received")
check("ผู้ซื้อกดได้รับ → sam ได้ 600", bal(sam) == 600)
check("กดซ้ำไม่ได้เงินซ้ำ", buyer.post(f"/logistics/orders/{oid_sam}/received").status_code == 400 and bal(sam) == 600)
kim.post(f"/logistics/orders/{oid_kim}/status", json={"status": "cancelled"})
check("ผู้ขายยกเลิก → คืนเงินผู้ซื้อ + คืนสต็อก", bal(buyer) == 1400 and kim.get("/shop/my/products").json()["products"][0]["stock"] == 2 and bal(kim) == 0)

print("── สินค้าแพลตฟอร์ม (ผู้ดูแล) ยังใช้ได้ ──")
pp = boss.post("/manage/api/products", json={"name": "ของแพลตฟอร์ม", "price": 100, "stock": 3}).json()
o = buyer.post("/shop/orders", json={"items": [{"product_id": pp["id"], "qty": 1}], "address": "99 ถนนทดสอบ"}).json()
boss.post(f"/logistics/orders/{o['id']}/status", json={"status": "packed"})
boss.post(f"/logistics/orders/{o['id']}/status", json={"status": "shipped"})
check("ผู้ดูแลกดได้รับแล้วได้", boss.post(f"/logistics/orders/{o['id']}/status", json={"status": "delivered"}).status_code == 200)

os.remove(db_file)
print(f"\n✅ ผ่านทั้งหมด {n} ข้อ")
