"""ทดสอบช่วงที่ 3–4 แบบไม่แตะฐานข้อมูลจริง (SQLite + โฟลเดอร์อัปโหลดชั่วคราว)

    python tests/smoke_phase34.py
"""
import io, os, sys, tempfile
from datetime import datetime, timedelta, timezone
db_file = tempfile.mktemp(suffix=".db")
os.environ["DATABASE_URL"] = f"sqlite:///{db_file}"
os.environ.setdefault("SECRET_KEY", "test")
os.environ["MODERATION"] = "off"          # ทดสอบระบบซื้อขาย — การอนุมัติทดสอบใน smoke_moderation.py
os.environ["OLLAMA_URL"] = "http://127.0.0.1:9"          # ไม่มี AI → ต้องได้คำแนะนำพื้นฐาน
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app.routers.cloud as cloud_mod
cloud_mod.UPLOAD_ROOT = tempfile.mkdtemp()
import app.routers.video as video_mod
video_mod.UPLOAD_ROOT = cloud_mod.UPLOAD_ROOT

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

boss, alice, bob = client_for("boss"), client_for("alice"), client_for("bob")
db = SessionLocal(); db.query(User).filter(User.username == "boss").update({"is_admin": True})
for name in ("alice", "bob"):
    move_money(db, db.query(User).filter(User.username == name).first().id, 1000, "admin", "seed")
db.commit(); db.close()
bal = lambda c: c.get("/wallet").json()["balance"]
tok = lambda c: c.get("/token").json()["token"]

print("── แชท ──")
alice.post("/chat/messages", json={"room": "general", "text": "สวัสดีทุกคน"})
check("ห้องรวม bob เห็น", bob.get("/chat/messages?room=general").json()["messages"][0]["text"] == "สวัสดีทุกคน")
alice.post("/chat/messages", json={"room": "dm:bob", "text": "ลับ"})
check("DM ถึง bob", bob.get("/chat/messages?room=dm:alice").json()["messages"][0]["text"] == "ลับ")
check("DM ไม่โผล่ห้องรวม", len(boss.get("/chat/messages?room=general").json()["messages"]) == 1)
check("ห้อง DM อยู่ในรายการ", any(r["room"] == "dm:alice" for r in bob.get("/chat/rooms").json()["rooms"]))
check("ดึงเฉพาะข้อความใหม่ (after)", bob.get("/chat/messages?room=general&after=999").json()["messages"] == [])

print("── คอร์สเรียน ──")
cid = bob.post("/course", json={"title": "Python พื้นฐาน", "price": 200}).json()["id"]
bob.post(f"/course/{cid}/lessons", json={"title": "บทที่ 1", "content": "print('hi')"})
bob.post(f"/course/{cid}/lessons", json={"title": "บทที่ 2 แบบทดสอบ", "content": "Python ใช้ฟังก์ชันอะไรพิมพ์ข้อความ", "questions": [
    {"kind": "choice", "prompt": "ฟังก์ชันพิมพ์ข้อความ?", "choices": ["echo", "print", "say"], "answer": "1", "explanation": "ใช้ print()"},
    {"kind": "text", "prompt": "พิมพ์ชื่อภาษาที่เรียน", "answer": "python|ไพธอน"}]})
check("ปรนัยต้องมีตัวเลือก ≥2", bob.post(f"/course/{cid}/lessons", json={"title": "x", "questions": [{"kind": "choice", "prompt": "?", "choices": ["a"], "answer": "0"}]}).status_code == 400)
check("ยังไม่ลงทะเบียน = ไม่เห็นเนื้อหา", "content" not in alice.get(f"/course/{cid}").json()["lessons"][0])
alice.post(f"/course/{cid}/enroll")
check("ลงทะเบียน: alice -200, bob +200", bal(alice) == 800 and bal(bob) == 1200)
c = alice.get(f"/course/{cid}").json()
check("ลงทะเบียนแล้วเห็นเนื้อหา", c["lessons"][0]["content"] == "print('hi')")
check("ผู้เรียนไม่เห็นเฉลย", "answer" not in c["lessons"][1]["questions"][0])
check("ผู้สอนเห็นเฉลย", bob.get(f"/course/{cid}").json()["lessons"][1]["questions"][0]["answer"] == "1")
alice.post(f"/course/{cid}/lessons/{c['lessons'][0]['id']}/done")
l2, q1, q2 = c["lessons"][1]["id"], c["lessons"][1]["questions"][0]["id"], c["lessons"][1]["questions"][1]["id"]
check("บทมีคำถาม กดจบเองไม่ได้", alice.post(f"/course/{cid}/lessons/{l2}/done").status_code == 400)
ans = lambda q, a: alice.post(f"/course/{cid}/lessons/{l2}/questions/{q}/answer", json={"answer": a}).json()
check("ปรนัยตอบผิด", ans(q1, "0")["correct"] is False)
r = ans(q1, "1"); check("ปรนัยตอบถูก + คำอธิบาย", r["correct"] and r["explanation"] == "ใช้ print()" and not r["lesson_done"])
check("อัตนัย: ไม่สนตัวพิมพ์/ช่องว่าง", ans(q2, "  PYTHON ")["lesson_done"] is True)
check("ความคืบหน้า 2/2", alice.get(f"/course/{cid}").json()["progress"] == "2/2")
check("ลงซ้ำไม่ได้", alice.post(f"/course/{cid}/enroll").status_code == 400)

