"""ทดสอบช่วงที่ 1–2 แบบไม่แตะฐานข้อมูลจริง (ใช้ SQLite ชั่วคราว)

    python tests/smoke_phase2.py
"""
import os, sys, tempfile
db_file = tempfile.mktemp(suffix=".db")
os.environ["DATABASE_URL"] = f"sqlite:///{db_file}"
os.environ.setdefault("SECRET_KEY", "test")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app.models.user import User

ok_count = 0
def check(name, cond, extra=""):
    global ok_count
    if not cond:
        raise SystemExit(f"❌ {name} {extra}")
    ok_count += 1
    print(f"  ✅ {name}")

def client_for(username):
    c = TestClient(app)
    c.post("/members/register", data=dict(full_name=username.title(), username=username,
           email=f"{username}@test.local", phone="", password="password123", confirm="password123"))
    r = c.post("/members/login", data=dict(username=username, password="password123"), follow_redirects=False)
    c.cookies.set("nrw_token", r.cookies["nrw_token"])
    return c

boss, alice, bob = client_for("boss"), client_for("alice"), client_for("bob")
db = SessionLocal(); db.query(User).filter(User.username == "boss").update({"is_admin": True}); db.commit(); db.close()

print("── สมาชิก / ผู้ดูแล ──")
check("/members/me", alice.get("/members/me").json()["username"] == "alice")
check("แก้เบอร์โทร", alice.patch("/members/me", json={"phone": "0811111111"}).status_code == 200)
check("รหัสผ่านเดิมผิด → 400", alice.post("/members/me/password", json={"current": "x", "new": "newpass123"}).status_code == 400)
check("คนทั่วไปเข้า /manage ไม่ได้", alice.get("/manage/api/users").status_code == 403)
check("admin เข้า /manage ได้", boss.get("/manage/api/users").status_code == 200)

print("── กระเป๋าเงิน (ต้องอนุมัติ) ──")
r = alice.post("/wallet/tx", json={"type": "topup", "amount": 1000, "desc": "slip A1"}).json()
check("เติมเงิน = คำขอรออนุมัติ", r["pending"] and alice.get("/wallet").json()["balance"] == 0)
check("อนุมัติแล้วยอดเพิ่ม", boss.post(f"/manage/api/wallet-requests/{r['request']['id']}/approve").status_code == 200
      and alice.get("/wallet").json()["balance"] == 1000)
check("อนุมัติซ้ำไม่ได้", boss.post(f"/manage/api/wallet-requests/{r['request']['id']}/approve").status_code == 400)
w = alice.post("/wallet/tx", json={"type": "withdraw", "amount": 200}).json()
check("ถอน = กันยอดทันที", alice.get("/wallet").json()["balance"] == 800)
boss.post(f"/manage/api/wallet-requests/{w['request']['id']}/reject")
check("ปฏิเสธถอน = คืนยอด", alice.get("/wallet").json()["balance"] == 1000)
check("ถอนเกินยอด → 400", alice.post("/wallet/tx", json={"type": "withdraw", "amount": 99999}).status_code == 400)

