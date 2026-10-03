"""ทดสอบระบบอนุมัติเนื้อหา (ผู้ดูแลกดอนุมัติก่อนเนื้อหาของสมาชิกจะแสดง)

    python tests/smoke_moderation.py
"""
import io, os, sys, tempfile
from datetime import datetime, timedelta, timezone
db_file = tempfile.mktemp(suffix=".db")
os.environ["DATABASE_URL"] = f"sqlite:///{db_file}"
os.environ.setdefault("SECRET_KEY", "test")
os.environ["MODERATION"] = "on"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import app.routers.cloud as cloud_mod
cloud_mod.UPLOAD_ROOT = tempfile.mkdtemp()
import app.routers.health as health_mod, app.routers.video as video_mod
health_mod.UPLOAD_ROOT = video_mod.UPLOAD_ROOT = cloud_mod.UPLOAD_ROOT

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

boss, sam, viewer = client_for("boss"), client_for("sam"), client_for("viewer")
db = SessionLocal(); db.query(User).filter(User.username == "boss").update({"is_admin": True})
for u in ("sam", "viewer"):
    move_money(db, db.query(User).filter(User.username == u).first().id, 1000, "admin", "seed")
db.commit(); db.close()
queue = lambda: boss.get("/manage/api/moderation").json()["items"]
def approve(kind):
    m = next(i for i in queue() if i["kind"] == kind)
    return boss.post(f"/manage/api/moderation/{m['id']}/approve", json={}).status_code == 200
def reject(kind, why="ไม่เหมาะสม"):
    m = next(i for i in queue() if i["kind"] == kind)
    return boss.post(f"/manage/api/moderation/{m['id']}/reject", json={"reason": why}).status_code == 200

print("── โพสต์ข่าว ──")
sam.post("/news/posts", json={"text": "โปรโมชั่นร้านใหม่", "cat": "announce"})
check("ยังไม่อนุมัติ: คนอื่นไม่เห็น", viewer.get("/news/posts").json()["posts"] == [])
check("เจ้าของเห็น + ป้ายรออนุมัติ", sam.get("/news/posts").json()["posts"][0]["mod"]["status"] == "pending")
check("ผู้ดูแลเห็นในคิว", queue()[0]["kind"] == "post" and queue()[0]["title"] == "โปรโมชั่นร้านใหม่")
check("คนทั่วไปเข้าคิวไม่ได้", sam.get("/manage/api/moderation").status_code == 403)
check("ปฏิเสธต้องมีเหตุผล", boss.post(f"/manage/api/moderation/{queue()[0]['id']}/reject", json={}).status_code == 400)
approve("post")
check("อนุมัติแล้วทุกคนเห็น", len(viewer.get("/news/posts").json()["posts"]) == 1)
boss.post("/news/posts", json={"text": "ประกาศจากแอดมิน", "cat": "announce"})
check("โพสต์ของผู้ดูแลแสดงทันที", len(viewer.get("/news/posts").json()["posts"]) == 2)

print("── สินค้า ──")
p = sam.post("/shop/my/products", json={"name": "กระเป๋า", "price": 100, "stock": 5}).json()
check("สินค้ายังไม่ขึ้นหน้าร้าน", viewer.get("/shop/products").json()["products"] == [])
check("สั่งซื้อสินค้ารออนุมัติไม่ได้", viewer.post("/shop/orders", json={"items": [{"product_id": p["id"], "qty": 1}], "address": "ที่อยู่ทดสอบ"}).status_code == 404)
approve("product")
check("อนุมัติแล้วขึ้นหน้าร้าน", len(viewer.get("/shop/products").json()["products"]) == 1)
sam.put(f"/shop/my/products/{p['id']}", json={"name": "ของต้องห้าม", "price": 100, "stock": 5})
check("แก้ไขแล้วต้องอนุมัติใหม่", viewer.get("/shop/products").json()["products"] == [])
reject("product", "สินค้าผิดกฎ")
check("เจ้าของเห็นเหตุผลที่ไม่อนุมัติ", sam.get("/shop/my/products").json()["products"][0]["mod"]["reason"] == "สินค้าผิดกฎ")

