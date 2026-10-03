/* modules/logistics.js — คลังสินค้า/ขนส่ง
   สมาชิก: ดูเส้นทางพัสดุของออเดอร์ตัวเอง
   ผู้ดูแล: คิวออเดอร์ (แพ็ก → ส่ง → ได้รับ / ยกเลิก) + สต็อกสินค้า
   API: GET /shop/orders · GET /logistics/orders/{id} · GET /logistics/queue · POST /logistics/orders/{id}/status · GET/POST /logistics/inventory */
const STEP_LABEL = {packed:'📦 แพ็กแล้ว', shipped:'🚚 ส่งแล้ว', delivered:'✅ ได้รับแล้ว', cancelled:'✕ ยกเลิก'};

registerModule('logistics', {
  sub: 'ติดตามพัสดุ · ผู้ดูแลจัดการคิวจัดส่งและสต็อก',
  async render(el){
    if(!State.me){ loginGate(el, 'ติดตามพัสดุ'); return; }
    el.innerHTML = `<div class="m-split"><div class="m-card"><h3>📦 พัสดุของฉัน</h3><div id="lgMine"></div></div>
      <div class="m-card"><h3>🧭 เส้นทางพัสดุ</h3><div id="lgTrack"><p class="m-muted">เลือกออเดอร์ทางซ้าย</p></div></div></div>
      ${State.me.is_admin ? `<div class="m-card"><h3>🛠️ คิวจัดส่ง (ผู้ดูแล)</h3><div id="lgQueue"></div></div>
      <div class="m-card"><h3>🏬 สต็อกสินค้า (ผู้ดูแล)</h3><div id="lgStock"></div></div>` : ''}`;
    el.onclick = e=>{
      const t = e.target.closest('[data-track]'), s = e.target.closest('[data-step]'), k = e.target.closest('[data-stock]');
      if(t) this.track(t.dataset.track);
      if(s) this.step(s.dataset.order, s.dataset.step);
      if(k) this.stock(k.dataset.stock);
    };
    const d = await api('/shop/orders');
    document.getElementById('lgMine').innerHTML = d && d.orders.length ? d.orders.map(o=>`
      <div class="m-row"><span>#${o.id} · ${baht(o.total)}<br><small class="m-muted">${esc(o.date)}</small></span>
      <button class="btn-ghost" data-track="${o.id}">${esc(o.status_label)} ›</button></div>`).join('')
      : '<p class="m-muted">ยังไม่มีออเดอร์ — <a href="#" data-view="shop" class="m-link">ไปร้านค้า</a></p>';
    if(d && d.orders.length) this.track(d.orders[0].id);
    if(State.me.is_admin){ this.loadQueue(); this.loadStock(); }
  },
  async track(id){
    const o = await api(`/logistics/orders/${id}`);
    if(!o) return;
    document.getElementById('lgTrack').innerHTML = `<p><b>ออเดอร์ #${o.id}</b> · ${baht(o.total)}${o.tracking?` · เลขพัสดุ <b>${esc(o.tracking)}</b>`:''}</p>
      <p class="m-muted">ส่งที่: ${esc(o.address)}</p>
      <ol class="m-timeline">${o.timeline.map(t=>`<li><b>${esc(t.label)}</b> <small class="m-muted">${esc(t.date)}</small><br>${esc(t.note)}</li>`).join('')}</ol>`;
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
    if(await api(`/logistics/orders/${id}/status`, {json:{status, tracking}})){ toast('อัปเดตแล้ว'); this.loadQueue(); this.loadStock(); }
  },
  async loadStock(){
    const d = await api('/logistics/inventory');
    document.getElementById('lgStock').innerHTML = d && d.products.length ? `<table class="m-table"><tr><th>สินค้า</th><th>คงเหลือ</th><th></th></tr>
      ${d.products.map(p=>`<tr class="${p.low?'m-warn':''}"><td>${esc(p.name)}${p.is_active?'':' <small class="m-muted">(ปิดขาย)</small>'}</td>
        <td>${p.stock}${p.low?' ⚠️':''}</td><td><button class="btn-ghost m-sm" data-stock="${p.id}">± ปรับ</button></td></tr>`).join('')}</table>`
      : '<p class="m-muted">ยังไม่มีสินค้า</p>';
  },
  async stock(id){
    const delta = parseInt(prompt('เพิ่ม/ลดสต็อก (เช่น 10 หรือ -2)'), 10);
    if(!delta) return;
    if(await api(`/logistics/inventory/${id}`, {json:{delta}})) this.loadStock();
  },
});
