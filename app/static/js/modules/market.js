/* modules/market.js — มือสอง/เช่า: ลงประกาศขาย/ให้เช่า, ซื้อ/เช่าด้วยกระเป๋าเงิน (เงินเข้าผู้ขายทันที)
   API: GET /market/listings · POST /market/listings · POST /market/listings/{id}/deal · /close · POST /market/deals/{id}/return · GET /market/deals */
registerModule('rental', {
  sub: 'ซื้อขายของมือสองและให้เช่าระหว่างสมาชิก · จ่ายผ่านกระเป๋าเงิน',
  async render(el){
    el.innerHTML = `<div class="m-tabs"><button class="m-tab on" data-tab="all">🛍️ ตลาด</button>
      <button class="m-tab" data-tab="mine">📋 ประกาศของฉัน</button><button class="m-tab" data-tab="deals">🧾 ที่ฉันซื้อ/เช่า</button>
      <button class="m-tab" data-tab="new">➕ ลงประกาศ</button></div><div id="mkBody"></div>`;
    el.onclick = e=>{
      const tab = e.target.closest('[data-tab]');
      if(tab){ el.querySelectorAll('.m-tab').forEach(t=>t.classList.toggle('on', t===tab)); this.show(tab.dataset.tab); }
      const deal = e.target.closest('[data-deal]'), close = e.target.closest('[data-close]'), ret = e.target.closest('[data-return]');
      if(deal) this.deal(deal.dataset.deal, deal.dataset.kind, +deal.dataset.price);
      if(close) this.act(`/market/listings/${close.dataset.close}/close`, 'ปิดประกาศแล้ว', 'mine');
      if(ret) this.act(`/market/deals/${ret.dataset.return}/return`, 'บันทึกได้ของคืนแล้ว', 'mine');
      if(e.target.id==='mkSubmit') this.create();
    };
    this.show('all');
  },
  card(l){
    let btn = '';
    if(l.is_mine && l.status==='active') btn = `<button class="btn-ghost m-sm" data-close="${l.id}">ปิดประกาศ</button>`;
    else if(l.is_mine && l.status==='rented' && l.open_deal_id) btn = `<button class="btn-primary m-sm" data-return="${l.open_deal_id}">ได้ของคืนแล้ว</button>`;
    else if(!l.is_mine && l.status==='active') btn = `<button class="btn-primary m-sm" data-deal="${l.id}" data-kind="${l.kind}" data-price="${l.price}">${l.kind==='rent'?'เช่า':'ซื้อ'}</button>`;
    return itemCard({images:l.images, icon:l.kind==='rent'?'🔁':'♻️', tag:{text:l.kind==='rent'?'ให้เช่า':'ขาย', cls:l.kind==='rent'?'st-pending':'st-approved'},
      status:l.status_label, mod:l.mod, title:l.title, text:l.description, price:l.price, unit:l.kind==='rent'?' / วัน':'',
      meta:`${l.seller} · ${l.date}`, actions:btn});
  },
  async show(tab){
    const box = document.getElementById('mkBody');
    if(tab!=='all' && !State.me){ loginGate(box, 'ตลาดมือสอง'); return; }
    if(tab==='new'){
      box.innerHTML = `<div class="m-card m-form"><label>ประเภท<select id="mkKind" class="m-input"><option value="sale">ขาย</option><option value="rent">ให้เช่า (ราคาต่อวัน)</option></select></label>
        <label>ชื่อสินค้า<input id="mkTitle" class="m-input" maxlength="200"></label>
        <label>รายละเอียด<textarea id="mkDesc" class="m-input" rows="3" maxlength="3000"></textarea></label>
        <label>ราคา (บาท)<input id="mkPrice" class="m-input" type="number" min="1"></label>
        <label>รูปสินค้า</label>${imagePicker('mk')}
        <button class="btn-primary" id="mkSubmit">ลงประกาศ</button></div>`;
      return;
    }
    if(tab==='deals'){
      const d = await api('/market/deals');
      box.innerHTML = `<div class="m-card">${d && d.deals.length ? d.deals.map(x=>`<div class="m-row"><span>${x.kind==='rent'?`เช่า ${x.days} วัน`:'ซื้อ'}: ${esc(x.title)}<br><small class="m-muted">${esc(x.date)}${x.kind==='rent'?(x.returned?' · คืนแล้ว':' · ยังไม่คืน'):''}</small></span><span>${baht(x.total)}</span></div>`).join('') : '<p class="m-muted">ยังไม่มีรายการ</p>'}</div>`;
      return;
    }
    const d = await api('/market/listings' + (tab==='mine' ? '?mine=true' : ''));
    box.innerHTML = d && d.listings.length ? `<div class="m-grid">${d.listings.map(l=>this.card(l)).join('')}</div>` : '<p class="m-muted">ยังไม่มีประกาศ</p>';
  },
  async create(){
    const body = {kind:document.getElementById('mkKind').value, title:document.getElementById('mkTitle').value.trim(),
                  description:document.getElementById('mkDesc').value.trim(), price:+document.getElementById('mkPrice').value, images:pickedImages('mk')};
    if(body.title.length<2 || !(body.price>0)){ toast('กรุณาใส่ชื่อและราคา'); return; }
    const r = await api('/market/listings', {json:body});
    if(r){ toast(r.mod ? 'ส่งแล้ว — จะแสดงเมื่อผู้ดูแลอนุมัติ' : 'ลงประกาศแล้ว'); document.querySelector('.m-tab[data-tab="mine"]').click(); }
  },
  async deal(id, kind, price){
    if(!State.me){ toast('กรุณาเข้าสู่ระบบก่อน'); return; }
    let days = 1;
    if(kind==='rent'){ days = parseInt(prompt('เช่ากี่วัน?', '1'), 10); if(!(days>=1)) return; }
    if(!confirm(`${kind==='rent'?`เช่า ${days} วัน`:'ซื้อ'} ราคา ${baht(price*days)} — จ่ายจากกระเป๋าเงิน?`)) return;
    const r = await api(`/market/listings/${id}/deal`, {json:{days}});
    if(r){ toast('สำเร็จ! เงินโอนให้ผู้ขายแล้ว'); fetchWallet().then(updateWalletChips); this.show('all'); }
  },
  async act(url, msg, tab){ if(await api(url, {method:'POST'})){ toast(msg); this.show(tab); } },
});
