/* modules/logistics.js — คลังสินค้า/ขนส่ง (3 แท็บ)
   🚚 พัสดุของฉัน: เส้นทางพัสดุ · 🏬 สต็อกสินค้า: modules/stock.js (StockUI)
   🛠️ คิวจัดส่ง (ผู้ดูแล): แพ็ก → ส่ง → ได้รับ / ยกเลิก
   API: GET /shop/orders · GET /logistics/orders/{id} · GET /logistics/queue · POST /logistics/orders/{id}/status · GET/POST /logistics/inventory */
const STEP_LABEL = {packed:'📦 แพ็กแล้ว', shipped:'🚚 ส่งแล้ว', delivered:'✅ ได้รับแล้ว', cancelled:'✕ ยกเลิก'};

registerModule('logistics', {
  sub: 'ติดตามพัสดุ · จัดการสต็อกสินค้า (รับเข้า/เบิก/ตรวจนับ/ประวัติ) · ผู้ดูแลจัดการคิวจัดส่ง',
  async render(el){
    if(!State.me){ loginGate(el, 'คลังสินค้า/ขนส่ง'); return; }
    const tab = State.lgTab || 'parcel'; State.lgTab = null;
    el.innerHTML = `<div class="m-tabs"><button class="m-tab" data-lgtab="parcel">🚚 พัสดุของฉัน</button><button class="m-tab" data-lgtab="stock">🏬 สต็อกสินค้า</button>
      ${State.me.is_admin?'<button class="m-tab" data-lgtab="queue">🛠️ คิวจัดส่ง (ผู้ดูแล)</button>':''}</div><div id="lgBody"></div>`;
    el.onclick = e=>{
      const tb = e.target.closest('[data-lgtab]'); if(tb) return this.tab(tb.dataset.lgtab);
      const r = e.target.closest('[data-received]');
      if(r && confirm('ได้รับสินค้าครบถ้วนแล้ว? ระบบจะโอนเงินให้ผู้ขาย')) api(`/logistics/orders/${r.dataset.received}/received`, {method:'POST'}).then(x=>{ if(x){ toast('ขอบคุณครับ'); this.track(x.id); } });
      const t = e.target.closest('[data-track]'), s = e.target.closest('[data-step]');
      if(t) this.track(t.dataset.track);
      if(s) this.step(s.dataset.order, s.dataset.step);
    };
    this.tab(tab);
  },
  async tab(name){
    document.querySelectorAll('[data-lgtab]').forEach(b=>b.classList.toggle('on', b.dataset.lgtab===name));
    const body = document.getElementById('lgBody');
    if(name==='stock') return StockUI.render(body);
    if(name==='queue'){ body.innerHTML = '<div class="m-card"><h3>🛠️ คิวจัดส่ง</h3><div id="lgQueue"></div></div>'; return this.loadQueue(); }
    body.innerHTML = `<div class="m-split"><div class="m-card"><h3>📦 พัสดุของฉัน</h3><div id="lgMine"></div></div>
      <div class="m-card"><h3>🧭 เส้นทางพัสดุ</h3><div id="lgTrack"><p class="m-muted">เลือกออเดอร์ทางซ้าย</p></div></div></div>`;
    const d = await api('/shop/orders');
    document.getElementById('lgMine').innerHTML = d && d.orders.length ? d.orders.map(o=>`
      <div class="m-row"><span>#${o.id} · ${baht(o.total)}<br><small class="m-muted">${esc(o.date)}</small></span>
      <button class="btn-ghost" data-track="${o.id}">${esc(o.status_label)} ›</button></div>`).join('')
      : '<p class="m-muted">ยังไม่มีออเดอร์ — <a href="#" data-view="shop" class="m-link">ไปร้านค้า</a></p>';
    if(d && d.orders.length) this.track(d.orders[0].id);
  },
  async track(id){
    const o = await api(`/logistics/orders/${id}`);
    if(!o) return;
    document.getElementById('lgTrack').innerHTML = `<p><b>ออเดอร์ #${o.id}</b> · ${baht(o.total)}${o.tracking?` · เลขพัสดุ <b>${esc(o.tracking)}</b>`:''}</p>
      <p class="m-muted">ส่งที่: ${esc(o.address)}</p>
      <ol class="m-timeline">${o.timeline.map(t=>`<li><b>${esc(t.label)}</b> <small class="m-muted">${esc(t.date)}</small><br>${esc(t.note)}</li>`).join('')}</ol>
      ${o.status==='shipped' ? `<button class="btn-primary" data-received="${o.id}">ได้รับสินค้าแล้ว (โอนเงินให้ผู้ขาย)</button>` : ''}`;
  },
  async loadQueue(){
    const d = await api('/logistics/queue');
    document.getElementById('lgQueue').innerHTML = d && d.orders.length ? `<table class="m-table"><tr><th>#</th><th>ลูกค้า</th><th>สินค้า</th><th>ยอด</th><th>สถานะ</th><th></th></tr>
      ${d.orders.map(o=>`<tr><td>${o.id}</td><td>${esc(o.full_name)}<br><small class="m-muted">${esc(o.address)}</small></td>
        <td>${o.items.map(i=>esc(i.name)+'×'+i.qty).join('<br>')}</td><td>${baht(o.total)}</td><td>${esc(o.status_label)}</td>
        <td>${o.next.map(n=>`<button class="${n==='cancelled'?'btn-ghost':'btn-primary'} m-sm" data-order="${o.id}" data-step="${n}">${STEP_LABEL[n]}</button>`).join(' ')}</td></tr>`).join('')}</table>`
      : '<p class="m-muted">ไม่มีออเดอร์ค้าง</p>';
  },
  async step(id, status){
    let tracking = '';
    if(status==='shipped'){ tracking = prompt('เลขพัสดุ (ไม่บังคับ)') || ''; }
    if(status==='cancelled' && !confirm(`ยกเลิกออเดอร์ #${id}? (คืนเงิน + คืนสต็อกให้อัตโนมัติ)`)) return;
    if(await api(`/logistics/orders/${id}/status`, {json:{status, tracking}})){ toast('อัปเดตแล้ว'); this.loadQueue(); }
  },
});
