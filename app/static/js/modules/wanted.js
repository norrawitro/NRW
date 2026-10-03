/* modules/wanted.js — ประกาศซื้อ: โพสต์ว่าต้องการซื้ออะไร (รูป + ข้อความ + งบ), คนที่มีของยื่นข้อเสนอ,
   เจ้าของกด "รับข้อเสนอ" → จ่ายเงินจากกระเป๋าให้ผู้ขายทันที
   API: GET/POST /wanted/posts · POST /wanted/posts/{id}/close · GET/POST /wanted/posts/{id}/offers
        POST /wanted/offers/{id}/accept | /decline */
registerModule('wanted', {
  sub: 'โพสต์ว่าคุณต้องการซื้ออะไร ให้คนที่มีของมายื่นข้อเสนอ · จ่ายผ่านกระเป๋าเงิน',
  async render(el){
    el.innerHTML = `<div class="m-tabs"><button class="m-tab on" data-tab="all">🔎 คนกำลังหาซื้อ</button>
      <button class="m-tab" data-tab="mine">📋 ประกาศซื้อของฉัน</button><button class="m-tab" data-tab="new">➕ ลงประกาศซื้อ</button></div><div id="wtBody"></div>`;
    el.onclick = e=>this.click(e, el);
    this.show('all');
  },
  async click(e, el){
    const t = e.target, tab = t.closest('[data-tab]');
    if(tab){ el.querySelectorAll('.m-tab').forEach(x=>x.classList.toggle('on', x===tab)); return this.show(tab.dataset.tab); }
    if(t.dataset.offers) return this.offers(t.dataset.offers);
    if(t.dataset.offer) return this.offerForm(t.dataset.offer);
    if(t.dataset.send) return this.sendOffer(t.dataset.send);
    if(t.dataset.close && confirm('ปิดประกาศนี้? ข้อเสนอที่ค้างอยู่จะถูกปฏิเสธ') && await api(`/wanted/posts/${t.dataset.close}/close`, {method:'POST'})){ toast('ปิดประกาศแล้ว'); this.show('mine'); }
    if(t.dataset.accept && confirm(`รับข้อเสนอนี้? จะจ่าย ${baht(t.dataset.price)} จากกระเป๋าให้ผู้ขายทันที`)){
      if(await api(`/wanted/offers/${t.dataset.accept}/accept`, {method:'POST'})){ toast('ซื้อสำเร็จ! เงินโอนให้ผู้ขายแล้ว — นัดรับของกับผู้ขายทางแชท'); fetchWallet().then(updateWalletChips); this.show('mine'); }
    }
    if(t.dataset.decline && await api(`/wanted/offers/${t.dataset.decline}/decline`, {method:'POST'})){ toast('ปฏิเสธแล้ว'); this.offers(t.dataset.post); }
    if(t.id==='wtSubmit') this.create(el);
  },
  card(p){
    let btn = `<button class="btn-ghost m-sm" data-offers="${p.id}">ข้อเสนอ (${p.offer_count})</button>`;
    if(p.is_mine && p.status==='open') btn += ` <button class="btn-ghost m-sm" data-close="${p.id}">ปิดประกาศ</button>`;
    if(!p.is_mine && p.status==='open') btn = `<button class="btn-primary m-sm" data-offer="${p.id}">🙋 ฉันมีของ — ยื่นข้อเสนอ</button> ` + btn;
    if(!p.is_mine) btn += ' ' + dmButton(p.buyer_username, '💬 ทักผู้ประกาศ');
    return itemCard({images:p.images, icon:'🔎', tag:{text:'ต้องการซื้อ', cls:'st-pending'}, status:p.status_label, mod:p.mod,
      title:p.title, text:p.description, price:p.budget, unit:' (งบสูงสุด)', meta:`${p.buyer} · ${p.date}`,
      actions:`<div>${btn}</div><div id="wtOff-${p.id}"></div>`});
  },
  async show(tab){
    const box = document.getElementById('wtBody');
    if(tab!=='all' && !State.me) return loginGate(box, 'ประกาศซื้อ');
    if(tab==='new'){
      box.innerHTML = `<div class="m-card m-form"><label>ต้องการซื้ออะไร<input id="wtTitle" class="m-input" maxlength="200" placeholder="เช่น หาซื้อจักรยานมือสอง"></label>
        <label>รายละเอียด (สภาพ, รุ่น, พื้นที่นัดรับ)<textarea id="wtDesc" class="m-input" rows="3" maxlength="3000"></textarea></label>
        <label>งบสูงสุด (บาท)<input id="wtBudget" class="m-input" type="number" min="1"></label>
        <label>รูปตัวอย่างของที่ต้องการ</label>${imagePicker('wt')}
        <button class="btn-primary" id="wtSubmit">ลงประกาศซื้อ</button></div>`;
      return;
    }
    const d = await api('/wanted/posts' + (tab==='mine' ? '?mine=true' : '')); if(!d) return;
    box.innerHTML = d.posts.length ? `<div class="m-grid m-grid-wide">${d.posts.map(p=>this.card(p)).join('')}</div>` : '<p class="m-muted">ยังไม่มีประกาศซื้อ</p>';
  },
  async create(el){
    const body = {title:document.getElementById('wtTitle').value.trim(), description:document.getElementById('wtDesc').value.trim(),
                  budget:+document.getElementById('wtBudget').value, images:pickedImages('wt')};
    if(body.title.length<2 || !(body.budget>0)) return toast('กรุณาใส่สิ่งที่ต้องการซื้อและงบ');
    const r = await api('/wanted/posts', {json:body});
    if(r){ toastSubmitted(r, 'ลงประกาศซื้อแล้ว'); el.querySelector('[data-tab=mine]').click(); }
  },
  offerForm(id){
    if(!State.me) return toast('กรุณาเข้าสู่ระบบก่อน');
    document.getElementById('wtOff-'+id).innerHTML = `<div class="m-form"><textarea id="woMsg-${id}" class="m-input" rows="2" maxlength="2000" placeholder="รายละเอียดของที่คุณมี / สภาพ / นัดรับ"></textarea>
      <input id="woPrice-${id}" class="m-input" type="number" min="1" placeholder="ราคาที่เสนอ (บาท)">${imagePicker('wo'+id)}
      <button class="btn-primary m-sm" data-send="${id}">ส่งข้อเสนอ</button></div>`;
  },
  async sendOffer(id){
    const body = {message:document.getElementById('woMsg-'+id).value.trim(), price:+document.getElementById('woPrice-'+id).value, images:pickedImages('wo'+id)};
    if(!(body.price>0)) return toast('กรุณาใส่ราคา');
    if(await api(`/wanted/posts/${id}/offers`, {json:body})){ toast('ส่งข้อเสนอแล้ว — รอผู้ประกาศตอบ'); this.offers(id); }
  },
  async offers(id){
    if(!State.me) return toast('กรุณาเข้าสู่ระบบก่อน');
    const d = await api(`/wanted/posts/${id}/offers`); if(!d) return;
    document.getElementById('wtOff-'+id).innerHTML = d.offers.length ? d.offers.map(o=>`<div class="m-card ui-offer">
      <div class="m-row"><b>${esc(o.seller)}</b><span class="m-price">${baht(o.price)}</span></div>${d.is_owner?`<div>${dmButton(o.seller_username, '💬 คุยกับผู้เสนอ')}</div>`:''}
      ${o.message ? `<p class="ui-text">${esc(o.message)}</p>` : ''}${o.images.length ? gallery(o.images) : ''}
      <div class="m-row"><small class="m-muted">${esc(o.date)} · ${esc(o.status_label)}</small>
      ${d.is_owner && d.post_status==='open' && o.status==='pending' ? `<span><button class="btn-primary m-sm" data-accept="${o.id}" data-price="${o.price}">รับข้อเสนอ</button>
        <button class="btn-ghost m-sm" data-decline="${o.id}" data-post="${id}">ไม่รับ</button></span>` : ''}</div></div>`).join('')
      : `<p class="m-muted">${d.is_owner ? 'ยังไม่มีข้อเสนอ' : 'คุณยังไม่ได้ยื่นข้อเสนอ'}</p>`;
  },
});
