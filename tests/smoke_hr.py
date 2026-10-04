"""ทดสอบพนักงาน/ตารางงาน/เงินเดือน: คำนวณรายเดือน-รายวัน-รายชั่วโมง, OT, ขาดงาน, ประกันสังคม, จ่ายเข้ากระเป๋า, สิทธิ์

    python tests/smoke_hr.py
"""
import os, sys, tempfile
from datetime import date, timedelta
db_file = tempfile.mktemp(suffix=".db")
os.environ["DATABASE_URL"] = f"sqlite:///{db_file}"
os.environ.setdefault("SECRET_KEY", "test")
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

owner, emp, other = (client_for(u) for u in ("owner", "emp", "other"))
db = SessionLocal(); move_money(db, db.query(User).filter(User.username == "owner").first().id, 50000, "admin", "seed"); db.commit(); db.close()
bal = lambda c: c.get("/wallet").json()["balance"]
M = "2026-09"; D = lambda d: f"2026-09-{d:02d}"

print("── พนักงาน ──")
a = owner.post("/hr/staff", json={"name": "สมชาย", "position": "แคชเชียร์", "pay_type": "monthly", "rate": 15000, "username": "@emp"}).json()
b = owner.post("/hr/staff", json={"name": "สมหญิง", "pay_type": "daily", "rate": 400, "social_security": False}).json()
c = owner.post("/hr/staff", json={"name": "กะดึก", "pay_type": "hourly", "rate": 60, "social_security": False}).json()
check("เพิ่มพนักงาน 3 แบบ + ผูกบัญชี @emp", a["username"] == "emp" and len(owner.get("/hr/staff").json()["staff"]) == 3)
check("ผูกบัญชีที่ไม่มีอยู่ → 404", owner.post("/hr/staff", json={"name": "x", "rate": 1, "username": "ghost"}).status_code == 404)
check("คนอื่นแก้พนักงานเราไม่ได้", other.put(f"/hr/staff/{a['id']}", json={"name": "x", "rate": 1}).status_code == 404)

print("── ตารางงาน ──")
for d in range(1, 21):
    owner.post("/hr/shifts", json={"staff_id": a["id"], "day": D(d), "start": "09:00", "end": "18:00", "break_min": 60, "status": "worked"})
owner.post("/hr/shifts", json={"staff_id": a["id"], "day": D(21), "start": "09:00", "end": "20:00", "break_min": 60, "status": "worked"})
s22 = owner.post("/hr/shifts", json={"staff_id": a["id"], "day": D(22), "start": "09:00", "end": "18:00"}).json()
check("กะใหม่ = ตามตาราง 8 ชม.", s22["status"] == "planned" and s22["hours"] == 8)
owner.post(f"/hr/shifts/{s22['id']}/status", json={"status": "absent"})
check("บันทึกกะซ้ำวันเดิม = แทนที่ (1 คน 1 กะ/วัน)",
      owner.post("/hr/shifts", json={"staff_id": b["id"], "day": D(1), "start": "08:00", "end": "17:00"}).json()["id"]
      == owner.post("/hr/shifts", json={"staff_id": b["id"], "day": D(1), "start": "08:00", "end": "17:00", "status": "worked"}).json()["id"])
for d in (2, 3):
    owner.post("/hr/shifts", json={"staff_id": b["id"], "day": D(d), "start": "08:00", "end": "17:00", "status": "worked"})
owner.post("/hr/shifts", json={"staff_id": b["id"], "day": D(4), "start": "08:00", "end": "18:00", "status": "worked"})
owner.post("/hr/shifts", json={"staff_id": c["id"], "day": D(5), "start": "22:00", "end": "06:00", "break_min": 0, "status": "worked"})
check("เวลาผิดรูปแบบ → 422", owner.post("/hr/shifts", json={"staff_id": c["id"], "day": D(6), "start": "25:00", "end": "06:00"}).status_code == 422)
check("คนอื่นลงกะให้พนักงานเราไม่ได้", other.post("/hr/shifts", json={"staff_id": a["id"], "day": D(6), "start": "09:00", "end": "18:00"}).status_code == 404)
wk = owner.get("/hr/shifts?start=2026-09-01&days=7").json()
check("ดูตารางรายสัปดาห์", len(wk["days"]) == 7 and len(wk["staff"]) == 3 and len(wk["shifts"]) == 7 + 4 + 1)
cp = owner.post("/hr/shifts/copy-week", json={"from_start": "2026-09-01", "to_start": "2026-10-06"}).json()
check("คัดลอกสัปดาห์ (สถานะเป็น 'ตามตาราง')", cp["copied"] == 12 and
      all(s["status"] == "planned" for s in owner.get("/hr/shifts?start=2026-10-06&days=7").json()["shifts"]))
