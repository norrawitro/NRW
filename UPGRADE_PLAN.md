# Nora-Web: Mock → Real Upgrade Plan

Backup ก่อนทำ: git tag `backup-before-web-edit-20260914_221805` (commit 7cfec07)

## สถานะก่อนทำ

| View | สถานะ |
|---|---|
| 📰 ข่าวสาร | ✅ จริงแล้ว (API + PostgreSQL: posts/post_likes/post_comments) |
| 💳 กระเป๋าเงิน | ❌ mock — `State.wallet` ใน JS, topup/withdraw คำนวณในหน้า |
| ☁️ คลาวด์ | ❌ mock — `State.cloudItems` ใน JS, upload = เติมชื่อไฟล์เฉยๆ |
| 🤖 AI | ❌ mock — `aiReplyFor()` keyword matching ใน JS |
| 🏠 Home | ❌ การ์ดพื้นที่ = mock wallet, hero slides hardcode |

## ลำดับงาน (ทำทีละอย่าง, verify ก่อนไปต่อ)

### Step 1: กระเป๋าเงินจริง
- **DB**: table `wallets` (user_id PK/FK, balance, token, created_at, updated_at) + `wallet_transactions` (id, user_id, type[topup/withdraw/token], amount, desc, created_at)
- **API** (`app/routers/wallet.py`, prefix `/wallet`):
  - `GET /wallet` → {balance, token, tx:[...]} (login required)
  - `POST /wallet/tx` → {type, amount, desc} (login required, atomic update)
  - `GET /wallet/summary` → public-safe สำหรับ AI context (balance/token)
- **Frontend**: `DataLayer.getWallet/addTransaction` → เรียก API จิง, `updateWalletChips` ดึงจาก API ตอนโหลด
- **Verify**: `bash verify.sh 1` — topup 100 → balance เพิ่มใน DB + UI, withdraw เกินยอด → reject

### Step 2: คลาวด์จริง
- **DB**: table `cloud_folders` (id, user_id, parent_id, name, created_at) + `cloud_files` (id, user_id, folder_id, name, size, path, created_at)
- **API** (`app/routers/cloud.py`, prefix `/cloud`):
  - `GET /cloud` → {storage:{used,total}, path, items:[...]}
  - `POST /cloud/folders` → สร้างโฟลเดอร์
  - `POST /cloud/upload` → upload ไฟล์จริง (multipart, เก็บใน `uploads/<user_id>/`)
  - `GET /cloud/download/{file_id}` → ส่งไฟล์
  - `DELETE /cloud/items/{id}` → ลบ (โฟลเดอร์+ไฟล์ในนั้น)
- **Frontend**: `DataLayer.getCloudItems/addCloudFolder/addCloudFile/deleteCloudItem` → API จิง, upload ใช้ `<input type=file>` จริง
- **Verify**: `bash verify.sh 2` — upload ไฟล์จริง → download ได้, สร้างโฟลเดอร์ → เห็นใน UI, ลบ → หาย

### Step 3: AI จริง
- **API** (`app/routers/ai.py`, prefix `/ai`):
  - `POST /ai/chat` → {message} → เรียก Ollama (localhost:11434, qwen3:4b) พร้อม system prompt + context จริง (ยอด wallet, storage used, ข่าวล่าสุด 3 ข้อ)
  - Fallback: ถ้า Ollama down → ตอบว่า AI ยังไม่พร้อม (ไม่ fake คำตอบ)
- **Frontend**: `sendAIMessage` → POST /ai/chat, ลบ `aiReplyFor()`
- **Verify**: `bash verify.sh 3` — ถาม "เช็คยอดเงินฉัน" → คำตอบมีจำนวนเงินจริงจาก DB

### Step 4: Home/Hero polish + ปิดงาน
- การ์ด "พื้นที่ของฉัน" = ยอด wallet จริง (Step 1 ทำให้ได้เอง)
- Hero slides: เปลี่ยนจาก hardcode → ดึงประกาศ pinned/ล่าสุดจาก DB
- ทดสอบครบทุก view, git commit + tag

## กฎ
- ทุก step: backup ไฟล์ที่แก้ก่อน (git commit = restore point)
- ทุก step: `bash verify.sh <n>` ผ่านก่อนไป step ถัดไป
- ถ้า step ไหน fail → หยุด รายงาน (ไม่ retry เอง)
