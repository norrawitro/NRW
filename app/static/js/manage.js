/* manage.js — แผงผู้ดูแล (/manage): อนุมัติคำขอเติม/ถอนเงิน, จัดการสมาชิก, เพิ่ม/แก้สินค้า
   API: /manage/api/* (ต้องเป็น admin) */
const $ = id => document.getElementById(id);
const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const baht = n => '฿' + Number(n||0).toLocaleString('th-TH', {maximumFractionDigits:2});
let _t; function toast(m){ const t=$('toast'); t.textContent=m; t.classList.add('on'); clearTimeout(_t); _t=setTimeout(()=>t.classList.remove('on'),2800); }
try{ if(JSON.parse(localStorage.getItem('nrw_dark')||'false')) document.documentElement.setAttribute('data-theme','dark'); }catch(e){}

async function api(url, opts={}){
  if(opts.json !== undefined){ opts.method = opts.method||'POST'; opts.headers = {'Content-Type':'application/json'}; opts.body = JSON.stringify(opts.json); delete opts.json; }
  const r = await fetch(url, {credentials:'same-origin', ...opts});
  let d = null; try{ d = await r.json(); }catch(e){}
  if(!r.ok){ toast((d && typeof d.detail==='string') ? d.detail : 'เกิดข้อผิดพลาด'); return null; }
  return d;
}

const Tabs = {
  async requests(){
    $('body').innerHTML = `<div class="m-card"><select id="reqFilter" class="m-input" style="max-width:200px">
      <option value="pending">รออนุมัติ</option><option value="approved">อนุมัติแล้ว</option><option value="rejected">ปฏิเสธแล้ว</option><option value="all">ทั้งหมด</option></select>
      <div id="reqTable"></div><p class="m-muted">อนุมัติเติม = เพิ่มยอดทันที (ตรวจสลิปก่อน) · อนุมัติถอน = ยืนยันว่าโอนเงินจริงแล้ว · ปฏิเสธถอน = คืนยอดให้สมาชิก</p></div>`;
    $('reqFilter').onchange = ()=>this.loadRequests();
    this.loadRequests();
  },
  async loadRequests(){
    const d = await api('/manage/api/wallet-requests?status=' + $('reqFilter').value); if(!d) return;
    $('reqTable').innerHTML = d.requests.length ? `<table class="m-table"><tr><th>#</th><th>สมาชิก</th><th>ประเภท</th><th>จำนวน</th><th>หมายเหตุ</th><th>วันที่</th><th>สถานะ</th><th></th></tr>
      ${d.requests.map(r=>`<tr><td>${r.id}</td><td>${esc(r.full_name)}<br><small class="m-muted">@${esc(r.username)}</small></td>
        <td>${r.type==='topup'?'➕ เติม':'➖ ถอน'}</td><td><b>${baht(r.amount)}</b></td><td>${esc(r.desc)}</td><td>${esc(r.date)}</td>
        <td><span class="badge st-${r.status}">${esc(r.status_label)}</span>${r.decided_by?`<br><small class="m-muted">โดย ${esc(r.decided_by)}</small>`:''}</td>
        <td>${r.status==='pending'?`<button class="btn-primary m-sm" data-req="${r.id}" data-act="approve">อนุมัติ</button> <button class="btn-ghost m-sm" data-req="${r.id}" data-act="reject">ปฏิเสธ</button>`:''}</td></tr>`).join('')}</table>`
      : '<p class="m-muted" style="padding:16px 0">ไม่มีคำขอ</p>';
  },
  async users(){
    const d = await api('/manage/api/users'); if(!d) return;
    $('body').innerHTML = `<div class="m-card"><table class="m-table"><tr><th>#</th><th>สมาชิก</th><th>ยอดเงิน</th><th>โทเคน</th><th>สถานะ</th><th></th></tr>
      ${d.users.map(u=>`<tr><td>${u.id}</td><td>${esc(u.full_name)}<br><small class="m-muted">@${esc(u.username)} · ${esc(u.email)}${u.is_admin?' · ⚡ admin':''}</small></td>
        <td>${baht(u.balance)}</td><td>${u.token.toLocaleString()}</td><td>${u.is_active?'✅ ใช้งานได้':'⛔ ระงับ'}</td>
        <td><button class="btn-ghost m-sm" data-adjust="${u.id}">± ปรับยอด</button> <button class="btn-ghost m-sm" data-toggle="${u.id}" data-field="is_active">${u.is_active?'ระงับ':'เปิดใช้'}</button>
        <button class="btn-ghost m-sm" data-toggle="${u.id}" data-field="is_admin">${u.is_admin?'ถอด admin':'ตั้ง admin'}</button></td></tr>`).join('')}</table></div>`;
  },
  async products(){
    const d = await api('/manage/api/products'); if(!d) return;
    this.productList = d.products;
    $('body').innerHTML = `<div class="m-split"><div class="m-card"><table class="m-table"><tr><th>#</th><th>สินค้า</th><th>ราคา</th><th>สต็อก</th><th></th></tr>
      ${d.products.map(p=>`<tr><td>${p.id}</td><td>${esc(p.name)}${p.is_active?'':' <small class="m-muted">(ปิดขาย)</small>'}</td><td>${baht(p.price)}</td><td>${p.stock}</td>
        <td><button class="btn-ghost m-sm" data-edit="${p.id}">แก้ไข</button></td></tr>`).join('') || '<tr><td colspan="5" class="m-muted">ยังไม่มีสินค้า</td></tr>'}</table></div>
      <div class="m-card m-form"><h3 id="pfTitle">➕ เพิ่มสินค้า</h3><input type="hidden" id="pfId">
        <label>ชื่อ<input id="pfName" class="m-input" maxlength="200"></label><label>รายละเอียด<textarea id="pfDesc" class="m-input" rows="3"></textarea></label>
        <label>ราคา (บาท)<input id="pfPrice" class="m-input" type="number" min="0" step="0.01"></label><label>สต็อก<input id="pfStock" class="m-input" type="number" min="0"></label>
        <label>ลิงก์รูป (ไม่บังคับ)<input id="pfImg" class="m-input" maxlength="500"></label><label><input type="checkbox" id="pfActive" checked> เปิดขาย</label>
        <button class="btn-primary m-full" id="pfSave">บันทึก</button> <button class="btn-ghost m-full" id="pfNew">ล้างฟอร์ม</button></div></div>`;
  },
  fillProduct(p){
    $('pfTitle').textContent = p ? `✏️ แก้ไข #${p.id}` : '➕ เพิ่มสินค้า';
    $('pfId').value = p ? p.id : ''; $('pfName').value = p ? p.name : ''; $('pfDesc').value = p ? p.description : '';
    $('pfPrice').value = p ? p.price : ''; $('pfStock').value = p ? p.stock : ''; $('pfImg').value = p ? p.image_url : ''; $('pfActive').checked = p ? p.is_active : true;
  },
  async saveProduct(){
    const id = $('pfId').value;
    const body = {name:$('pfName').value.trim(), description:$('pfDesc').value.trim(), price:+$('pfPrice').value||0,
                  stock:parseInt($('pfStock').value,10)||0, image_url:$('pfImg').value.trim(), is_active:$('pfActive').checked};
    if(!body.name){ toast('กรุณาใส่ชื่อสินค้า'); return; }
    if(await api('/manage/api/products' + (id?'/'+id:''), {method:id?'PUT':'POST', json:body})){ toast('บันทึกแล้ว'); this.products(); }
  },
};

