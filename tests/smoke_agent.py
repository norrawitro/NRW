"""ทดสอบ AI Agent (เฉพาะเจ้าของ): สิทธิ์, รหัสผ่าน, ล็อกเมื่อใส่ผิด, คำสั่งเข้า tmux, สถานะ CPU/GPU/Ollama
ใช้ terminal ปลอม — ไม่ต้องมี tmux/ollama จริง

    python tests/smoke_agent.py
"""
import os, sys, tempfile
db_file = tempfile.mktemp(suffix=".db")
os.environ["DATABASE_URL"] = f"sqlite:///{db_file}"
os.environ.setdefault("SECRET_KEY", "test")
os.environ["OLLAMA_URL"] = "http://127.0.0.1:9"
os.environ["AGENT_ENTER_DELAY"] = "0.05"
# ใช้ค่าทดสอบเสมอ — ไม่ให้ค่าใน .env ของเครื่องจริง (ปุ่มโมเดล, ชื่อ session, เจ้าของ) มาทำให้ผลเปลี่ยน
os.environ.update(AGENT_SHELL_TARGET="shell", AGENT_TMUX_TARGET="hermes", AGENT_STOP="C-c", AGENT_RESET="/new", AGENT_START_CMD="hermes", AGENT_OWNER="",
                  AGENT_PASSWORD_HASH="", AGENT_MODELS="9arm Gateway=/model --provider 9arm;"
                  "Coder 30B=/model qwen3-coder:30b --provider ollama-launch;Coder 3B=/model qwen2.5-coder:3b --provider ollama-launch;"
                  "Qwen3.5 2B=/model qwen3.5:2b --provider ollama-launch")          # ปิดไว้ → ใช้ `ollama ps` (ปลอม)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app.models.user import User
from app.routers import agent as agent_mod
from app.services import agent_host as host

calls = []
tmux = {"alive": True}
OLLAMA_PS = """NAME                 ID              SIZE      PROCESSOR          UNTIL
qwen3-coder:30b      abc123def456    21 GB     48%/52% CPU/GPU    4 minutes from now
qwen2.5-coder:3b     0123456789ab    2.4 GB    100% GPU           Forever
"""
def fake_run(args, timeout=5):
    calls.append(args)
    if args[:2] == ["tmux", "has-session"]:
        return (0 if tmux["alive"] else 1), ""
    if args[:2] == ["tmux", "new-session"]:
        tmux["alive"] = True; return 0, ""
    if args[:2] == ["tmux", "kill-session"]:
        tmux["alive"] = False; return 0, ""
    if args[:2] == ["tmux", "capture-pane"]:
        return 0, "hermes> สวัสดี\nพร้อมทำงาน\n"
    if args[:2] == ["ollama", "ps"]:
        return 0, OLLAMA_PS
    if "nvidia-smi" in args[0]:
        return 0, "NVIDIA GeForce RTX 4060, 37, 6100, 8188, 55\n"
    return 0, ""
host.run = fake_run
host.shutil.which = lambda name: "/usr/bin/nvidia-smi" if name == "nvidia-smi" else None

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

boss, admin2, cust = (client_for(u) for u in ("boss", "admin2", "cust"))
db = SessionLocal(); db.query(User).filter(User.username.in_(["boss", "admin2"])).update({"is_admin": True}, synchronize_session=False); db.commit(); db.close()
H = {"X-WKW-Agent": "1"}
ck = lambda c, name: next(x.value for x in c.cookies.jar if x.name == name)

print("── สิทธิ์ ──")
check("ลูกค้าเข้าไม่ได้ (403)", cust.get("/agent/state").status_code == 403 and cust.post("/agent/unlock", json={"password": "x"}).status_code == 403)
check("ไม่ login เข้าไม่ได้", TestClient(app).get("/agent/state").status_code == 401)
os.environ.pop("AGENT_PASSWORD_HASH", None)
check("ยังไม่ตั้งรหัส = ปิดใช้งาน", boss.get("/agent/state").json()["enabled"] is False and boss.post("/agent/send", json={"text": "hi"}, headers=H).status_code == 403)
os.environ["AGENT_PASSWORD_HASH"] = agent_mod.make_hash("correct-horse-42")
check("ตั้งรหัสแล้ว แต่ยังไม่ปลดล็อก → 401", boss.get("/agent/status").status_code == 401 and boss.post("/agent/send", json={"text": "hi"}, headers=H).status_code == 401)

