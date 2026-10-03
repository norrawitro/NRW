/* modules/creator.js — ครีเอเตอร์/สมาชิก VIP: ดูครีเอเตอร์, สมัคร VIP 30 วัน, อ่านโพสต์ VIP, เปิดหน้าของตัวเอง + โพสต์
   API: GET/POST /creator · POST /creator/{id}/subscribe · GET /creator/{id}/posts · POST /creator/me/posts */
registerModule('creator', {
  sub: 'ติดตามครีเอเตอร์ สมัคร VIP เพื่อดูเนื้อหาพิเศษ หรือเปิดหน้าของคุณเอง',
  async render(el){
    this.el = el;
    const d = await api('/creator'); if(!d) return;
    const mine = d.creators.find(c=>c.is_mine);
    el.innerHTML = `<div class="m-split"><div><div class="m-grid">${d.creators.map(c=>`<div class="m-card m-product">${gallery(c.images, '⭐')}<b>⭐ ${esc(c.name)}</b><p class="m-muted">${esc(c.bio)}</p>
        <small class="m-muted">${c.fans} สมาชิก VIP · ${baht(c.monthly_price)}/เดือน</small>
        ${c.subscribed_until?`<span class="badge st-approved">VIP ถึง ${esc(c.subscribed_until)}</span>`:''}
        <div><button class="btn-ghost m-sm" data-posts="${c.id}">ดูโพสต์</button>${!c.is_mine?` <button class="btn-primary m-sm" data-sub="${c.id}" data-price="${c.monthly_price}">${c.subscribed_until?'ต่ออายุ':'สมัคร VIP'}</button>`:''}</div></div>`).join('') || '<p class="m-muted">ยังไม่มีครีเอเตอร์</p>'}</div><div id="crPosts"></div></div>
      <div><div class="m-card m-form"><h3>${mine?'✏️ หน้าครีเอเตอร์ของฉัน':'🌟 เป็นครีเอเตอร์'}</h3><textarea id="cpBio" class="m-input" rows="3" placeholder="แนะนำตัว">${esc(mine?mine.bio:'')}</textarea>
        <input id="cpPrice" class="m-input" type="number" min="1" placeholder="ค่าสมาชิกต่อเดือน (บาท)" value="${mine?mine.monthly_price:''}">
        <label>รูปหน้าเพจ / ตัวอย่างผลงาน</label>${imagePicker('cp', mine ? (mine.images||[]) : [])}<button class="btn-primary" id="cpSave">บันทึก</button></div>
        ${mine?`<div class="m-card m-form"><h3>📝 โพสต์ใหม่</h3><input id="cpTitle" class="m-input" placeholder="หัวข้อ"><textarea id="cpBody" class="m-input" rows="4" placeholder="เนื้อหา"></textarea>
        <label><input type="checkbox" id="cpVip" checked> เฉพาะสมาชิก VIP</label><button class="btn-primary" id="cpPost">โพสต์</button></div>`:''}</div></div>`;
    el.onclick = e=>this.click(e);
  },
  async click(e){
    const t = e.target;
    if(t.dataset.posts) this.posts(t.dataset.posts);
    if(t.dataset.sub){
      if(!State.me) return toast('กรุณาเข้าสู่ระบบก่อน');
      if(confirm(`สมัคร VIP 30 วัน ราคา ${baht(t.dataset.price)}?`)){ const r = await api(`/creator/${t.dataset.sub}/subscribe`, {method:'POST'}); if(r){ toast(`เป็น VIP ถึง ${r.until}`); fetchWallet().then(updateWalletChips); await this.render(this.el); this.posts(t.dataset.sub); } }
    }
    if(t.id==='cpSave'){
      if(!State.me) return toast('กรุณาเข้าสู่ระบบก่อน');
      if(await api('/creator', {json:{bio:document.getElementById('cpBio').value.trim(), monthly_price:+document.getElementById('cpPrice').value, images:pickedImages('cp')}})){ toast('บันทึกแล้ว'); this.render(this.el); }
    }
    if(t.id==='cpPost'){
      const body = {title:document.getElementById('cpTitle').value.trim(), body:document.getElementById('cpBody').value, vip_only:document.getElementById('cpVip').checked};
      const r = body.title && await api('/creator/me/posts', {json:body});
      if(r){ toastSubmitted(r, 'โพสต์แล้ว'); this.render(this.el); }
    }
  },
  async posts(id){
    const d = await api(`/creator/${id}/posts`); if(!d) return;
    document.getElementById('crPosts').innerHTML = `<div class="m-card"><h3>📰 โพสต์</h3>${d.posts.map(p=>`<div class="m-row" style="display:block"><b>${p.vip_only?'💎 ':''}${esc(p.title)}</b> <small class="m-muted">${esc(p.date)}</small> ${modBadge(p.mod)}
      <div class="m-pre">${p.body!==null?esc(p.body):'🔒 สมัคร VIP เพื่ออ่านโพสต์นี้'}</div></div>`).join('') || '<p class="m-muted">ยังไม่มีโพสต์</p>'}</div>`;
  },
});
