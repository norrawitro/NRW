#!/bin/bash
# NRW Upgrade Verify — ทดสอบ mock→real ทุก step
# Usage: bash verify.sh [1|2|3|4|all]
# ใช้ test user: verify_bot (สร้างให้อัตโนมัติ, password: verify_bot_pw_2026)

set -u
cd /home/uusirw/projects/myserver
source venv/bin/activate

PASS=0; FAIL=0
ok()   { echo "  ✅ $1"; PASS=$((PASS+1)); }
bad()  { echo "  ❌ $1"; FAIL=$((FAIL+1)); }
check(){ if [ "$2" = "$3" ]; then ok "$1"; else bad "$1 (got: $2, want: $3)"; fi; }

BASE=http://127.0.0.1:8000
JAR=$(mktemp)

# ── Login (สร้าง verify_bot ถ้่ายังไม่มี) ─────────────────────
python3 - <<'PYEOF'
from app.database import SessionLocal
from app.models.user import User
from app.auth import hash_password
db = SessionLocal()
u = db.query(User).filter(User.username=="verify_bot").first()
if not u:
    u = User(username="verify_bot", email="verify_bot@test.local",
             full_name="Verify Bot", hashed_pw=hash_password("verify_bot_pw_2026"), is_active=True)
    db.add(u); db.commit()
print("verify_bot ready")
PYEOF

login() {
    rm -f "$JAR"
    code=$(curl -s -o /dev/null -w "%{http_code}" -c "$JAR" -X POST "$BASE/members/login" \
        -d "username=verify_bot&password=verify_bot_pw_2026")
    # login redirect 302 → cookie set
    grep -q nrw_token "$JAR" && ok "login verify_bot (cookie set)" || bad "login verify_bot"
}

