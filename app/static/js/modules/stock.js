/* modules/stock.js — หน้าจัดการสต็อก (แท็บ 🏬 สต็อกสินค้า ในคลังสินค้า/ขนส่ง) — ใช้ผ่าน StockUI.render(box)
   ผู้ขาย: สินค้าร้านตัวเอง · ผู้ดูแล: เลือกดู ร้านฉัน / สินค้าแพลตฟอร์ม / ทั้งหมด
   API: GET /stock?scope= · POST /stock/{id}/move {kind:in|out|count,qty,note} · PUT /stock/{id}/settings {low_at}
        GET /stock/{id}/history · GET /stock/moves?scope= · GET /stock/export.csv?scope= */
const StockUI = {
  scope: 'mine', filter: 'all',
  async render(box){
    this.box = box;
    const d = await api('/stock?scope='+this.scope); if(!d) return;
    this.data = d;
    const s = d.summary, F = (k,t)=>`<button class="m-tab ${this.filter===k?'on':''}" data-sfilter="${k}">${t}</button>`;
    box.innerHTML = `
      ${d.is_admin ? `<div class="m-row" style="justify-content:flex-start;gap:8px;margin-bottom:10px"><small class="m-muted">ดูสต็อกของ</small>
        <select id="stScope" class="m-input" style="width:auto">${[['mine','ร้านของฉัน'],['platform','สินค้าแพลตฟอร์ม'],['all','ทั้งระบบ']].map(([v,t])=>`<option value="${v}" ${this.scope===v?'selected':''}>${t}</option>`).join('')}</select></div>` : ''}
      <div class="st-cards">
        <div class="m-card st-card"><small>รายการสินค้า</small><b>${s.skus.toLocaleString()}</b></div>
        <div class="m-card st-card"><small>จำนวนชิ้นรวม</small><b>${s.units.toLocaleString()}</b></div>
        <div class="m-card st-card"><small>มูลค่าสต็อก</small><b>${baht(s.value)}</b></div>
        <div class="m-card st-card st-warn"><small>⚠️ ใกล้หมด</small><b>${s.low}</b></div>
        <div class="m-card st-card st-bad"><small>⛔ หมด</small><b>${s.out}</b></div></div>
      <div class="m-row"><div class="m-tabs" style="margin:0">${F('all','ทั้งหมด')}${F('low','ใกล้หมด')}${F('out','หมด')}</div>
        <span><input id="stFind" class="m-input" style="width:180px" placeholder="🔍 ค้นหาสินค้า" value="${esc(this.q||'')}">
        <a class="btn-ghost m-sm" href="/stock/export.csv?scope=${this.scope}">⬇️ ส่งออก Excel (CSV)</a></span></div>
      <div class="m-card" style="overflow-x:auto"><table class="m-table st-table"><tr><th>สินค้า</th><th>คงเหลือ</th><th>สถานะ</th><th>ขาย 30 วัน</th><th>มูลค่า</th><th></th></tr>
        <tbody id="stRows"></tbody></table></div>
      <div id="stPanel"></div>
      <div class="m-card"><h3>🕘 ความเคลื่อนไหวล่าสุด</h3><div id="stMoves"><p class="m-muted">กำลังโหลด…</p></div></div>`;
    this.drawRows();
    box.onclick = e=>this.click(e);
    document.getElementById('stFind').oninput = e=>{ this.q = e.target.value.trim().toLowerCase(); this.drawRows(); };
    const sc = document.getElementById('stScope'); if(sc) sc.onchange = e=>{ this.scope = e.target.value; this.render(box); };
    this.loadMoves();
  },
  drawRows(){
    const rows = this.data.products.filter(p=>(this.filter==='all' || p.status===this.filter) && (!this.q || p.name.toLowerCase().includes(this.q)));
    const badge = {out:'st-rejected', low:'st-pending', ok:'st-approved'};
    document.getElementById('stRows').innerHTML = rows.length ? rows.map(p=>`<tr class="${p.status!=='ok'?'m-warn':''}">
      <td><div class="st-name">${p.image_url?`<img src="${esc(p.image_url)}" alt="">`:'<span class="st-noimg">📦</span>'}<span>${esc(p.name)}${p.is_active?'':' <small class="m-muted">(ปิดขาย)</small>'}<br><small class="m-muted">${baht(p.price)} · เตือนเมื่อเหลือ ≤ ${p.low_at}</small></span></div></td>
      <td><b class="st-qty">${p.stock.toLocaleString()}</b></td>
      <td><span class="badge ${badge[p.status]}">${esc(p.status_label)}</span>${p.days_left!==null?`<br><small class="m-muted">พอขาย ~${p.days_left} วัน</small>`:''}</td>
      <td>${p.sold_30d}</td><td>${baht(p.value)}</td>
      <td class="st-acts"><button class="btn-primary m-sm" data-sact="in" data-pid="${p.id}">📥 รับเข้า</button>
        <button class="btn-ghost m-sm" data-sact="out" data-pid="${p.id}">📤 เบิก</button>
        <button class="btn-ghost m-sm" data-sact="count" data-pid="${p.id}">🔢 ตรวจนับ</button>
        <button class="btn-ghost m-sm" data-sact="hist" data-pid="${p.id}">🕘 ประวัติ</button></td></tr>`).join('')
      : `<tr><td colspan="6" class="m-muted">${this.data.products.length?'ไม่มีสินค้าตามตัวกรอง':'ยังไม่มีสินค้า — ลงสินค้าได้ที่ ขายออนไลน์ → ➕ ลงสินค้า'}</td></tr>`;
  },
  click(e){
    const f = e.target.closest('[data-sfilter]'); if(f){ this.filter = f.dataset.sfilter; this.box.querySelectorAll('[data-sfilter]').forEach(b=>b.classList.toggle('on', b===f)); return this.drawRows(); }
    const b = e.target.closest('[data-sact]'); if(b) return b.dataset.sact==='hist' ? this.history(+b.dataset.pid) : this.form(b.dataset.sact, +b.dataset.pid);
    if(e.target.id==='stSave') return this.save();
    if(e.target.id==='stLowSave') return this.saveLow();
    if(e.target.id==='stClose') document.getElementById('stPanel').innerHTML = '';
  },
  form(kind, pid){
    const p = this.data.products.find(x=>x.id===pid); this.cur = {kind, pid};
    const T = {in:['📥 รับสินค้าเข้า','จำนวนที่รับเข้า','เช่น ล็อตใหม่จากซัพพลายเออร์'], out:['📤 เบิกออก / ตัดสต็อก','จำนวนที่เบิกออก','เช่น ชำรุด, ใช้เอง, ของแถม'],
               count:['🔢 ตรวจนับสต็อก','จำนวนที่นับได้จริง','เช่น ตรวจนับสิ้นเดือน']}[kind];
    const panel = document.getElementById('stPanel');
    panel.innerHTML = `<div class="m-card m-form st-form"><div class="m-row"><h3>${T[0]} — ${esc(p.name)}</h3><button class="btn-ghost m-sm" id="stClose">✕</button></div>
      <p class="m-muted">คงเหลือตอนนี้ <b>${p.stock}</b> ชิ้น</p>
      <label>${T[1]}<input id="stQty" class="m-input" type="number" min="0" value="${kind==='count'?p.stock:''}"></label>
      <label>หมายเหตุ<input id="stNote" class="m-input" maxlength="200" placeholder="${T[2]}"></label>
      <button class="btn-primary" id="stSave">บันทึก</button>
      <hr><label>แจ้งเตือนใกล้หมดเมื่อเหลือไม่เกิน (ชิ้น)<input id="stLow" class="m-input" type="number" min="0" value="${p.low_at}"></label>
      <button class="btn-ghost m-sm" id="stLowSave">บันทึกจุดแจ้งเตือน</button></div>`;
    panel.scrollIntoView({behavior:'smooth', block:'center'}); document.getElementById('stQty').focus();
  },
  async save(){
    const qty = parseInt(document.getElementById('stQty').value, 10), note = document.getElementById('stNote').value.trim();
    if(!(qty>=0) || (this.cur.kind!=='count' && qty===0)) return toast('กรุณาใส่จำนวน');
    const r = await api(`/stock/${this.cur.pid}/move`, {json:{kind:this.cur.kind, qty, note}});
    if(r){ toast(`บันทึกแล้ว — คงเหลือ ${r.stock} ชิ้น`); this.render(this.box); }
  },
  async saveLow(){
    const low_at = parseInt(document.getElementById('stLow').value, 10); if(!(low_at>=0)) return;
    if(await api(`/stock/${this.cur.pid}/settings`, {method:'PUT', json:{low_at}})){ toast('บันทึกจุดแจ้งเตือนแล้ว'); this.render(this.box); }
  },
  async history(pid){
    const d = await api(`/stock/${pid}/history`); if(!d) return;
    const panel = document.getElementById('stPanel');
    panel.innerHTML = `<div class="m-card"><div class="m-row"><h3>🕘 ประวัติสต็อก — ${esc(d.product)}</h3><button class="btn-ghost m-sm" id="stClose">✕</button></div>${this.moveTable(d.moves, false)}</div>`;
    panel.scrollIntoView({behavior:'smooth', block:'center'});
  },
  async loadMoves(){
    const d = await api('/stock/moves?scope='+this.scope); const el = document.getElementById('stMoves'); if(!d || !el) return;
    el.innerHTML = this.moveTable(d.moves, true);
  },
  moveTable(moves, withProduct){
    return moves.length ? `<div style="overflow-x:auto"><table class="m-table"><tr><th>วันที่</th>${withProduct?'<th>สินค้า</th>':''}<th>รายการ</th><th>จำนวน</th><th>คงเหลือ</th><th>โดย</th><th>หมายเหตุ</th></tr>
      ${moves.map(m=>`<tr><td><small>${esc(m.date)}</small></td>${withProduct?`<td>${esc(m.product)}</td>`:''}<td>${esc(m.label)}</td>
        <td class="${m.change>0?'m-plus':'m-minus'}"><b>${m.change>0?'+':''}${m.change}</b></td><td>${m.balance}</td><td>${esc(m.by)}</td><td><small>${esc(m.note)}</small></td></tr>`).join('')}</table></div>`
      : '<p class="m-muted">ยังไม่มีความเคลื่อนไหว</p>';
  },
};
