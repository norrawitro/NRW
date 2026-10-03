# แผนที่ไฟล์หน้าเว็บ Nora-Web

หน้าเว็บหลัก (`/`) แยกเป็นไฟล์เล็ก ๆ เพื่อให้แก้ทีละไฟล์ได้ — **อ่านเฉพาะไฟล์ที่เกี่ยวข้อง ไม่ต้องอ่านทั้งหมด**

แก้ไฟล์แล้ว refresh หน้าเว็บได้เลย ไม่ต้อง restart server (ยกเว้นไฟล์ `.py`)

## HTML
| ไฟล์ | มีอะไร |
|------|--------|
| `app/templates/wkw.html` | โครงหน้าเว็บ (header, เมนู, ทุก view) — ไม่มี CSS/JS ในไฟล์ |

## CSS — `app/static/css/`
| ไฟล์ | มีอะไร |
|------|--------|
| `base.css` | สี/ธีม (`:root`, dark mode), ส่วนหัว, เมนูด้านข้าง, เลย์เอาต์ |
| `home-news.css` | หน้าแรก (hero, การ์ด, ไอคอนระบบ), ข่าวสาร (โพสต์, ความเห็น) |
| `views.css` | คลาวด์, กระเป๋าเงิน, AI, drawer, footer, responsive (มือถือ) |
| `modules.css` | ส่วนประกอบของระบบใหม่ (การ์ด, ตาราง, ฟอร์ม, แท็บ, กราฟแท่ง), ช่องค้นหา, toast |
| `modules2.css` | แชท, คอร์ส, บอร์ดงาน, เกม, วิดีโอ, โฆษณา, IoT, สุขภาพ, ช่องแนบรูป/แกลเลอรี (`.ui-*`) |

## JavaScript — `app/static/js/` (โหลดตามลำดับนี้ ใช้ตัวแปรร่วมกัน)
| ไฟล์ | มีอะไร | ถ้าจะแก้เรื่อง… |
|------|--------|----------------|
| `data.js` | รายชื่อ 22 ระบบ (`MODULES`), ช่วงพัฒนา (`PHASES`), `State`, `DataLayer` | เพิ่ม/เปลี่ยนชื่อระบบ |
| `core.js` | `api()`, `toast()`, `baht()`, `registerModule()`, `isLive()`, ผู้ใช้ที่ login (`State.me`), ธีมมืด | ตัวช่วยกลาง |
| `ui_kit.js` | ชิ้นส่วนร่วมรูปแบบเดียวกัน: `imagePicker(id)` + `pickedImages(id)` (แนบรูป ≤5 → `POST /media/images`), `gallery(images)`, `itemCard({...})` การ์ดรูป+ข้อความ+ราคา+ปุ่ม | ช่องแนบรูป / หน้าตาการ์ดทุกระบบ |
| `api.js` | `fetchWallet()`, `fetchCloud()`, `fmtSize()` | การโหลดข้อมูลกระเป๋าเงิน/คลาวด์ |
| `home.js` | เมนูด้านข้าง, ไอคอนระบบ, hero slides | หน้าแรก, เมนู |
| `news.js` | โพสต์, feed, ถูกใจ, ความเห็น, โพสต์ใหม่, `esc()` | ข่าวสาร |
| `cloud.js` | แถบพื้นที่, breadcrumb, ตารางไฟล์ | คลาวด์ (หน้าตา) |
| `wallet.js` | ยอดเงิน, ตารางธุรกรรม | กระเป๋าเงิน (หน้าตา) |
| `ai.js` | ข้อความแชท, `sendAIMessage()` | ศูนย์ AI |
| `router.js` | `showView()` สลับหน้า, drawer ระบบที่ยังไม่เปิด | การเปลี่ยนหน้า |
| `events.js` | ผูกปุ่ม/คลิกทั้งหมด | ปุ่มกดแล้วไม่ทำงาน |
| `main.js` | เริ่มทำงานตอนเปิดหน้า | ลำดับการโหลด |

