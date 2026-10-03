/* core.js — ตัวช่วยที่ทุกระบบใช้ร่วมกัน: api(), toast(), baht(), ผู้ใช้ที่ login (State.me), ระบบ module
   วิธีเพิ่มระบบใหม่: สร้างไฟล์ใน js/modules/ แล้วเรียก registerModule('id', {render(el){...}})
   ระบบที่ register แล้วจะปลดล็อกในเมนูอัตโนมัติ */

const MODULE_VIEWS = {};
function registerModule(id, def){ MODULE_VIEWS[id] = def; }
function isLive(m){ return m.phase===1 || !!MODULE_VIEWS[m.id]; }

/** เรียก API แบบ JSON → คืน data หรือ null (แจ้ง error ให้แล้ว) */
async function api(url, opts={}){
  const o = {credentials:'same-origin', ...opts};
  if(o.json !== undefined){ o.method = o.method || 'POST'; o.headers = {'Content-Type':'application/json'}; o.body = JSON.stringify(o.json); delete o.json; }
  let r;
  try{ r = await fetch(url, o); }catch(e){ toast('เชื่อมต่อเซิร์ฟเวอร์ไม่ได้'); return null; }
  let data = null;
  try{ data = await r.json(); }catch(e){}
  if(r.status===401){ toast('กรุณาเข้าสู่ระบบก่อน'); return null; }
  if(r.status===422){ toast('ข้อมูลไม่ครบหรือสั้นเกินไป กรุณาตรวจสอบอีกครั้ง'); return null; }
  if(!r.ok){ toast((data && typeof data.detail==='string') ? data.detail : 'เกิดข้อผิดพลาด'); return null; }
  return data;
}

const baht = n => '฿' + Number(n||0).toLocaleString('th-TH', {maximumFractionDigits:2});

let _toastTimer;
function toast(msg){
  const t = document.getElementById('toast');
  t.textContent = msg; t.classList.add('on');
  clearTimeout(_toastTimer); _toastTimer = setTimeout(()=>t.classList.remove('on'), 2800);
}

/** กล่อง "กรุณาเข้าสู่ระบบ" สำหรับระบบที่ต้อง login */
function loginGate(el, what){
  el.innerHTML = `<div class="m-card m-center"><div style="font-size:40px">🔒</div>
    <h3>เข้าสู่ระบบเพื่อใช้${esc(what)}</h3><p class="m-muted">ข้อมูลของแต่ละบัญชีแยกกัน</p>
    <a href="/members/login" class="btn-primary">🔑 เข้าสู่ระบบ</a></div>`;
}

/* ── ผู้ใช้ที่ login อยู่ ─────────────────────────────────────── */
State.me = null;
async function loadMe(){
  try{
    const r = await fetch('/members/me', {credentials:'same-origin'});
    const d = await r.json();
    State.me = d.logged_in ? d : null;
  }catch(e){ State.me = null; }
  renderMe();
}
function renderMe(){
  const me = State.me, av = document.getElementById('userAvatar');
  av.textContent = me ? me.initial : '👤';
  av.title = me ? `${me.full_name} (@${me.username}) — ดูโปรไฟล์` : 'เข้าสู่ระบบ';
  av.onclick = ()=>{ window.location.href = me ? '/members/profile' : '/members/login'; };
  const box = document.getElementById('memberBox');
  if(me && box){
    box.innerHTML = `<div class="launcher-head"><h3>สวัสดี, ${esc(me.full_name)}</h3></div>
      <p style="font-size:14px;color:var(--ink-soft);">@${esc(me.username)}${me.is_admin?' · ⚡ ผู้ดูแลระบบ':''}</p>
      <div style="margin-top:10px;display:flex;gap:8px;flex-wrap:wrap;align-items:center;">
        <a href="/members/profile" class="btn-primary" style="padding:7px 14px;font-size:13px;">👤 โปรไฟล์</a>
        ${me.is_admin?'<a href="/manage" class="btn-ghost" style="padding:7px 14px;font-size:13px;">🛠️ แผงผู้ดูแล</a>':''}
        <a href="/members/logout" style="color:var(--ink-soft);font-size:13px;font-weight:600;">ออกจากระบบ</a></div>`;
  }
  renderSidebar();
}

/* ── ธีมมืด: จำไว้ในเบราว์เซอร์ (ใช้ key เดียวกับหน้าโปรไฟล์) ───── */
try{ State.dark = JSON.parse(localStorage.getItem('nrw_dark')||'false'); }catch(e){}
function applyTheme(){
  document.documentElement.setAttribute('data-theme', State.dark?'dark':'');
  const b = document.getElementById('themeBtn'); if(b) b.textContent = State.dark?'☀️':'🌙';
}