print("── ระบบอื่น ──")
sam.post("/market/listings", json={"kind": "sale", "title": "จักรยาน", "price": 500})
check("มือสอง: ซ่อนจนอนุมัติ", viewer.get("/market/listings").json()["listings"] == [])
approve("listing"); check("มือสอง: อนุมัติแล้วเห็น", len(viewer.get("/market/listings").json()["listings"]) == 1)
cid = sam.post("/course", json={"title": "คอร์สทดสอบ", "price": 0}).json()["id"]
check("คอร์ส: ลงทะเบียนไม่ได้จนอนุมัติ", viewer.post(f"/course/{cid}/enroll").status_code == 404)
approve("course"); check("คอร์ส: อนุมัติแล้วลงทะเบียนได้", viewer.post(f"/course/{cid}/enroll").status_code == 200)
sam.post("/jobs", json={"title": "จ้างทำเว็บ", "budget": 100})
check("งาน: ซ่อนจนอนุมัติ", viewer.get("/jobs").json()["jobs"] == [])
approve("job"); check("งาน: อนุมัติแล้วเห็น", len(viewer.get("/jobs").json()["jobs"]) == 1)
sam.post("/ads", json={"title": "โฆษณาสแปม", "days": 2})
check("โฆษณา: ยังไม่ขึ้นหน้าแรก", viewer.get("/ads/serve").json()["ad"] is None)
reject("ad", "สแปม")
check("โฆษณา: ไม่อนุมัติ = คืนเงิน ฿40", sam.get("/wallet").json()["balance"] == 1000)
vid = sam.post("/video", data={"title": "คลิป"}, files={"file": ("a.mp4", io.BytesIO(b"\x00\x00\x00\x18ftyp"), "video/mp4")}).json()["id"]
check("วิดีโอ: คนอื่นเปิดไฟล์ไม่ได้จนอนุมัติ", viewer.get(f"/video/{vid}/file").status_code == 404 and sam.get(f"/video/{vid}/file").status_code == 200)
approve("video"); check("วิดีโอ: อนุมัติแล้วดูได้", viewer.get(f"/video/{vid}/file").status_code == 200)
eid = sam.post("/events", json={"title": "งานสัมมนา", "starts_at": (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()}).json()["id"]
check("กิจกรรม: ซื้อตั๋วไม่ได้จนอนุมัติ", viewer.post(f"/events/{eid}/tickets").status_code == 404)
approve("event"); check("กิจกรรม: อนุมัติแล้วซื้อได้", viewer.post(f"/events/{eid}/tickets").status_code == 200)
page = sam.post("/creator", json={"bio": "x", "monthly_price": 10}).json()["id"]
sam.post("/creator/me/posts", json={"title": "โพสต์ฟรี", "body": "สวัสดี", "vip_only": False})
check("โพสต์ครีเอเตอร์: ซ่อนจนอนุมัติ", viewer.get(f"/creator/{page}/posts").json()["posts"] == [])
approve("creator_post"); check("โพสต์ครีเอเตอร์: อนุมัติแล้วเห็น", len(viewer.get(f"/creator/{page}/posts").json()["posts"]) == 1)

print("── หลักฐานออกกำลังกาย ──")
pic = lambda: {"file": ("run.jpg", io.BytesIO(b"\xff\xd8\xff jpg"), "image/jpeg")}
r = sam.post("/health", data={"activity": "วิ่ง", "minutes": "60"}, files=pic()).json()
check("ส่งแล้วรออนุมัติ ยังไม่ได้โทเคน", r["status"] == "pending" and sam.get("/token").json()["token"] == 0)
check("ผู้ดูแลเห็นรูปหลักฐาน", boss.get(f"/health/evidence/{r['id']}").status_code == 200)
check("คนอื่นดูรูปหลักฐานไม่ได้", viewer.get(f"/health/evidence/{r['id']}").status_code == 404)
approve("health")
check("อนุมัติแล้วได้ 2 โทเคน", sam.get("/token").json()["token"] == 2)
r2 = sam.post("/health", data={"activity": "เดิน", "minutes": "60"}, files=pic()).json()
reject("health", "รูปไม่ชัด")
check("ไม่อนุมัติ = ไม่ได้โทเคน + เห็นเหตุผล", sam.get("/token").json()["token"] == 2
      and next(l for l in sam.get("/health").json()["logs"] if l["id"] == r2["id"])["reason"] == "รูปไม่ชัด")
check("แดชบอร์ดผู้ดูแลนับคิว", boss.get("/analytics/admin").json()["pending_content"] == 0)

os.remove(db_file)
print(f"\n✅ ผ่านทั้งหมด {n} ข้อ")
