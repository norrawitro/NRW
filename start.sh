#!/bin/bash
# NRW Start Script (v2 — watchdog mode)
# Usage: bash start.sh
# - รัน uvicorn ผ่าน watchdog.sh (auto-restart + health check + persistent log)
# - Logs: logs/uvicorn.log, logs/watchdog.log
# - Backup เดิม (foreground, ไม่มี log): start.sh.bak.20260914_175300

set -e
cd /home/uusirw/projects/myserver
mkdir -p logs

# ถ้่่า server รันอยู่แล้ว → ไม่ทำอะไรมาก
if curl -s -o /dev/null --max-time 5 http://127.0.0.1:8000/ 2>/dev/null; then
    echo "=== NRW Server already running on http://localhost:8000 ==="
    exit 0
fi

# Kill uvicorn เก่าท่ีอาจค้างอยู่ (ไม่มี watchdog)
pkill -f "uvicorn app.main:app" 2>/dev/null || true
sleep 2

# รัน watchdog ใน background (detached — รันตอดอยู่แม้ terminal ปิ่ด)
# (watchdog.sh log เองลง logs/watchdog.log + logs/uvicorn.log)
nohup bash watchdog.sh >/dev/null 2>&1 &
echo "=== NRW Server starting (watchdog mode) ==="
echo "Local:    http://localhost:8000"
echo "API Docs: http://localhost:8000/docs"
echo "Logs:     logs/uvicorn.log  /  logs/watchdog.log"
echo "Stop:     pkill -f watchdog.sh && pkill -f 'uvicorn app.main:app'"

# รอยให้ server พร้อม (max 30 วิ)
for i in $(seq 1 30); do
    code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 2 http://127.0.0.1:8000/ 2>/dev/null || true)
    if [ "$code" = "200" ]; then
        echo "=== Ready (HTTP $code) ==="
        exit 0
    fi
    sleep 1
done
echo "=== WARNING: server ยังไม่พร้อมใน 30 วิ — ดูล็อกที่ logs/uvicorn.log ==="
exit 1