print("── รหัสผ่าน ──")
check("รหัสผิด → 401 บอกจำนวนครั้งที่เหลือ", "เหลือ 4" in boss.post("/agent/unlock", json={"password": "wrong"}).json()["detail"])
r = boss.post("/agent/unlock", json={"password": "correct-horse-42"})
check("รหัสถูก → ปลดล็อก + cookie httponly", r.status_code == 200 and "httponly" in r.headers["set-cookie"].lower() and "samesite=strict" in r.headers["set-cookie"].lower())
check("สถานะ: ปลดล็อกแล้ว + ปุ่มโมเดล 4 ปุ่ม", boss.get("/agent/state").json()["unlocked"] is True and len(boss.get("/agent/state").json()["models"]) == 4)
for _ in range(5):
    admin2.post("/agent/unlock", json={"password": "nope"})
check("ผิด 5 ครั้ง → ล็อก 15 นาที (แม้รหัสถูก)", admin2.post("/agent/unlock", json={"password": "correct-horse-42"}).status_code == 429)
check("cookie ของ boss ใช้กับบัญชีอื่นไม่ได้", TestClient(app, cookies={"nrw_token": ck(admin2, "nrw_token"), "wkw_agent": ck(boss, "wkw_agent")}).get("/agent/status").status_code == 401)

print("── คำสั่งเข้า terminal ──")
check("POST ไม่มี header X-WKW-Agent → 403 (กันเว็บอื่นสั่ง)", boss.post("/agent/send", json={"text": "hi"}).status_code == 403)
calls.clear()
boss.post("/agent/send", json={"text": "/queue สร้างหน้า login\nแล้วทดสอบ; rm -rf /"}, headers=H)
check("ส่ง: tmux send-keys -l ข้อความตามตัวอักษร (ไม่ผ่าน shell) + Enter",
      calls[0] == ["tmux", "send-keys", "-t", "hermes", "-l", "/queue สร้างหน้า login แล้วทดสอบ; rm -rf /"] and calls[1] == ["tmux", "send-keys", "-t", "hermes", "Enter"])
calls.clear(); boss.post("/agent/enter", headers=H)
check("ปุ่ม Enter = กด Enter อย่างเดียว", calls == [["tmux", "send-keys", "-t", "hermes", "Enter"]])
import time as _t; _t0 = _t.time(); os.environ["AGENT_ENTER_DELAY"] = "0.3"; boss.post("/agent/send", json={"text": "x"}, headers=H)
check("รอก่อนกด Enter (กัน Hermes มองเป็นการวาง)", _t.time() - _t0 >= 0.3); os.environ["AGENT_ENTER_DELAY"] = "0.05"
calls.clear(); boss.post("/agent/model", json={"id": 1}, headers=H)
check("ปุ่มโมเดล Coder 30B → ส่ง /model qwen3-coder:30b --provider ollama-launch", calls[0][-1] == "/model qwen3-coder:30b --provider ollama-launch")
check("โมเดลที่ไม่มี → 404", boss.post("/agent/model", json={"id": 9}, headers=H).status_code == 404)
calls.clear(); boss.post("/agent/stop", headers=H)
check("Stop = กด Ctrl+C", calls == [["tmux", "send-keys", "-t", "hermes", "C-c"]])
calls.clear(); boss.post("/agent/reset", headers=H)
check("Reset = ส่ง /new + Enter", calls[0][-1] == "/new" and calls[1][-1] == "Enter")
os.environ["AGENT_MODELS"] = "Gateway=/model gw-x;Local=/model foo:1b"
check("ตั้งปุ่มโมเดลเองผ่าน .env ได้", [m["label"] for m in boss.get("/agent/state").json()["models"]] == ["Gateway", "Local"])

print("── ปุ่มคีย์ + session ──")
calls.clear(); boss.post("/agent/key", json={"key": "C-l"}, headers=H)
check("ปุ่ม Ctrl+L → tmux send-keys C-l", calls == [["tmux", "send-keys", "-t", "hermes", "C-l"]])
check("คีย์นอกรายการ → 400", boss.post("/agent/key", json={"key": "C-x"}, headers=H).status_code == 400
      and boss.post("/agent/key", json={"key": "a;rm"}, headers=H).status_code == 400)
check("มี session อยู่แล้ว กดเริ่มใหม่ → 400", boss.post("/agent/session", json={"action": "start"}, headers=H).status_code == 400)
tmux["alive"] = False; calls.clear()
r = boss.post("/agent/session", json={"action": "start"}, headers=H)
check("ไม่มี session → สร้าง tmux -d แล้วพิมพ์ hermes + Enter", r.status_code == 200
      and any(c[:5] == ["tmux", "new-session", "-d", "-s", "hermes"] for c in calls) and ["tmux", "send-keys", "-t", "hermes", "-l", "hermes"] in calls)
