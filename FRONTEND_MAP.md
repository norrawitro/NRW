# แผนที่ไฟล์หน้าเว็บ Nora-Web

หน้าเว็บหลัก (`/`) แยกเป็นไฟล์เล็ก ๆ เพื่อให้แก้ทีละไฟล์ได้ — **อ่านเฉพาะไฟล์ที่เกี่ยวข้อง ไม่ต้องอ่านทั้งหมด**

แก้ไฟล์แล้ว refresh หน้าเว็บได้เลย ไม่ต้อง restart server (ยกเว้นไฟล์ `.py`)

## HTML
| ไฟล์ | มีอะไร |
|------|--------|
| `app/templates/nora-web.html` | โครงหน้าเว็บ (header, เมนู, ทุก view) — ไม่มี CSS/JS ในไฟล์ |

## CSS — `app/static/css/`
| ไฟล์ | มีอะไร |
|------|--------|
| `base.css` | สี/ธีม (`:root`, dark mode), ส่วนหัว, เมนูด้านข้าง, เลย์เอาต์ |
| `home-news.css` | หน้าแรก (hero, การ์ด, ไอคอนระบบ), ข่าวสาร (โพสต์, ความเห็น) |
| `views.css` | คลาวด์, กระเป๋าเงิน, AI, drawer, footer, responsive (มือถือ) |
| `modules.css` | ส่วนประกอบของระบบใหม่ (การ์ด, ตาราง, ฟอร์ม, แท็บ, กราฟแท่ง), ช่องค้นหา, toast |

## JavaScript — `app/static/js/` (โหลดตามลำดับนี้ ใช้ตัวแปรร่วมกัน)
| ไฟล์ | มีอะไร | ถ้าจะแก้เรื่อง… |
|------|--------|----------------|
| `data.js` | รายชื่อ 20 ระบบ (`MODULES`), ช่วงพัฒนา (`PHASES`), `State`, `DataLayer` | เพิ่ม/เปลี่ยนชื่อระบบ |
| `core.js` | `api()`, `toast()`, `baht()`, `registerModule()`, `isLive()`, ผู้ใช้ที่ login (`State.me`), ธีมมืด | ตัวช่วยกลาง |
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
| `shop.js` | 🛒 ขายออนไลน์ (ตะกร้า, สั่งซื้อ) | `app/routers/shop.py` |
| `logistics.js` | 🚚 คลังสินค้า/ขนส่ง (ติดตามพัสดุ, คิวจัดส่ง, สต็อก) | `app/routers/logistics.py` |
| `market.js` | ♻️ มือสอง/เช่า | `app/routers/market.py` |
| `token.js` | 🪙 โทเคน (โอน, แลกเป็นเงิน) | `app/routers/token.py` |
| `analytics.js` | 📊 แดชบอร์ดวิเคราะห์ | `app/routers/analytics.py` |

**เปิดระบบใหม่:** สร้าง `js/modules/<id>.js` → เรียก `registerModule('<id>', {sub:'...', render(el){...}})`
→ ใส่ `<script>` ใน `nora-web.html` (ก่อน `main.js`) — ระบบจะปลดล็อกในเมนูเองอัตโนมัติ (`id` ต้องตรงกับใน `MODULES`)

## หน้าอื่น
| ไฟล์ | หน้า |
|------|------|
| `app/templates/manage.html` + `app/static/js/manage.js` | `/manage` แผงผู้ดูแล: อนุมัติคำขอเงิน, สมาชิก, สินค้า |
| `app/templates/members/profile.html` + `app/static/js/profile.js` | `/members/profile` โปรไฟล์: แก้ข้อมูล, เปลี่ยนรหัส, สถิติ, โพสต์ของฉัน |

## API ฝั่ง server — `app/routers/`
`news.py` ข่าวสาร · `wallet.py` กระเป๋าเงิน · `cloud.py` คลาวด์ · `ai.py` AI (Ollama) · `members.py` สมาชิก ·
`manage.py` แผงผู้ดูแล · `shop.py` · `logistics.py` · `market.py` · `token.py` · `analytics.py`

ตัวช่วยฝั่ง server: `app/deps.py` (ผู้ใช้ที่ login / admin) · `app/services/wallet_ops.py` (เพิ่ม/หักเงินและโทเคน — **ทุกระบบที่มีการจ่ายเงินต้องใช้ตัวนี้**)

## กฎสำคัญ
- เงิน/โทเคน: ใช้ `move_money()` / `move_tokens()` เท่านั้น (ล็อกแถว + กันยอดติดลบ + บันทึกประวัติ) แล้ว `db.commit()` ครั้งเดียวตอนจบ
- ทดสอบหลังแก้: `python tests/smoke_phase2.py` (ใช้ฐานข้อมูลชั่วคราว ไม่แตะข้อมูลจริง) และ `bash verify.sh all`
- ข้อความที่ผู้ใช้พิมพ์ (โพสต์, ชื่อไฟล์, ข้อความ AI) ต้องผ่าน `esc()` ก่อนใส่ใน `innerHTML` เสมอ — กันโดนแฮ็ก (XSS)
- โฟลเดอร์กับไฟล์ในคลาวด์มี id ซ้ำกันได้ (คนละตาราง) — ส่ง `type` ไปด้วยเสมอเมื่อลบ
- ไฟล์ JS ใช้ตัวแปรร่วมกัน ถ้าเพิ่มไฟล์ใหม่ต้องใส่ `<script>` ใน `nora-web.html` ให้ถูกลำดับ
