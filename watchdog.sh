#!/bin/bash
# NRW Watchdog — รัน uvicorn + auto-restart ถ้่่อดับ + health check ทุก 30 วิ
# Usage: bash watchdog.sh   (รันใน background)
# Logs:  logs/uvicorn.log  (output ของ uvicorn)
#        logs/watchdog.log (เหตุการณ์: start/exit/kill/health)

set -u
cd /home/uusirw/projects/myserver
mkdir -p logs

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a logs/watchdog.log; }

# Health checker: curl ทุก 30 วิ, ถ้าไม่ได้ 2xx/3xx → kill uvicorn ให้ watchdog restart
start_health_check() {
    (
        while true; do
            sleep 30
            code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 http://127.0.0.1:8000/ 2>/dev/null)
            if [ "$code" != "200" ] && [ "$code" != "301" ] && [ "$code" != "302" ]; then
                log "HEALTH FAIL: http_code=$code (expect 200) — killing uvicorn pid=$UVICORN_PID"
                kill "$UVICORN_PID" 2>/dev/null
            fi
        done
    ) &
    HEALTH_PID=$!
}

log "watchdog started (pid $$)"
source venv/bin/activate

while true; do
    log "starting uvicorn..."
    # --timeout-graceful-shutdown: ไม่ค้าง "Waiting for background tasks" ตอนรีสตาร์ท
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --timeout-graceful-shutdown 10 >> logs/uvicorn.log 2>&1 &
    UVICORN_PID=$!
    log "uvicorn started (pid $UVICORN_PID)"
    start_health_check
    wait "$UVICORN_PID"
    EXIT_CODE=$?
    kill "$HEALTH_PID" 2>/dev/null
    log "uvicorn EXITED with code $EXIT_CODE — restarting in 5s"
    sleep 5
done
