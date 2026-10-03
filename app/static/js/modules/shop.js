/* modules/shop.js — ขายออนไลน์ (สมาชิกทุกคนลงขายได้)
   แท็บ: สินค้าทั้งหมด (ตะกร้า + ออเดอร์ของฉัน) · ร้านของฉัน (สินค้า + ออเดอร์ที่ต้องส่ง) · ลงสินค้า
   API: GET /shop/products · POST /shop/orders · GET /shop/orders · GET/POST/PUT /shop/my/products · GET /shop/my/sales
        POST /shop/images · POST /logistics/orders/{id}/status · POST /logistics/orders/{id}/received */
const Cart = {};   // product_id -> qty
const SELL_STEP = {packed:'📦 แพ็กแล้ว', shipped:'🚚 ส่งแล้ว', cancelled:'✕ ยกเลิก'};

registerModule('shop', {
  sub: 'ซื้อ–ขายสินค้า จ่ายผ่านกระเป๋าเงิน · เงินถึงผู้ขายเมื่อผู้ซื้อได้รับของ · ได้โทเคนทุก ฿100',
  render(el){
    this.el = el;
    el.innerHTML = `<div class="m-tabs"><button class="m-tab on" data-tab="all">🛍️ สินค้าทั้งหมด</button>
      <button class="m-tab" data-tab="mine">🏪 ร้านของฉัน</button><button class="btn-primary" data-tab="new">➕ ลงสินค้า</button></div><div id="shBody"></div>`;
    el.onclick = e=>this.click(e);
    this.tab('all');
  },
  tab(name, product){
    this.el.querySelectorAll('[data-tab]').forEach(t=>t.classList.toggle('on', t.dataset.tab===name));
    if(name!=='all' && !State.me) return loginGate(document.getElementById('shBody'), 'ร้านค้า');
    ({all:()=>this.showAll(), mine:()=>this.showMine(), new:()=>this.showForm(product)})[name]();
  },
  async click(e){
    const t = e.target.closest('button,a'); if(!t) return;
    const d = t.dataset;
    if(d.tab) return this.tab(d.tab);
    if(d.add){ const p = this.products.find(x=>x.id==d.add); if((Cart[p.id]||0) < p.stock){ Cart[p.id]=(Cart[p.id]||0)+1; this.drawCart(); } else toast('สินค้าไม่พอ'); }
    if(d.rm){ delete Cart[d.rm]; this.drawCart(); }
    if(t.id==='checkoutBtn') this.checkout();
    if(d.received && confirm('ได้รับสินค้าครบถ้วนแล้ว? ระบบจะโอนเงินให้ผู้ขาย')){
      if(await api(`/logistics/orders/${d.received}/received`, {method:'POST'})){ toast('ขอบคุณครับ — โอนเงินให้ผู้ขายแล้ว'); this.loadOrders(); }
    }
    if(d.edit) this.tab('new', this.myProducts.find(p=>p.id==d.edit));
    if(d.step){
      let tracking = '';
      if(d.step==='shipped'){ tracking = prompt('เลขพัสดุ (ไม่บังคับ)') || ''; }
      if(d.step==='cancelled' && !confirm(`ยกเลิกออเดอร์ #${d.order}? ระบบจะคืนเงินผู้ซื้อและคืนสต็อก`)) return;
      if(await api(`/logistics/orders/${d.order}/status`, {json:{status:d.step, tracking}})){ toast('อัปเดตแล้ว'); this.showMine(); }
    }
    if(t.id==='pfSave') this.save();
  },

  /* ── สินค้าทั้งหมด ── */
  async showAll(){
    const box = document.getElementById('shBody');
    box.innerHTML = `<div class="m-split"><div class="m-grid" id="shopGrid"><p class="m-muted">กำลังโหลด…</p></div>
      <div><div class="m-card"><h3>🧺 ตะกร้า</h3><div id="cartBox"></div></div><div class="m-card"><h3>📦 ออเดอร์ของฉัน</h3><div id="myOrders"></div></div></div></div>`;
    const d = await api('/shop/products');
    this.products = d ? d.products : [];
    document.getElementById('shopGrid').innerHTML = this.products.length ? this.products.map(p=>`
      <div class="m-card m-product">
        ${gallery(p.images, '🛍️')}
        <b>${esc(p.name)}</b><p class="m-muted">${esc(p.description)}</p><small class="m-muted">🏪 ${esc(p.seller)}</small>
        <div class="m-row"><span class="m-price">${baht(p.price)}</span><span class="m-muted">เหลือ ${p.stock}</span></div>
        <button class="btn-primary" data-add="${p.id}" ${p.stock<1?'disabled':''}>${p.stock<1?'หมด':'ใส่ตะกร้า'}</button></div>`).join('')
      : '<p class="m-muted">ยังไม่มีสินค้า — กด ➕ ลงสินค้า เพื่อเปิดร้านของคุณ</p>';
    this.drawCart(); this.loadOrders();
  },
  drawCart(){
    const lines = Object.entries(Cart).map(([id,q])=>({p:(this.products||[]).find(x=>x.id==id), q})).filter(x=>x.p);
    const total = lines.reduce((s,x)=>s+x.p.price*x.q, 0);
    const box = document.getElementById('cartBox'); if(!box) return;
    box.innerHTML = lines.length ? `${lines.map(x=>`<div class="m-row"><span>${esc(x.p.name)} × ${x.q}</span><span>${baht(x.p.price*x.q)} <button class="m-x" data-rm="${x.p.id}">✕</button></span></div>`).join('')}
      <div class="m-row m-total"><span>รวม</span><span>${baht(total)}</span></div>
      <textarea id="shipAddr" class="m-input" rows="2" placeholder="ที่อยู่จัดส่ง"></textarea>
      <button class="btn-primary m-full" id="checkoutBtn">สั่งซื้อ (จ่ายจากกระเป๋าเงิน)</button>` : '<p class="m-muted">ตะกร้าว่าง</p>';
  },
  async checkout(){
    if(!State.me) return toast('กรุณาเข้าสู่ระบบก่อน');
    const address = document.getElementById('shipAddr').value.trim();
    if(address.length < 5) return toast('กรุณาใส่ที่อยู่จัดส่ง');
    const o = await api('/shop/orders', {json:{items:Object.entries(Cart).map(([id,q])=>({product_id:+id, qty:q})), address}});
    if(!o) return;
    Object.keys(Cart).forEach(k=>delete Cart[k]);
    toast(`สั่งซื้อสำเร็จ ${o.orders.length>1?`(แยก ${o.orders.length} ร้าน)`:`ออเดอร์ #${o.id}`}` + (o.tokens_earned?` · ได้ ${o.tokens_earned} โทเคน`:''));
    fetchWallet().then(updateWalletChips);
    this.showAll();
  },
  async loadOrders(){
    const box = document.getElementById('myOrders');
    if(!State.me){ box.innerHTML = '<p class="m-muted">เข้าสู่ระบบเพื่อดูออเดอร์</p>'; return; }
    const d = await api('/shop/orders');
    box.innerHTML = d && d.orders.length ? d.orders.map(o=>`
      <div class="m-row"><span>#${o.id} · ${esc(o.seller)}<br><small class="m-muted">${o.items.map(i=>esc(i.name)+'×'+i.qty).join(', ')}${o.tracking?` · พัสดุ ${esc(o.tracking)}`:''}</small></span>
        <span>${baht(o.total)}<br>${o.status==='shipped' ? `<button class="btn-primary m-sm" data-received="${o.id}">ได้รับสินค้าแล้ว</button>`
          : `<a href="#" class="m-link" data-view="logistics">${esc(o.status_label)} →</a>`}</span></div>`).join('')
      : '<p class="m-muted">ยังไม่มีออเดอร์</p>';
  },

  /* ── ร้านของฉัน ── */
  async showMine(){
    const box = document.getElementById('shBody');
    const [p, s] = await Promise.all([api('/shop/my/products'), api('/shop/my/sales')]);
    if(!p || !s) return;
    this.myProducts = p.products;
    const pending = s.orders.filter(o=>o.next.length);
    box.innerHTML = `<div class="m-split"><div class="m-card"><h3>📦 ออเดอร์ที่ต้องส่ง (${pending.length})</h3>
        ${s.orders.map(o=>`<div class="m-row"><span>#${o.id} · ${esc(o.buyer)} · ${esc(o.date)}<br><small class="m-muted">${o.items.map(i=>esc(i.name)+'×'+i.qty).join(', ')}<br>ส่งที่: ${esc(o.address)}</small></span>
          <span>${baht(o.total)}<br><small class="m-muted">${esc(o.status_label)}${o.paid_out?' · 💰 ได้รับเงินแล้ว':o.status==='shipped'?' · รอผู้ซื้อยืนยัน':''}</small><br>
          ${o.next.map(n=>`<button class="${n==='cancelled'?'btn-ghost':'btn-primary'} m-sm" data-order="${o.id}" data-step="${n}">${SELL_STEP[n]}</button>`).join(' ')}</span></div>`).join('') || '<p class="m-muted">ยังไม่มีออเดอร์</p>'}
        <p class="m-muted">เงินจะเข้ากระเป๋าของคุณเมื่อผู้ซื้อกด "ได้รับสินค้าแล้ว"</p></div>
      <div class="m-card"><h3>🏪 สินค้าของฉัน (${p.products.length})</h3>${p.products.map(x=>`<div class="m-row"><span>${esc(x.name)}${x.is_active?'':' <small class="m-muted">(ปิดขาย)</small>'} ${modBadge(x.mod)}<br>
          <small class="m-muted">${baht(x.price)} · เหลือ ${x.stock}${x.stock<=5?' ⚠️':''}</small></span><button class="btn-ghost m-sm" data-edit="${x.id}">แก้ไข</button></div>`).join('')
        || '<p class="m-muted">ยังไม่มีสินค้า</p>'}<button class="btn-primary m-full" data-tab="new">➕ ลงสินค้าใหม่</button></div></div>`;
  },

  /* ── ลงสินค้า / แก้ไข ── */
  showForm(p){
    this.editing = p || null;
    document.getElementById('shBody').innerHTML = `<div class="m-card m-form" style="max-width:520px"><h3>${p?`✏️ แก้ไขสินค้า`:'➕ ลงสินค้าใหม่'}</h3>
      <label>รูปสินค้า</label>${imagePicker('pf', p ? (p.images||[]) : [])}
      <label>ชื่อสินค้า<input id="pfName" class="m-input" maxlength="200" value="${esc(p?p.name:'')}"></label>
      <label>รายละเอียด<textarea id="pfDesc" class="m-input" rows="3">${esc(p?p.description:'')}</textarea></label>
      <label>ราคา (บาท)<input id="pfPrice" class="m-input" type="number" min="1" step="0.01" value="${p?p.price:''}"></label>
      <label>จำนวนในสต็อก<input id="pfStock" class="m-input" type="number" min="0" value="${p?p.stock:1}"></label>
      <label><input type="checkbox" id="pfActive" ${!p||p.is_active?'checked':''}> เปิดขาย</label>
      <button class="btn-primary m-full" id="pfSave">${p?'บันทึก':'ลงขาย'}</button></div>`;
  },
  async save(){
    const body = {name:document.getElementById('pfName').value.trim(), description:document.getElementById('pfDesc').value.trim(),
      price:+document.getElementById('pfPrice').value, stock:parseInt(document.getElementById('pfStock').value,10)||0,
      images:pickedImages('pf'), image_url:pickedImages('pf')[0]||'', is_active:document.getElementById('pfActive').checked};
    if(!body.name || !(body.price>0)) return toast('กรุณาใส่ชื่อและราคา');
    const url = this.editing ? `/shop/my/products/${this.editing.id}` : '/shop/my/products';
    const r = await api(url, {method:this.editing?'PUT':'POST', json:body});
    if(r){ toastSubmitted(r, this.editing?'บันทึกแล้ว':'ลงขายแล้ว 🎉'); this.tab('mine'); }
  },
});