print("── ขายออนไลน์ + คลัง/ขนส่ง ──")
p = boss.post("/manage/api/products", json={"name": "เสื้อ", "price": 250, "stock": 3}).json()
check("admin เพิ่มสินค้า", p["id"] > 0 and len(alice.get("/shop/products").json()["products"]) == 1)
check("สั่งเกินสต็อก → 400", alice.post("/shop/orders", json={"items": [{"product_id": p["id"], "qty": 9}], "address": "123 ถนนทดสอบ"}).status_code == 400)
o = alice.post("/shop/orders", json={"items": [{"product_id": p["id"], "qty": 2}], "address": "123 ถนนทดสอบ"}).json()
check("สั่งซื้อ: หักเงิน 500 + ได้ 5 โทเคน", alice.get("/wallet").json()["balance"] == 500 and o["tokens_earned"] == 5)
check("สต็อกเหลือ 1", boss.get("/logistics/inventory").json()["products"][0]["stock"] == 1)
check("bob สั่งเงินไม่พอ → 400", bob.post("/shop/orders", json={"items": [{"product_id": p["id"], "qty": 1}], "address": "456 ถนนทดสอบ"}).status_code == 400)
check("สต็อกไม่ลดเมื่อซื้อไม่สำเร็จ", boss.get("/logistics/inventory").json()["products"][0]["stock"] == 1)
check("ข้ามขั้น paid→delivered ไม่ได้", boss.post(f"/logistics/orders/{o['id']}/status", json={"status": "delivered"}).status_code == 400)
boss.post(f"/logistics/orders/{o['id']}/status", json={"status": "packed"})
t = boss.post(f"/logistics/orders/{o['id']}/status", json={"status": "shipped", "tracking": "TH123"}).json()
check("เส้นทางพัสดุ 3 จุด + เลขพัสดุ", len(t["timeline"]) == 3 and t["tracking"] == "TH123")
check("เจ้าของดูเส้นทางได้", alice.get(f"/logistics/orders/{o['id']}").status_code == 200)
check("คนอื่นดูไม่ได้", bob.get(f"/logistics/orders/{o['id']}").status_code == 404)
o2 = alice.post("/shop/orders", json={"items": [{"product_id": p["id"], "qty": 1}], "address": "123 ถนนทดสอบ"}).json()
boss.post(f"/logistics/orders/{o2['id']}/status", json={"status": "cancelled"})
check("ยกเลิก = คืนเงิน + คืนสต็อก + ดึงโทเคนคืน", alice.get("/wallet").json()["balance"] == 500
      and boss.get("/logistics/inventory").json()["products"][0]["stock"] == 1
      and alice.get("/token").json()["token"] == 5)

print("── มือสอง/เช่า ──")
l = bob.post("/market/listings", json={"kind": "rent", "title": "กล้อง", "price": 100}).json()
check("ซื้อ/เช่าของตัวเองไม่ได้", bob.post(f"/market/listings/{l['id']}/deal", json={"days": 1}).status_code == 400)
d = alice.post(f"/market/listings/{l['id']}/deal", json={"days": 3}).json()
check("เช่า 3 วัน: alice -300, bob +300", d["total"] == 300 and alice.get("/wallet").json()["balance"] == 200
      and bob.get("/wallet").json()["balance"] == 300)
check("ของถูกเช่าแล้ว ไม่โชว์ในตลาด", all(x["id"] != l["id"] for x in alice.get("/market/listings").json()["listings"]))
bob.post(f"/market/deals/{d['deal_id']}/return")
check("คืนของแล้วเปิดให้เช่าอีก", any(x["id"] == l["id"] for x in alice.get("/market/listings").json()["listings"]))

print("── โทเคน ──")
check("โอน 3 โทเคนให้ bob", alice.post("/token/transfer", json={"to_username": "bob", "amount": 3}).status_code == 200
      and bob.get("/token").json()["token"] == 3)
check("โอนเกินที่มี → 400", alice.post("/token/transfer", json={"to_username": "bob", "amount": 999}).status_code == 400)
boss.post("/manage/api/users/2/adjust", json={"token": 18})   # alice: 5 - 3 + 18 = 20
r = alice.post("/token/redeem", json={"amount": 20}).json()
check("แลก 20 โทเคน = ฿2", r["balance"] == 202 and r["token"] == 0)

print("── วิเคราะห์ ──")
check("สรุปของฉัน", alice.get("/analytics/me").json()["orders"] == 2)
a = boss.get("/analytics/admin").json()
check("ภาพรวมผู้ดูแล", a["sales"] == 500 and a["top_products"][0]["qty"] == 2)
check("คนทั่วไปดูภาพรวมไม่ได้", alice.get("/analytics/admin").status_code == 403)

os.remove(db_file)
print(f"\n✅ ผ่านทั้งหมด {ok_count} ข้อ")
