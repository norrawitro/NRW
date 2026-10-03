"""ทดสอบรูปแบบเดียวกัน (แนบรูปได้ทุกระบบ), ตลาดซื้อขายโทเคน, ประกาศซื้อ

    python tests/smoke_unified.py
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
from app.database import SessionLocal
from app.models.user import User
from app.services.wallet_ops import move_money, move_tokens

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

boss, ann, bob = (client_for(u) for u in ("boss", "ann", "bob"))
db = SessionLocal(); db.query(User).filter(User.username == "boss").update({"is_admin": True})
uid = {u.username: u.id for u in db.query(User).all()}
for u in ("ann", "bob"):
    move_money(db, uid[u], 1000, "admin", "seed")
move_tokens(db, uid["ann"], 100, "admin", "seed"); db.commit(); db.close()
bal = lambda c: c.get("/wallet").json()["balance"]
tok = lambda c: c.get("/token").json()["token"]

def approve_all():
    for it in boss.get("/manage/api/moderation").json()["items"]:
        boss.post(f"/manage/api/moderation/{it['id']}/approve", json={})

print("── อัปโหลดรูป + แนบรูป ──")
img = ann.post("/media/images", files={"file": ("a.png", io.BytesIO(b"\x89PNG\r\n\x1a\nxx"), "image/png")}).json()["url"]
check("อัปโหลดรูปได้ url /media/images/", img.startswith("/media/images/") and ann.get(img).status_code == 200)
check("ไฟล์ไม่ใช่รูป → 400", ann.post("/media/images", files={"file": ("a.exe", b"MZ")}).status_code == 400)
check("ไม่ login อัปโหลดไม่ได้", TestClient(app).post("/media/images", files={"file": ("a.png", b"x", "image/png")}).status_code == 401)
check("ลิงก์ javascript: ถูกปฏิเสธ", ann.post("/market/listings", json={"kind": "sale", "title": "x1", "price": 1, "images": ["javascript:alert(1)"]}).status_code == 400)
check("เกิน 5 รูป → 422", ann.post("/market/listings", json={"kind": "sale", "title": "x1", "price": 1, "images": [img] * 6}).status_code == 422)
l = ann.post("/market/listings", json={"kind": "rent", "title": "กล้องให้เช่า", "price": 50, "images": [img, img]}).json()
check("มือสอง/เช่า มีรูป", l["images"] == [img, img])
ev = boss.post("/events", json={"title": "สัมมนา", "description": "", "place": "ออนไลน์", "starts_at": "2030-01-01T10:00", "price": 0, "capacity": 10, "images": [img]})
check("กิจกรรมแนบรูปได้", ev.status_code == 200 and bob.get("/events").json()["events"][0]["images"] == [img])
approve_all()
pr = ann.post("/shop/my/products", json={"name": "เสื้อ", "price": 250, "stock": 3, "images": [img, img]})
check("สินค้าใช้รูปจาก /media ได้ (รูปแรก = รูปปก)", pr.status_code == 200 and ann.get("/shop/my/products").json()["products"][0]["image_url"] == img)
check("ประกาศที่อนุมัติแล้วแสดงพร้อมรูป", bob.get("/market/listings").json()["listings"][0]["images"] == [img, img])

print("── ตลาดโทเคน ──")
s = ann.post("/token/offers", json={"side": "sell", "amount": 40, "price": 2.5}).json()
check("ประกาศขาย → พักโทเคน", tok(ann) == 60 and s["remaining"] == 40)
check("ขายเกินที่มี → 400", ann.post("/token/offers", json={"side": "sell", "amount": 1000, "price": 1}).status_code == 400)
check("รับประกาศตัวเองไม่ได้", ann.post(f"/token/offers/{s['id']}/take", json={"amount": 1}).status_code == 400)
r = bob.post(f"/token/offers/{s['id']}/take", json={"amount": 10}).json()
check("bob ซื้อ 10 → จ่าย 25 ได้ 10 โทเคน", r["total"] == 25 and bal(bob) == 975 and tok(bob) == 10 and bal(ann) == 1025)
check("รับเกินที่เหลือ → 400", bob.post(f"/token/offers/{s['id']}/take", json={"amount": 31}).status_code == 400)
ann.post(f"/token/offers/{s['id']}/cancel")
check("ยกเลิก → คืนโทเคนที่เหลือ 30", tok(ann) == 90)
b = bob.post("/token/offers", json={"side": "buy", "amount": 20, "price": 3}).json()
check("ประกาศซื้อ → พักเงิน 60", bal(bob) == 915)
check("ประกาศซื้ออยู่ในสมุด", any(o["id"] == b["id"] for o in ann.get("/token/offers").json()["buy"]))
ann.post(f"/token/offers/{b['id']}/take", json={"amount": 20})
check("ann ขายให้ครบ → ได้ 60, bob ได้ 20 โทเคน, ปิดประกาศ",
      bal(ann) == 1085 and tok(bob) == 30 and tok(ann) == 70 and not ann.get("/token/offers").json()["buy"])
b2 = bob.post("/token/offers", json={"side": "buy", "amount": 10, "price": 1}).json()
bob.post(f"/token/offers/{b2['id']}/cancel")
check("ยกเลิกประกาศซื้อ → คืนเงิน", bal(bob) == 915)
check("ยกเลิกซ้ำไม่ได้", bob.post(f"/token/offers/{b2['id']}/cancel").status_code == 404)

print("── ประกาศซื้อ ──")
w = bob.post("/wanted/posts", json={"title": "หาซื้อจักรยาน", "description": "มือสองสภาพดี", "budget": 500, "images": [img]}).json()
check("ลงประกาศซื้อ → รออนุมัติ", w["mod_status"] == "pending" and w["images"] == [img])
check("ยังไม่อนุมัติ คนอื่นไม่เห็น", not ann.get("/wanted/posts").json()["posts"])
check("ยังไม่อนุมัติ ยื่นข้อเสนอไม่ได้", ann.post(f"/wanted/posts/{w['id']}/offers", json={"price": 400}).status_code == 404)
check("เจ้าของเห็นในประกาศของฉัน", bob.get("/wanted/posts?mine=true").json()["posts"][0]["mod"]["status"] == "pending")
check("คิวผู้ดูแลมีประกาศซื้อ + รูป", any(i["kind"] == "wanted" and i.get("image") == img for i in boss.get("/manage/api/moderation").json()["items"]))
approve_all()
check("อนุมัติแล้วแสดงต่อสาธารณะ", ann.get("/wanted/posts").json()["posts"][0]["title"] == "หาซื้อจักรยาน")
check("ยื่นข้อเสนอให้ตัวเองไม่ได้", bob.post(f"/wanted/posts/{w['id']}/offers", json={"price": 1}).status_code == 400)
o1 = ann.post(f"/wanted/posts/{w['id']}/offers", json={"message": "มีคันนึง", "price": 450, "images": [img]}).json()
o2 = boss.post(f"/wanted/posts/{w['id']}/offers", json={"message": "ของใหม่", "price": 480}).json()
check("ann เห็นเฉพาะข้อเสนอตัวเอง", len(ann.get(f"/wanted/posts/{w['id']}/offers").json()["offers"]) == 1)
offs = bob.get(f"/wanted/posts/{w['id']}/offers").json()
check("เจ้าของเห็นทุกข้อเสนอ เรียงราคาถูกก่อน", offs["is_owner"] and [o["price"] for o in offs["offers"]] == [450, 480])
check("คนอื่นรับข้อเสนอแทนไม่ได้", ann.post(f"/wanted/offers/{o1['id']}/accept").status_code == 404)
bob.post(f"/wanted/offers/{o1['id']}/accept")
check("รับข้อเสนอ → จ่าย 450 ให้ ann", bal(bob) == 465 and bal(ann) == 1535)
st = {o["id"]: o["status"] for o in bob.get(f"/wanted/posts/{w['id']}/offers").json()["offers"]}
check("ข้อเสนออื่นถูกปฏิเสธอัตโนมัติ + ประกาศปิด", st == {o1["id"]: "accepted", o2["id"]: "declined"}
      and not ann.get("/wanted/posts").json()["posts"])
check("รับซ้ำไม่ได้", bob.post(f"/wanted/offers/{o2['id']}/accept").status_code == 400 and bal(bob) == 465)
w2 = bob.post("/wanted/posts", json={"title": "หาซื้อทีวี", "budget": 9000}).json(); approve_all()
o3 = ann.post(f"/wanted/posts/{w2['id']}/offers", json={"price": 8000}).json()
check("เงินไม่พอรับข้อเสนอ → 400", bob.post(f"/wanted/offers/{o3['id']}/accept").status_code == 400 and bal(bob) == 465)
bob.post(f"/wanted/posts/{w2['id']}/close")
check("ปิดประกาศ → ยื่นเพิ่มไม่ได้", ann.post(f"/wanted/posts/{w2['id']}/offers", json={"price": 1}).status_code == 404)

os.remove(db_file)
print(f"\n✅ ผ่านทั้งหมด {n} ข้อ")