print("── ตลาดงาน (พักเงิน) ──")
jid = alice.post("/jobs", json={"title": "ทำโลโก้ร้าน", "budget": 300}).json()["id"]
bob.post(f"/jobs/{jid}/proposals", json={"message": "ทำได้ภายใน 3 วัน"})
pid = alice.get("/jobs?scope=mine").json()["jobs"][0]["proposals"][0]["id"]
alice.post(f"/jobs/{jid}/hire/{pid}")
check("จ้างแล้วเงินถูกพัก (alice 500)", bal(alice) == 500 and bal(bob) == 1200)
alice.post(f"/jobs/{jid}/complete")
check("งานเสร็จ: bob ได้ 300", bal(bob) == 1500)
jid2 = alice.post("/jobs", json={"title": "แปลเอกสาร", "budget": 100}).json()["id"]
bob.post(f"/jobs/{jid2}/proposals", json={"message": "รับงานครับ"})
alice.post(f"/jobs/{jid2}/hire/" + str(alice.get("/jobs?scope=mine").json()["jobs"][0]["proposals"][0]["id"]))
alice.post(f"/jobs/{jid2}/cancel")
check("ยกเลิกหลังจ้าง = คืนเงิน", bal(alice) == 500)
check("คนอื่นกดเสร็จแทนไม่ได้", bob.post(f"/jobs/{jid}/complete").status_code == 403)

print("── พื้นที่ทำงาน ──")
wid = alice.post("/workspace", json={"name": "ทีมร้าน"}).json()["id"]
check("คนนอกเข้าไม่ได้", bob.get(f"/workspace/{wid}").status_code == 404)
alice.post(f"/workspace/{wid}/members", json={"username": "bob"})
bob.post(f"/workspace/{wid}/tasks", json={"title": "ถ่ายรูปสินค้า"})
tid = alice.get(f"/workspace/{wid}").json()["tasks"][0]["id"]
bob.post(f"/workspace/{wid}/tasks/{tid}", json={"status": "done"})
alice.put(f"/workspace/{wid}/notes", json={"notes": "ประชุมวันจันทร์"})
w = alice.get(f"/workspace/{wid}").json()
check("เชิญ + งาน + โน้ต", len(w["members"]) == 2 and w["tasks"][0]["status"] == "done" and w["notes"] == "ประชุมวันจันทร์")

print("── โฆษณา ──")
check("ลิงก์ javascript: ถูกปฏิเสธ", bob.post("/ads", json={"title": "xx", "link": "javascript:alert(1)", "days": 1}).status_code == 400)
ad = bob.post("/ads", json={"title": "ร้านกาแฟ", "text": "ลด 20%", "link": "https://example.com", "days": 3}).json()
check("ซื้อโฆษณา 3 วัน = ฿60", bal(bob) == 1440 and ad["running"])
check("หน้าแรกได้โฆษณา", alice.get("/ads/serve").json()["ad"]["title"] == "ร้านกาแฟ")
check("คลิกแล้ว redirect", alice.get(f"/ads/{ad['id']}/go", follow_redirects=False).headers["location"] == "https://example.com")
boss.post(f"/ads/{ad['id']}/toggle")
check("ผู้ดูแลปิดแล้วไม่แสดง", alice.get("/ads/serve").json()["ad"] is None)

print("── วิดีโอ ──")
check("ไฟล์ผิดชนิด → 400", bob.post("/video", data={"title": "x"}, files={"file": ("a.exe", b"MZ")}).status_code == 400)
vid = bob.post("/video", data={"title": "สอนทำกาแฟ"}, files={"file": ("a.mp4", io.BytesIO(b"\x00\x00\x00\x18ftypmp42"), "video/mp4")}).json()["id"]
check("ดูวิดีโอได้", alice.get(f"/video/{vid}/file").content.startswith(b"\x00\x00\x00\x18ftyp"))
alice.post(f"/video/{vid}/view")
check("นับยอดวิว", alice.get("/video").json()["videos"][0]["views"] == 1)
check("คนอื่นลบไม่ได้", alice.delete(f"/video/{vid}").status_code == 403)