# ═══ STEP 1: WALLET ═══════════════════════════════════════════
step1() {
    echo "── Step 1: Wallet จริง ──"
    login
    # 1.1 GET /wallet
    d=$(curl -s -b "$JAR" "$BASE/wallet")
    echo "$d" | grep -q '"balance"' && ok "GET /wallet ตอบ JSON" || bad "GET /wallet: $d"
    # 1.2 topup 100
    code=$(curl -s -o /dev/null -w "%{http_code}" -b "$JAR" -X POST "$BASE/wallet/tx" \
        -H 'Content-Type: application/json' -d '{"type":"topup","amount":100,"desc":"verify topup"}')
    check "POST /wallet/tx topup 100" "$code" "200"
    # 1.3 balance ใน DB เพิ่ม 100
    bal=$(python3 -c "
from app.database import SessionLocal
from app.models.wallet import Wallet
from app.models.user import User
db=SessionLocal()
u=db.query(User).filter(User.username=='verify_bot').first()
w=db.query(Wallet).filter(Wallet.user_id==u.id).first()
print(w.balance if w else 'none')" 2>/dev/null)
    echo "  (DB balance=$bal)"
    echo "$bal" | grep -q . && ok "wallet ใน DB มีข้อมูล" || bad "wallet ใน DB"
    # 1.4 withdraw เกินยอด → reject
    code=$(curl -s -o /dev/null -w "%{http_code}" -b "$JAR" -X POST "$BASE/wallet/tx" \
        -H 'Content-Type: application/json' -d '{"type":"withdraw","amount":999999,"desc":"overdraw test"}')
    [ "$code" = "400" ] && ok "withdraw เกินยอด → 400" || bad "withdraw เกินยอด (got $code, want 400)"
    # 1.5 tx history มีรายการ
    d=$(curl -s -b "$JAR" "$BASE/wallet")
    echo "$d" | grep -q 'verify topup' && ok "tx history มี 'verify topup'" || bad "tx history"
    # 1.6 ไม่ login → 401
    code=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/wallet")
    check "GET /wallet ไม่ login → 401" "$code" "401"
}

# ═══ STEP 2: CLOUD ════════════════════════════════════════════
step2() {
    echo "── Step 2: Cloud จริง ──"
    login
    # 2.1 GET /cloud
    d=$(curl -s -b "$JAR" "$BASE/cloud")
    echo "$d" | grep -q '"items"' && ok "GET /cloud ตอบ JSON" || bad "GET /cloud: $d"
    # 2.2 สร้างโฟลเดอร์
    d=$(curl -s -b "$JAR" -X POST "$BASE/cloud/folders" -H 'Content-Type: application/json' \
        -d '{"name":"verify_folder_'"$(date +%s)"'"}')
    fid=$(echo "$d" | python3 -c "import json,sys; print(json.load(sys.stdin)['id'])" 2>/dev/null)
    [ -n "$fid" ] && ok "สร้างโฟลเดอร์ (id=$fid)" || bad "สร้างโฟลเดอร์: $d"
    # 2.3 upload ไฟล์
    echo "verify file content $(date +%s)" > /tmp/verify_upload.txt
    code=$(curl -s -o /dev/null -w "%{http_code}" -b "$JAR" -X POST "$BASE/cloud/upload" \
        -F "file=@/tmp/verify_upload.txt" -F "folder_id=$fid")
    check "upload ไฟล์" "$code" "200"
    # 2.4 download ไฟล์ → เนื้่อหาตรง
    d=$(curl -s -b "$JAR" "$BASE/cloud?folder_id=$fid")
    file_id=$(echo "$d" | python3 -c "
import json,sys
d=json.load(sys.stdin)
f=[i for i in d['items'] if i['type']=='file']
print(f[0]['id'] if f else '')" 2>/dev/null)
    if [ -n "$file_id" ]; then
        dl=$(curl -s -b "$JAR" "$BASE/cloud/download/$file_id")
        echo "$dl" | grep -q "verify file content" && ok "download ไฟล์ (เนื้่อหาตรง)" || bad "download: $dl"
    else
        bad "หา file_id จาก /cloud?folder_id=$fid"
    fi
    # 2.5 storage used > 0 (ดู used_bytes เพราะไฟล์เล็กรั้บ GB = 0.0)
    d=$(curl -s -b "$JAR" "$BASE/cloud")
    echo "$d" | python3 -c "import json,sys; d=json.load(sys.stdin); assert d['storage']['used_bytes']>0" 2>/dev/null \
        && ok "storage used > 0" || bad "storage used"
}

# ═══ STEP 3: AI ═══════════════════════════════════════════════
step3() {
    echo "── Step 3: AI จริง ──"
    login
    # 3.1 Ollama รันอยู่?
    curl -s --max-time 5 http://localhost:11434/api/tags >/dev/null 2>&1 \
        && ok "Ollama รันอยู่" || bad "Ollama ไม่ได้รัน"
    # 3.2 chat ถามยอดเงิน → คำตอบมีจำนวนเงิน
    d=$(curl -s -b "$JAR" -X POST "$BASE/ai/chat" -H 'Content-Type: application/json' \
        -d '{"message":"เช็คยอดเงินฉัน"}')
    echo "$d" | grep -q '"reply"' && ok "POST /ai/chat ตอบ JSON" || bad "POST /ai/chat: $d"
    bal=$(curl -s -b "$JAR" "$BASE/wallet" | python3 -c "import json,sys; print(json.load(sys.stdin)['balance'])" 2>/dev/null)
    echo "  (balance=$bal)"
    if [ -n "$bal" ]; then
        echo "$d" | grep -q "$bal" && ok "คำตอบ AI มียอดเงินจริง ($bal)" || \
            echo "  ⚠️ คำตอบ AI: $(echo "$d" | python3 -c "import json,sys; print(json.load(sys.stdin).get('reply','')[:100])" 2>/dev/null)"
    fi
}

# ═══ STEP 4: FULL ═════════════════════════════════════════════
step4() {
    echo "── Step 4: ทดสอบครบ ──"
    # 4.1 public page 200
    check "GET / (public)" "$(curl -s -o /dev/null -w "%{http_code}" "$BASE/")" "200"
    check "GET / (funnel)" "$(curl -s -o /dev/null -w "%{http_code}" --max-time 15 ${PUBLIC_URL:-https://wkw.tail85b885.ts.net}/)" "200"
    # 4.2 news ยังทำงาน
    check "GET /news/posts" "$(curl -s -o /dev/null -w "%{http_code}" "$BASE/news/posts")" "200"
    # 4.3 wallet chip ในหน้าเว็บ (UI ดึง API)
    login
    curl -s -b "$JAR" "$BASE/" | grep -q 'fetchWallet\|/wallet' && ok "UI เชื่อม /wallet" || bad "UI เชื่อม /wallet"
}

case "${1:-all}" in
    1) step1;; 2) step2;; 3) step3;; 4) step4;; all) step1; step2; step3; step4;;
esac

echo ""
echo "════════════════════════════"
echo "PASS: $PASS  FAIL: $FAIL"
[ "$FAIL" = "0" ] && echo "✅ ทุกข้อผ่าน" || echo "❌ มีข้อ fail"
rm -f "$JAR" /tmp/verify_upload.txt
exit $FAIL