check("คัดลอกซ้ำไม่ทับของเดิม", owner.post("/hr/shifts/copy-week", json={"from_start": "2026-09-01", "to_start": "2026-10-06"}).json()["copied"] == 0)
check("ยืนยันการมาทำงาน: วันในอนาคตไม่ถูกยืนยัน",
      owner.post("/hr/shifts/confirm", json={"start": (date.today() + timedelta(days=2)).isoformat(), "days": 7}).json()["confirmed"] == 0)

print("── คำนวณเงินเดือน ──")
owner.post("/hr/adjusts", json={"staff_id": a["id"], "month": M, "amount": 1000, "note": "เบี้ยขยัน"})
owner.post("/hr/adjusts", json={"staff_id": a["id"], "month": M, "amount": -200, "note": "เบิกล่วงหน้า"})
pr = owner.get(f"/hr/payroll?month={M}").json()
r = {x["staff"]["name"]: x for x in pr["rows"]}
A = r["สมชาย"]
check("รายเดือน: OT 2 ชม. = 187.50, หักขาด 1 วัน = 500", A["ot_hours"] == 2 and A["ot_pay"] == 187.5 and A["absent_deduct"] == 500 and A["days_worked"] == 21)
check("ประกันสังคม 5% ของ 14,687.50 = 734.38", A["social_security"] == 734.38)
check("รวมรับ 15,687.50 · รวมหัก 934.38 · สุทธิ 14,753.12", A["gross"] == 15687.5 and A["deductions"] == 934.38 and A["net"] == 14753.12)
B = r["สมหญิง"]
check("รายวัน: 4 วัน × 400 + OT 1 ชม. (50×1.5) = 1,675", B["base"] == 1600 and B["ot_pay"] == 75 and B["net"] == 1675)
C = r["กะดึก"]
check("รายชั่วโมง: กะข้ามคืน 22:00–06:00 = 8 ชม. × 60 = 480", C["regular_hours"] == 8 and C["net"] == 480)
check("ยอดรวมทั้งร้าน", pr["totals"]["net"] == round(14753.12 + 1675 + 480, 2))
mg = owner.post("/hr/staff", json={"name": "ผู้จัดการ", "rate": 40000}).json()
owner.post("/hr/shifts", json={"staff_id": mg["id"], "day": D(1), "start": "09:00", "end": "18:00", "status": "worked"})
check("ประกันสังคมสูงสุด 750 (เงินเดือน 40,000)", next(x for x in owner.get(f"/hr/payroll?month={M}").json()["rows"] if x["staff"]["id"] == mg["id"])["social_security"] == 750)

print("── จ่ายเงินเดือน ──")
check("พนักงานไม่ผูกบัญชี จ่ายเข้ากระเป๋าไม่ได้", owner.post(f"/hr/payroll/{b['id']}/pay", json={"month": M, "method": "wallet"}).status_code == 400)
owner.post(f"/hr/payroll/{a['id']}/pay", json={"month": M, "method": "wallet"})
check("จ่ายเข้ากระเป๋า: เจ้าของ -14,753.12, พนักงาน +14,753.12", bal(emp) == 14753.12 and bal(owner) == round(50000 - 14753.12, 2))
check("จ่ายซ้ำไม่ได้", owner.post(f"/hr/payroll/{a['id']}/pay", json={"month": M, "method": "wallet"}).status_code == 400 and bal(emp) == 14753.12)
check("จ่ายแล้วแก้รายการบวก/หักไม่ได้", owner.post("/hr/adjusts", json={"staff_id": a["id"], "month": M, "amount": 5, "note": "x"}).status_code == 400)
check("บันทึกว่าจ่ายเอง (เงินสด) ได้", owner.post(f"/hr/payroll/{b['id']}/pay", json={"month": M, "method": "manual"}).json()["net"] == 1675)
check("ยอดสุทธิ 0 จ่ายไม่ได้", owner.post(f"/hr/payroll/{c['id']}/pay", json={"month": "2026-08", "method": "manual"}).status_code == 400)
me = emp.get("/hr/me").json()
check("พนักงานเห็นสลิป + นายจ้าง", me["payslips"][0]["net"] == 14753.12 and me["payslips"][0]["employer"] == "Owner")
check("คนที่ไม่ใช่พนักงาน เห็นว่าง", other.get("/hr/me").json() == {"jobs": [], "shifts": [], "payslips": []})
csv = owner.get(f"/hr/payroll/export.csv?month={M}")
check("ส่งออก CSV", csv.status_code == 200 and "สมชาย" in csv.text and "จ่ายแล้ว" in csv.text)
check("คนอื่นไม่เห็นเงินเดือนร้านเรา", other.get(f"/hr/payroll?month={M}").json()["rows"] == [])

os.remove(db_file)
print(f"\n✅ ผ่านทั้งหมด {n} ข้อ")