## ระบบที่เปิดเพิ่ม — `app/static/js/modules/` (1 ไฟล์ = 1 ระบบ)
| ไฟล์ | ระบบ | API ฝั่ง server |
|------|------|----------------|
| `info.js` | หน้าเกี่ยวกับ/คู่มือ/นโยบาย/เงื่อนไข/ติดต่อ (ลิงก์ท้ายเว็บ) | — |
| `search.js` | ช่องค้นหาด้านบน | `/shop/products` |
| `shop.js` | 🛒 ขายออนไลน์: สินค้าทั้งหมด / ร้านของฉัน / ➕ ลงสินค้า (สมาชิกทุกคนขายได้) | `app/routers/shop.py` |
| `logistics.js` | 🚚 คลังสินค้า/ขนส่ง (ติดตามพัสดุ, คิวจัดส่ง, สต็อก) | `app/routers/logistics.py` |
| `market.js` | ♻️ มือสอง/เช่า | `app/routers/market.py` |
| `token.js` | 🪙 โทเคน (โอน, แลกเป็นเงิน) | `app/routers/token.py` |
| `analytics.js` | 📊 แดชบอร์ดวิเคราะห์ (+ ฟังก์ชันกราฟ `bars()` / `stat()` ที่ระบบอื่นใช้ด้วย) | `app/routers/analytics.py` |
| `chat.js` | 💬 แชทเรียลไทม์ (ห้องรวม + DM, ดึงข้อความทุก 3 วิ) | `app/routers/chat.py` |
| `course.js` | 🎓 คอร์สเรียนแบบอินเตอร์แอกทีฟ (ซื้อคอร์ส, เนื้อหา + คำถามปรนัย/อัตนัย, ตัวสร้างคำถาม) | `app/routers/course.py` |
| `jobs.js` | 💼 ตลาดงาน/ฟรีแลนซ์ (พักเงิน) | `app/routers/jobs.py` |
| `workspace.js` | 🧩 พื้นที่ทำงานร่วมกัน (บอร์ดงาน + โน้ต) | `app/routers/workspace.py` |
| `ads.js` | 📢 โฆษณา (+ `loadHomeAd()` โฆษณาบนหน้าแรก) | `app/routers/ads.py` |
| `video.js` | 🎥 วิดีโอความรู้ | `app/routers/video.py` |
| `games.js` | 🎮 เกม (จับคู่ภาพ, คิดเลขเร็ว) + ตารางอันดับ | `app/routers/games.py` |
| `events.js` | 🎫 กิจกรรม/ตั๋ว/เช็คอิน | `app/routers/events.py` |
| `creator.js` | ⭐ ครีเอเตอร์/สมาชิก VIP | `app/routers/creator.py` |
| `iot.js` | 📡 อุปกรณ์ IoT ของสมาชิก | `app/routers/iot_devices.py` |
| `health.js` | 🏃 สุขภาพ: บันทึก + รูปหลักฐาน (รออนุมัติ) + โค้ช AI | `app/routers/health.py` |

**เปิดระบบใหม่:** สร้าง `js/modules/<id>.js` → เรียก `registerModule('<id>', {sub:'...', render(el){...}})`
→ ใส่ `<script>` ใน `wkw.html` (ก่อน `main.js`) — ระบบจะปลดล็อกในเมนูเองอัตโนมัติ (`id` ต้องตรงกับใน `MODULES`)

## หน้าอื่น
| ไฟล์ | หน้า |
|------|------|
| `app/templates/manage.html` + `app/static/js/manage.js` + `manage_content.js` | `/manage` แผงผู้ดูแล: 🛡️ อนุมัติเนื้อหา, คำขอเงิน, สมาชิก, สินค้า |
| `app/templates/members/profile.html` + `app/static/js/profile.js` | `/members/profile` โปรไฟล์: แก้ข้อมูล, เปลี่ยนรหัส, สถิติ, โพสต์ของฉัน |

## API ฝั่ง server — `app/routers/`
`news.py` ข่าวสาร · `wallet.py` กระเป๋าเงิน · `cloud.py` คลาวด์ · `ai.py` AI (Ollama) · `members.py` สมาชิก ·
`manage.py` แผงผู้ดูแล · `shop.py` · `logistics.py` · `market.py` · `token.py` · `analytics.py` ·
`chat.py` · `course.py` · `jobs.py` · `workspace.py` · `ads.py` · `video.py` · `games.py` · `events.py` · `creator.py` · `iot_devices.py` · `health.py`
ตาราง: `app/models/shop.py`, `market.py` (ช่วง 2) · `work.py` (ช่วง 3) · `community.py` (ช่วง 4)

ตัวช่วยฝั่ง server: `app/deps.py` (ผู้ใช้ที่ login / admin) · `app/services/wallet_ops.py` (เพิ่ม/หักเงินและโทเคน — **ทุกระบบที่มีการจ่ายเงินต้องใช้ตัวนี้**)