print("── เกม ──")
t0 = tok(alice)
for _ in range(6):
    alice.post("/games/score", json={"game": "memory", "score": 500})
check("ได้โทเคนสูงสุด 5 ต่อวัน", tok(alice) - t0 == 5)
check("คะแนนเกินจริง → 400", alice.post("/games/score", json={"game": "memory", "score": 99999}).status_code == 400)
check("ตารางอันดับ", alice.get("/games/leaderboard?game=memory").json()["top"][0]["score"] == 500)

print("── กิจกรรม/ตั๋ว ──")
when = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
eid = bob.post("/events", json={"title": "สัมมนาการตลาด", "starts_at": when, "price": 100, "capacity": 1}).json()["id"]
code = alice.post(f"/events/{eid}/tickets").json()["code"]
check("ซื้อตั๋ว: alice -100, bob +100", bal(alice) == 400 and bal(bob) == 1540)
check("ตั๋วเต็ม → 400", boss.post(f"/events/{eid}/tickets").status_code == 400)
check("เช็คอินด้วยรหัส", bob.post(f"/events/{eid}/checkin", json={"code": code}).json()["name"] == "Alice")
check("เช็คอินซ้ำไม่ได้", bob.post(f"/events/{eid}/checkin", json={"code": code}).status_code == 400)

print("── ครีเอเตอร์ VIP ──")
page = bob.post("/creator", json={"bio": "สอนชงกาแฟ", "monthly_price": 50}).json()["id"]
bob.post("/creator/me/posts", json={"title": "สูตรลับ", "body": "นมสด 30ml", "vip_only": True})
check("ยังไม่สมัคร = ไม่เห็นเนื้อหา VIP", alice.get(f"/creator/{page}/posts").json()["posts"][0]["body"] is None)
alice.post(f"/creator/{page}/subscribe")
check("สมัครแล้วเห็น + จ่าย 50", alice.get(f"/creator/{page}/posts").json()["posts"][0]["body"] == "นมสด 30ml" and bal(alice) == 350)

print("── IoT ──")
key = alice.post("/iot/my/devices", json={"device_id": "esp32-01", "name": "ห้องนอน"}).json()["key"]
check("key ผิด → 401", TestClient(app).post("/iot/device/data", headers={"X-Device-Key": "x"}, json={"device_id": "esp32-01", "temperature": 25}).status_code == 401)
TestClient(app).post("/iot/device/data", headers={"X-Device-Key": key}, json={"device_id": "esp32-01", "temperature": 26.5, "humidity": 60})
check("ค่าล่าสุดขึ้นแดชบอร์ด", alice.get("/iot/my/devices").json()["devices"][0]["latest"]["temperature"]["value"] == 26.5)
check("คนอื่นดูกราฟไม่ได้", bob.get("/iot/my/devices/esp32-01/readings").status_code == 404)
alice.post("/iot/my/devices/esp32-01/commands", json={"command": "LED_ON"})
check("อุปกรณ์รับคำสั่ง (ครั้งเดียว)", TestClient(app).get("/iot/device/commands", headers={"X-Device-Key": key}).json()["commands"] == ["LED_ON"]
      and TestClient(app).get("/iot/device/commands", headers={"X-Device-Key": key}).json()["commands"] == [])

print("── สุขภาพ ──")
t0 = tok(bob)
pic = lambda: {"file": ("run.jpg", io.BytesIO(b"\xff\xd8\xff jpg"), "image/jpeg")}
check("ไม่แนบรูป → ไม่รับ", bob.post("/health", data={"activity": "วิ่ง", "minutes": "45"}).status_code in (400, 422))
bob.post("/health", data={"activity": "วิ่ง", "minutes": "45"}, files=pic())
bob.post("/health", data={"activity": "เดิน", "minutes": "20", "steps": "3000"}, files=pic())
check("65 นาที = 2 โทเคน", tok(bob) - t0 == 2)
bob.post("/health", data={"activity": "ปั่นจักรยาน", "minutes": "600"}, files=pic())
check("วันละไม่เกิน 5 โทเคน", tok(bob) - t0 == 5)
check("สรุป 7 วัน", bob.get("/health").json()["total_minutes"] == 665)
check("AI ไม่พร้อม → คำแนะนำพื้นฐาน", "150" in bob.get("/health/tip").json()["tip"])

os.remove(db_file)
print(f"\n✅ ผ่านทั้งหมด {n} ข้อ")
