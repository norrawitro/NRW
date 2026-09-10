# NRW — Norrawit Roopsoong Web

Multi-purpose server สำหรับ:
- 🤖 **IoT / ESP32** — รับข้อมูล sensor, ส่ง command
- 🛍️ **Shop** — ร้านค้าออนไลน์
- 🛠️ **Admin** — จัดการข้อมูลระบบ
- 🎮 **Game** — game server (REST + WebSocket)

## Tech Stack
- **Backend:** FastAPI (Python)
- **Database:** PostgreSQL + SQLAlchemy
- **Tunnel:** Tailscale Funnel

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
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## API Docs
เปิด browser ที่ `http://localhost:8000/docs`

## Structure
```
app/
├── main.py          # Entry point
├── database.py      # DB connection
├── routers/
│   ├── iot.py       # /iot/*
│   ├── shop.py      # /shop/*
│   ├── admin.py     # /admin/*
│   └── game.py      # /game/*
├── models/          # SQLAlchemy models
├── templates/       # HTML (Jinja2)
└── static/          # CSS, JS, Images
```
