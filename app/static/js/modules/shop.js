/* modules/shop.js — ขายออนไลน์: รายการสินค้า, ตะกร้า, สั่งซื้อ (จ่ายจากกระเป๋าเงิน), ออเดอร์ของฉัน
   API: GET /shop/products · POST /shop/orders · GET /shop/orders */
const Cart = {};   // product_id -> qty

registerModule('shop', {
  sub: 'ซื้อสินค้า จ่ายจากกระเป๋าเงินกลาง · ได้โทเคนทุก ฿100',
  async render(el){
    el.innerHTML = `<div class="m-split">
      <div><div class="m-grid" id="shopGrid"><p class="m-muted">กำลังโหลด…</p></div></div>
      <div><div class="m-card"><h3>🧺 ตะกร้า</h3><div id="cartBox"></div></div>
           <div class="m-card"><h3>📦 ออเดอร์ของฉัน</h3><div id="myOrders"></div></div></div></div>`;
    const d = await api('/shop/products');
    this.products = d ? d.products : [];
    document.getElementById('shopGrid').innerHTML = this.products.length ? this.products.map(p=>`
      <div class="m-card m-product">
        ${p.image_url ? `<img src="${esc(p.image_url)}" alt="" loading="lazy">` : '<div class="m-noimg">🛍️</div>'}
        <b>${esc(p.name)}</b><p class="m-muted">${esc(p.description)}</p>
        <div class="m-row"><span class="m-price">${baht(p.price)}</span><span class="m-muted">เหลือ ${p.stock}</span></div>
        <button class="btn-primary" data-add="${p.id}" ${p.stock<1?'disabled':''}>${p.stock<1?'หมด':'ใส่ตะกร้า'}</button>
      </div>`).join('') : '<p class="m-muted">ยังไม่มีสินค้า — ผู้ดูแลเพิ่มสินค้าได้ที่แผงผู้ดูแล</p>';
    el.onclick = e=>{
      const add = e.target.closest('[data-add]'), rm = e.target.closest('[data-rm]');
      if(add){ const p = this.products.find(x=>x.id==add.dataset.add); if((Cart[p.id]||0) < p.stock){ Cart[p.id]=(Cart[p.id]||0)+1; this.drawCart(); } else toast('สินค้าไม่พอ'); }
      if(rm){ delete Cart[rm.dataset.rm]; this.drawCart(); }
      if(e.target.id==='checkoutBtn') this.checkout();
    };
    this.drawCart();
    this.loadOrders();
  },
  drawCart(){
    const lines = Object.entries(Cart).map(([id,q])=>({p:this.products.find(x=>x.id==id), q})).filter(x=>x.p);
    const total = lines.reduce((s,x)=>s+x.p.price*x.q, 0);
    document.getElementById('cartBox').innerHTML = lines.length ? `
      ${lines.map(x=>`<div class="m-row"><span>${esc(x.p.name)} × ${x.q}</span><span>${baht(x.p.price*x.q)} <button class="m-x" data-rm="${x.p.id}">✕</button></span></div>`).join('')}
      <div class="m-row m-total"><span>รวม</span><span>${baht(total)}</span></div>
      <textarea id="shipAddr" class="m-input" rows="2" placeholder="ที่อยู่จัดส่ง"></textarea>
      <button class="btn-primary m-full" id="checkoutBtn">สั่งซื้อ (จ่ายจากกระเป๋าเงิน)</button>` : '<p class="m-muted">ตะกร้าว่าง</p>';
  },
  async checkout(){
    if(!State.me){ toast('กรุณาเข้าสู่ระบบก่อน'); return; }
    const address = document.getElementById('shipAddr').value.trim();
    if(address.length < 5){ toast('กรุณาใส่ที่อยู่จัดส่ง'); return; }
    const items = Object.entries(Cart).map(([id,q])=>({product_id:+id, qty:q}));
    const o = await api('/shop/orders', {json:{items, address}});
    if(!o) return;
    Object.keys(Cart).forEach(k=>delete Cart[k]);
    toast(`สั่งซื้อสำเร็จ ออเดอร์ #${o.id}` + (o.tokens_earned?` · ได้ ${o.tokens_earned} โทเคน`:''));
    fetchWallet().then(updateWalletChips);
    this.render(document.getElementById('moduleBody'));
  },
  async loadOrders(){
    const box = document.getElementById('myOrders');
    if(!State.me){ box.innerHTML = '<p class="m-muted">เข้าสู่ระบบเพื่อดูออเดอร์</p>'; return; }
    const d = await api('/shop/orders');
    box.innerHTML = d && d.orders.length ? d.orders.map(o=>`
      <div class="m-row"><span>#${o.id} · ${esc(o.date)}<br><small class="m-muted">${o.items.map(i=>esc(i.name)+'×'+i.qty).join(', ')}</small></span>
        <span>${baht(o.total)}<br><a href="#" class="m-link" data-view="logistics">${esc(o.status_label)} →</a></span></div>`).join('')
      : '<p class="m-muted">ยังไม่มีออเดอร์</p>';
  },
});