## ระบบอนุมัติเนื้อหา
เนื้อหาที่สมาชิกลง (โพสต์, สินค้า, ประกาศมือสอง, คอร์ส, งาน, โฆษณา, วิดีโอ, กิจกรรม, โพสต์ครีเอเตอร์, หลักฐานออกกำลังกาย)
ซ่อนจนผู้ดูแลอนุมัติที่ `/manage` → แท็บ 🛡️ — โค้ดกลางอยู่ที่ `app/services/moderation.py` (`submit`, `hidden_ids`, `badge`, `ensure_visible`)
หน้าเว็บแสดงป้ายให้เจ้าของด้วย `modBadge()` ใน `core.js` · ปิดทั้งระบบได้ด้วย `MODERATION=off` ใน `.env`

## กฎสำคัญ
- เงิน/โทเคน: ใช้ `move_money()` / `move_tokens()` เท่านั้น (ล็อกแถว + กันยอดติดลบ + บันทึกประวัติ) แล้ว `db.commit()` ครั้งเดียวตอนจบ
- ทดสอบหลังแก้: `python tests/smoke_phase2.py`, `smoke_phase34.py`, `smoke_seller.py`, `smoke_moderation.py` (ใช้ฐานข้อมูลชั่วคราว ไม่แตะข้อมูลจริง) และ `bash verify.sh all`
- รีสตาร์ทหลังแก้ไฟล์ `.py`: `bash restart.sh` (ไฟล์ HTML/CSS/JS แค่ refresh หน้าเว็บ)
- ลิงก์ที่ผู้ใช้ใส่ (เช่นโฆษณา) ต้องผ่าน `safe_link()` ใน `app/services/helpers.py` — กัน `javascript:`
- ข้อความที่ผู้ใช้พิมพ์ (โพสต์, ชื่อไฟล์, ข้อความ AI) ต้องผ่าน `esc()` ก่อนใส่ใน `innerHTML` เสมอ — กันโดนแฮ็ก (XSS)
- โฟลเดอร์กับไฟล์ในคลาวด์มี id ซ้ำกันได้ (คนละตาราง) — ส่ง `type` ไปด้วยเสมอเมื่อลบ
- ไฟล์ JS ใช้ตัวแปรร่วมกัน ถ้าเพิ่มไฟล์ใหม่ต้องใส่ `<script>` ใน `wkw.html` ให้ถูกลำดับ

## รูปแบบเดียวกัน (ลงรูป + ข้อความ → โพสต์ขาย → กดซื้อ)
ระบบที่สมาชิกลงเนื้อหา ใช้วิธีแนบรูปเดียวกันหมด:
- หน้าเว็บ: ใส่ `${imagePicker('xx')}` ในฟอร์ม แล้วส่ง `images: pickedImages('xx')` ไปกับ body; แสดงด้วย `gallery(item.images)` หรือ `itemCard({...})`
- เซิร์ฟเวอร์: body มี `images: list[str]` → `set_images(db, "<kind>", id, body.images)`; ตอนแสดง `images_map(db, "<kind>", ids)` (`app/services/media.py`)
- ใช้แล้วใน: มือสอง/เช่า (`listing`), ประกาศซื้อ (`wanted`, ข้อเสนอ `wanted_offer`), ร้านค้า (`product`), คอร์ส (`course`), กิจกรรม (`event`), งาน (`job`), ครีเอเตอร์ (`creator`)
- `modules/wanted.js` — ประกาศซื้อ · `modules/token.js` — มีตลาดประกาศซื้อ/ขายโทเคนด้านล่าง

## ข้อความส่วนตัว (DM)
- `modules/dm.js` — กล่องข้อความ (ซ้าย) + บทสนทนา (ขวา), ค้นหาสมาชิก, แนบรูป, ดึงข้อความใหม่ทุก 3 วินาที; มือถือแสดงทีละฝั่ง
- เปิดคุยจากระบบไหนก็ได้: ใส่ `${dmButton(username, '💬 ทักผู้ขาย')}` ในการ์ด (ui_kit.js) หรือเรียก `openDm('username')`
- ตัวเลขยังไม่อ่าน: ปุ่ม ✉️ ที่หัวเว็บ + เมนูซ้าย — `refreshBadges()` ใน core.js (ทุก 30 วินาที, รวมตัวนับ 🛡️ ของผู้ดูแล)
- API ต้องส่ง `seller_username` / `buyer_username` มาด้วยถ้าจะมีปุ่มทัก (ตอนนี้มีใน มือสอง, ประกาศซื้อ, ร้านค้า)
