"""NRW agent host — คุยกับเครื่อง WSL ของเจ้าของ: ส่งข้อความเข้า tmux, อ่านหน้าจอ, สถานะ CPU/GPU/Ollama

ทุกคำสั่งเรียกผ่าน run() แบบ list (ไม่ผ่าน shell → กันการแทรกคำสั่ง) และทดสอบได้โดยแทน run()
ตั้งค่าใน .env (ไม่ตั้ง = ใช้ค่าเริ่มต้นด้านล่าง):
  AGENT_TMUX_TARGET=hermes                      ชื่อ session (หรือ session:window.pane) ของ tmux ที่รัน Hermes
  AGENT_MODELS=9arm Gateway=/model 9arm;Coder 30B=/model qwen3-coder:30b;Coder 3B=/model qwen2.5-coder:3b
                                                ปุ่มเลือกโมเดล: ชื่อปุ่ม=ข้อความที่ส่ง คั่นด้วย ;
  AGENT_STOP=C-c                                ปุ่ม Stop: C-c = กด Ctrl+C, หรือใส่ข้อความ เช่น /stop
  AGENT_RESET=/new                              ปุ่ม Reset: ข้อความที่ส่ง (เช่น /new หรือ /reset)
  AGENT_ENTER_DELAY=0.6                         รอกี่วินาทีหลังพิมพ์ก่อนกด Enter (Hermes มองว่าข้อความ+Enter ที่มาพร้อมกัน
                                                = การวาง (paste) → Enter กลายเป็นขึ้นบรรทัดใหม่แทนการส่ง)
  OLLAMA_URL=http://localhost:11434"""
import os
import shutil
import subprocess
import time

import httpx

TMUX_TARGET = os.getenv("AGENT_TMUX_TARGET", "hermes")
STOP_CMD = os.getenv("AGENT_STOP", "C-c")
RESET_CMD = os.getenv("AGENT_RESET", "/new")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
DEFAULT_MODELS = "9arm Gateway=/model 9arm;Coder 30B=/model qwen3-coder:30b;Coder 3B=/model qwen2.5-coder:3b"
TMUX_KEYS = {"C-c", "C-d", "C-z", "Escape", "Enter"}     # ปุ่มพิเศษที่ส่งเป็นการกดคีย์


def models() -> list[dict]:
    out = []
    for i, part in enumerate(os.getenv("AGENT_MODELS", DEFAULT_MODELS).split(";")):
        if "=" in part:
            label, cmd = part.split("=", 1)
            if label.strip() and cmd.strip():
                out.append({"id": i, "label": label.strip(), "command": cmd.strip()})
    return out


def run(args: list[str], timeout: float = 5) -> tuple[int, str]:
    """เรียกโปรแกรม — คืน (exit code, stdout+stderr); ไม่มีโปรแกรม = (127, '')"""
    try:
        p = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except FileNotFoundError:
        return 127, ""
    except subprocess.TimeoutExpired:
        return 124, "timeout"


# ─── tmux ─────────────────────────────────────────────────────
def send_text(text: str) -> tuple[bool, str]:
    """พิมพ์ข้อความลง tmux แล้วกด Enter (-l = ส่งตามตัวอักษร ไม่ตีความเป็นคีย์)"""
    code, out = run(["tmux", "send-keys", "-t", TMUX_TARGET, "-l", text])
    if code != 0:
        return False, out.strip() or "ส่งเข้า tmux ไม่ได้"
    time.sleep(float(os.getenv("AGENT_ENTER_DELAY", "0.6")))
    return press("Enter")


def press(key: str) -> tuple[bool, str]:
    """กดคีย์พิเศษ 1 ครั้ง (Enter, C-c, …)"""
    code, out = run(["tmux", "send-keys", "-t", TMUX_TARGET, key])
    return code == 0, out.strip()


def send_command(cmd: str) -> tuple[bool, str]:
    """ค่าใน .env เป็นได้ทั้งคีย์ (C-c) หรือข้อความ (/stop)"""
    if cmd in TMUX_KEYS:
        return press(cmd)
    return send_text(cmd)


def capture(lines: int = 120) -> tuple[bool, str]:
    code, out = run(["tmux", "capture-pane", "-p", "-J", "-t", TMUX_TARGET, "-S", f"-{lines}"])
    return code == 0, out.rstrip()


# ─── สถานะเครื่อง ─────────────────────────────────────────────
_cpu_prev: tuple[int, int] | None = None


def _cpu_times() -> tuple[int, int] | None:
    try:
        with open("/proc/stat") as f:
            vals = list(map(int, f.readline().split()[1:]))
    except (OSError, ValueError):
        return None
    idle = vals[3] + (vals[4] if len(vals) > 4 else 0)
    return idle, sum(vals)


