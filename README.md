# NRW — Norrawit Roopsoong Web

Multi-purpose server สำหรับ Norrawit Roopsoong (Gnoom)

🌐 **Live:** https://nora-web.tail85b885.ts.net/

---

## Features

- 🤖 **IoT / ESP32** — รับข้อมูล sensor, ส่ง command
- 🛍️ **Shop** — ร้านค้าออนไลน์
- 🛠️ **Admin** — จัดการข้อมูลระบบ
- 🎮 **Game** — game server (REST + WebSocket)

---

## Tech Stack

| Layer | Tech |
|-------|------|
| Backend | FastAPI (Python) |
| Database | PostgreSQL + SQLAlchemy |
| Tunnel | Tailscale Funnel |
| Frontend | HTML + Jinja2 (v2 design) |

---

## Setup

```bash
# 1. สร้าง virtual environment
python3 -m venv venv
source venv/bin/activate

# 2. ติดตั้ง dependencies
pip install -r requirements.txt

# 3. ตั้งค่า environment
cp .env.example .env
# แก้ไข .env ให้ตรงกับ database ของคุณ

# 4. รัน server
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

## Start with Tailscale Funnel (Public Access)

```bash
# Start uvicorn
bash start.sh

# Setup funnel (reset ก่อนเสมอ)
tailscale serve reset
tailscale funnel reset
tailscale serve --bg 8000
tailscale funnel --bg 8000

# ตรวจสอบ
tailscale funnel status
```

---

## API Docs

เปิด browser ที่ `http://localhost:8000/docs`

---

## Project Structure

```
myserver/
├── app/
│   ├── main.py          # Entry point
│   ├── database.py      # DB connection
│   ├── routers/
│   │   ├── iot.py       # /iot/*
│   │   ├── shop.py      # /shop/*
│   │   ├── admin.py     # /admin/*
│   │   └── game.py      # /game/*
│   ├── models/          # SQLAlchemy models
│   ├── templates/       # HTML (Jinja2)
│   │   ├── nora-web.html    # Main page (v2)
│   │   └── index.html
│   └── static/          # CSS, JS, Images
├── nora-web_v2.html     # Standalone v2 design
├── start.sh             # Start uvicorn script
├── funnel.sh            # Tailscale funnel script
├── requirements.txt
└── .env.example
```

---

## Changelog

- **v2** — nora-web redesign with new design system (dark/light, responsive)
- **v1** — initial FastAPI + Tailscale Funnel setup
