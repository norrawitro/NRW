#!/bin/bash
# NRW Restart — รีสตาร์ท uvicorn ให้โหลดโค้ดใหม่ (watchdog จะเปิดตัวใหม่ให้เอง)
# Usage: bash restart.sh
cd /home/uusirw/projects/myserver
pkill -f 'uvicorn app.main:app'
# รอปิดตัวปกติ สูงสุด 10 วิ — ถ้ายังค้างอยู่ให้บังคับปิด
for i in $(seq 1 10); do pgrep -f 'uvicorn app.main:app' >/dev/null || break; sleep 1; done
pgrep -f 'uvicorn app.main:app' >/dev/null && { echo "บังคับปิด uvicorn ที่ค้าง"; pkill -9 -f 'uvicorn app.main:app'; }
# ถ้า watchdog ไม่ได้รันอยู่ → เปิดด้วย start.sh
pgrep -f 'watchdog.sh' >/dev/null || { echo "watchdog ไม่ได้รัน — เปิดใหม่"; nohup bash watchdog.sh >/dev/null 2>&1 & }
for i in $(seq 1 40); do
    code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 2 http://127.0.0.1:8000/ 2>/dev/null)
    [ "$code" = "200" ] && { echo "=== พร้อมใช้งาน (HTTP 200) ==="; exit 0; }
    sleep 1
done
echo "=== ยังไม่พร้อม — ดู logs/uvicorn.log ==="; tail -15 logs/uvicorn.log; exit 1