def cpu_percent() -> float | None:
    """% การใช้ CPU ตั้งแต่ครั้งก่อนที่ถาม (ครั้งแรกวัด 0.2 วินาที)"""
    global _cpu_prev
    now = _cpu_times()
    if not now:
        return None
    if not _cpu_prev:
        time.sleep(0.2)
        _cpu_prev, now = now, _cpu_times()
    d_idle, d_total = now[0] - _cpu_prev[0], now[1] - _cpu_prev[1]
    _cpu_prev = now
    return round(100 * (1 - d_idle / d_total), 1) if d_total > 0 else 0.0


def mem_percent() -> float | None:
    try:
        info = {}
        with open("/proc/meminfo") as f:
            for line in f:
                k, v = line.split(":", 1)
                info[k] = int(v.split()[0])
        return round(100 * (1 - info["MemAvailable"] / info["MemTotal"]), 1)
    except (OSError, KeyError, ValueError):
        return None


def parse_nvidia(out: str) -> list[dict]:
    gpus = []
    for line in out.strip().splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) >= 4:
            try:
                util, used, total = float(parts[1]), float(parts[2]), float(parts[3])
            except ValueError:
                continue
            gpus.append({"name": parts[0], "util": util, "mem_used_mb": used, "mem_total_mb": total,
                         "mem_percent": round(100 * used / total, 1) if total else None,
                         "temp": float(parts[4]) if len(parts) > 4 and parts[4].replace(".", "").isdigit() else None})
    return gpus


def gpu_status() -> list[dict]:
    exe = shutil.which("nvidia-smi") or ("/usr/lib/wsl/lib/nvidia-smi" if os.path.exists("/usr/lib/wsl/lib/nvidia-smi") else None)
    if not exe:
        return []
    code, out = run([exe, "--query-gpu=name,utilization.gpu,memory.used,memory.total,temperature.gpu",
                     "--format=csv,noheader,nounits"])
    return parse_nvidia(out) if code == 0 else []


def parse_ollama_ps(out: str) -> list[dict]:
    """แปลงผล `ollama ps` (ใช้เมื่อเรียก API ไม่ได้) — คอลัมน์ PROCESSOR เช่น '100% GPU', '48%/52% CPU/GPU'"""
    rows = []
    lines = out.strip().splitlines()
    if not lines or not lines[0].startswith("NAME"):
        return rows
    head = lines[0]
    cols = {c: head.index(c) for c in ("NAME", "ID", "SIZE", "PROCESSOR", "UNTIL") if c in head}
    for line in lines[1:]:
        if not line.strip():
            continue
        proc = line[cols["PROCESSOR"]:cols.get("UNTIL", len(line))].strip() if "PROCESSOR" in cols else ""
        size = line[cols["SIZE"]:cols.get("PROCESSOR", len(line))].strip() if "SIZE" in cols else ""
        rows.append({"name": line.split()[0], "size": size, "processor": proc, **_split_processor(proc)})
    return rows


def _split_processor(p: str) -> dict:
    p = p.upper()
    if "/" in p and "CPU/GPU" in p:
        a, b = p.split()[0].split("/")
        return {"cpu_pct": float(a.rstrip("%")), "gpu_pct": float(b.rstrip("%"))}
    if p.endswith("GPU"):
        return {"cpu_pct": 0.0, "gpu_pct": float(p.split("%")[0])}
    if p.endswith("CPU"):
        return {"cpu_pct": float(p.split("%")[0]), "gpu_pct": 0.0}
    return {"cpu_pct": None, "gpu_pct": None}


def ollama_status() -> dict:
    """โมเดลที่โหลดอยู่ + สัดส่วน CPU/GPU — ใช้ API /api/ps ก่อน ไม่ได้ค่อยเรียก `ollama ps`"""
    try:
        r = httpx.get(f"{OLLAMA_URL}/api/ps", timeout=2)
        r.raise_for_status()
        rows = []
        for m in r.json().get("models", []):
            size, vram = m.get("size") or 0, m.get("size_vram") or 0
            gpu = round(100 * vram / size) if size else 0
            rows.append({"name": m.get("name"), "size": f"{size / 1e9:.1f} GB", "cpu_pct": float(100 - gpu), "gpu_pct": float(gpu),
                         "processor": f"{100 - gpu}%/{gpu}% CPU/GPU" if 0 < gpu < 100 else ("100% GPU" if gpu == 100 else "100% CPU"),
                         "until": m.get("expires_at", "")[:19].replace("T", " ")})
        return {"online": True, "models": rows}
    except Exception:
        code, out = run(["ollama", "ps"])
        return {"online": code == 0, "models": parse_ollama_ps(out) if code == 0 else []}


def tmux_alive() -> bool:
    code, _ = run(["tmux", "has-session", "-t", TMUX_TARGET.split(":")[0]])
    return code == 0