document.addEventListener('click', async e=>{
  const t = e.target;
  const tab = t.closest('[data-tab]');
  if(tab){ document.querySelectorAll('.m-tab').forEach(x=>x.classList.toggle('on', x===tab)); Tabs[tab.dataset.tab](); return; }
  if(t.dataset.req && confirm(`${t.dataset.act==='approve'?'อนุมัติ':'ปฏิเสธ'}คำขอ #${t.dataset.req}?`)){
    if(await api(`/manage/api/wallet-requests/${t.dataset.req}/${t.dataset.act}`, {method:'POST'})){ toast('เรียบร้อย'); Tabs.loadRequests(); }
  }
  if(t.dataset.toggle && confirm('ยืนยันการเปลี่ยนสถานะ?')){
    if(await api(`/manage/api/users/${t.dataset.toggle}/toggle/${t.dataset.field}`, {method:'POST'})) Tabs.users();
  }
  if(t.dataset.adjust){
    const amount = parseFloat(prompt('ปรับยอดเงิน (บาท) เช่น 100 หรือ -50 (เว้นว่าง = ไม่ปรับ)')||'0') || 0;
    const token = parseInt(prompt('ปรับโทเคน เช่น 10 หรือ -5 (เว้นว่าง = ไม่ปรับ)')||'0', 10) || 0;
    if(!amount && !token) return;
    const note = prompt('หมายเหตุ (ไม่บังคับ)') || '';
    if(await api(`/manage/api/users/${t.dataset.adjust}/adjust`, {json:{amount, token, note}})){ toast('ปรับยอดแล้ว'); Tabs.users(); }
  }
  if(t.dataset.edit) Tabs.fillProduct(Tabs.productList.find(p=>p.id==t.dataset.edit));
  if(t.id==='pfSave') Tabs.saveProduct();
  if(t.id==='pfNew') Tabs.fillProduct(null);
});
Tabs.requests();