calls.clear(); boss.post("/agent/session", json={"action": "restart"}, headers=H)
check("รีสตาร์ต = kill-session แล้วสร้างใหม่", ["tmux", "kill-session", "-t", "hermes"] in calls and any(c[:2] == ["tmux", "new-session"] for c in calls))
check("state มีรายการปุ่มคีย์", "C-c" in [k["key"] for k in boss.get("/agent/state").json()["keys"]])

print("── โหมด Shell (bash ใน WSL) ──")
calls.clear(); boss.post("/agent/send?target=shell", json={"text": "ls -la"}, headers=H)
check("Shell: ส่งเข้า tmux session shell", calls[0] == ["tmux", "send-keys", "-t", "shell", "-l", "ls -la"] and calls[1] == ["tmux", "send-keys", "-t", "shell", "Enter"])
calls.clear(); boss.post("/agent/send?target=shell", json={"text": "cd ~/projects\ngit status"}, headers=H)
check("Shell: หลายบรรทัด = รันทีละคำสั่ง", [c[-1] for c in calls if "-l" in c] == ["cd ~/projects", "git status"])
check("Shell: เกิน 20 คำสั่ง → 400", boss.post("/agent/send?target=shell", json={"text": "\n".join(["ls"] * 21)}, headers=H).status_code == 400)
calls.clear(); boss.post("/agent/stop?target=shell", headers=H)
check("Shell: Stop = Ctrl+C ที่ session shell", calls == [["tmux", "send-keys", "-t", "shell", "C-c"]])
check("เป้าหมายแปลก → 422", boss.post("/agent/send?target=root", json={"text": "x"}, headers=H).status_code == 422)
tmux["alive"] = False; calls.clear()
boss.post("/agent/session?target=shell", json={"action": "start"}, headers=H)
check("Shell: เริ่ม session = tmux new -s shell (bash เปล่า ไม่พิมพ์ hermes)",
      any(c[:5] == ["tmux", "new-session", "-d", "-s", "shell"] for c in calls) and not any("-l" in c for c in calls))
st = boss.get("/agent/status?target=shell").json()
check("Shell: สถานะ/หน้าจอของ session shell", st["tmux"]["target"] == "shell" and st["tmux"]["mode"] == "shell"
      and ["tmux", "capture-pane", "-p", "-J", "-t", "shell", "-S", "-120"] in calls)
check("state มีทั้ง Hermes และ Shell", [t["id"] for t in boss.get("/agent/state").json()["targets"]] == ["hermes", "shell"])

print("── สถานะ ──")
st = boss.get("/agent/status").json()
check("CPU/RAM เป็น %", isinstance(st["cpu"], float) and 0 <= st["cpu"] <= 100 and st["mem"] is not None)
check("GPU % + หน่วยความจำ GPU", st["gpu"] == 37 and st["gpus"][0]["mem_percent"] == 74.5)
m = {x["name"]: x for x in st["ollama"]["models"]}
check("Ollama: โมเดลแบ่ง CPU 48% / GPU 52%", m["qwen3-coder:30b"]["cpu_pct"] == 48 and m["qwen3-coder:30b"]["gpu_pct"] == 52)
check("Ollama: โมเดล 100% GPU", m["qwen2.5-coder:3b"]["gpu_pct"] == 100 and m["qwen2.5-coder:3b"]["cpu_pct"] == 0)
check("หน้าจอ terminal + ประวัติคำสั่ง", "พร้อมทำงาน" in st["screen"] and st["history"][0]["target"] == "shell")

print("── ล็อก / เปลี่ยนรหัส ──")
boss.post("/agent/lock")
check("กดล็อก → ต้องใส่รหัสใหม่", boss.get("/agent/status").status_code == 401)
boss.post("/agent/unlock", json={"password": "correct-horse-42"})
os.environ["AGENT_PASSWORD_HASH"] = agent_mod.make_hash("new-password-99")
check("เปลี่ยนรหัส → session เก่าใช้ไม่ได้ทันที", boss.get("/agent/status").status_code == 401)
os.environ["AGENT_OWNER"] = "boss"
check("AGENT_OWNER=boss → ผู้ดูแลคนอื่นเข้าไม่ได้", admin2.get("/agent/state").status_code == 403 and boss.get("/agent/state").status_code == 200)

os.remove(db_file)
print(f"\n✅ ผ่านทั้งหมด {n} ข้อ")
