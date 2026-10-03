/* modules/token.js — สินทรัพย์ดิจิทัล/โทเคน: ยอดโทเคน, ประวัติ, โอนให้สมาชิก, แลกเป็นเงิน, ตลาดประกาศซื้อ/ขายโทเคน
   API: GET /token · POST /token/transfer · POST /token/redeem
        GET /token/offers?mine= · POST /token/offers {side,amount,price} · POST /token/offers/{id}/take {amount} · /cancel
   ประกาศขาย = พักโทเคนไว้, ประกาศซื้อ = พักเงินไว้ · ยกเลิกแล้วคืนส่วนที่เหลือ */
registerModule('token', {
  sub: 'ได้โทเคนจากการซื้อสินค้า · โอนให้เพื่อน · แลกเป็นเงิน · ประกาศซื้อ/ขายโทเคนกับสมาชิก',
  async render(el){
    if(!State.me){ loginGate(el, 'โทเคน'); return; }
    const d = await api('/token');
    if(!d) return;
    el.innerHTML = `<div class="m-split"><div>
        <div class="ws-card ws-balance"><div class="label">โทเคนของฉัน</div><div class="amount">🪙 ${d.token.toLocaleString()}</div>
          <div class="label">แลกได้ ${d.redeem_rate} โทเคน = ฿1</div></div>
        <div class="m-card m-form"><h3>↗️ โอนโทเคน</h3><input id="tkTo" class="m-input" placeholder="username ผู้รับ">
          <input id="tkAmt" class="m-input" type="number" min="1" placeholder="จำนวน"><button class="btn-primary" id="tkSend">โอน</button></div>
        <div class="m-card m-form"><h3>💱 แลกเป็นเงิน</h3><input id="tkRedeem" class="m-input" type="number" min="${d.redeem_rate}" step="${d.redeem_rate}" placeholder="จำนวนโทเคน (ทีละ ${d.redeem_rate})">
          <button class="btn-primary" id="tkRedeemBtn">แลก</button></div></div>
      <div class="m-card"><h3>📜 ประวัติ</h3>${d.history.length ? d.history.map(h=>`<div class="m-row"><span>${esc(h.label)}<br><small class="m-muted">${esc(h.note)} · ${esc(h.date)}</small></span>
        <b class="${h.amount>0?'m-plus':'m-minus'}">${h.amount>0?'+':''}${h.amount.toLocaleString()}</b></div>`).join('') : '<p class="m-muted">ยังไม่มีประวัติ — ซื้อสินค้าทุก ฿100 ได้ 1 โทเคน</p>'}</div></div>
      <h3 class="m-h">🏦 ตลาดซื้อขายโทเคน</h3><div id="tkMarket"></div>`;
    this.market();
    el.onclick = async e=>{
      const t = e.target;
      if(t.id==='toPost'){
        const side = document.getElementById('toSide').value, amount = parseInt(document.getElementById('toAmt').value, 10), price = +document.getElementById('toPrice').value;
        if(!(amount>0) || !(price>0)) return toast('กรุณาใส่จำนวนและราคา');
        const what = side==='sell' ? `พัก ${amount.toLocaleString()} โทเคน` : `พักเงิน ${baht(amount*price)}`;
        if(confirm(`ลงประกาศ${side==='sell'?'ขาย':'ซื้อ'} ${amount.toLocaleString()} โทเคน ราคา ${baht(price)}/โทเคน?\n(ระบบจะ${what}ไว้จนมีคนรับหรือคุณยกเลิก)`)
           && await api('/token/offers', {json:{side, amount, price}})){ toast('ลงประกาศแล้ว'); fetchWallet().then(updateWalletChips); this.render(el); }
      }
      if(t.dataset.take){
        const amount = parseInt(prompt(`${t.dataset.side==='sell'?'ซื้อ':'ขาย'}กี่โทเคน? (สูงสุด ${t.dataset.max})`, t.dataset.max), 10);
        if(!(amount>0)) return;
        if(confirm(`${t.dataset.side==='sell'?'ซื้อ':'ขาย'} ${amount.toLocaleString()} โทเคน รวม ${baht(amount*t.dataset.price)}?`)
           && await api(`/token/offers/${t.dataset.take}/take`, {json:{amount}})){ toast('สำเร็จ!'); fetchWallet().then(updateWalletChips); this.render(el); }
      }
      if(t.dataset.cancel && confirm('ยกเลิกประกาศ? ส่วนที่เหลือจะคืนให้คุณ') && await api(`/token/offers/${t.dataset.cancel}/cancel`, {method:'POST'})){ toast('ยกเลิกแล้ว'); fetchWallet().then(updateWalletChips); this.render(el); }
      if(e.target.id==='tkSend'){
        const to_username = document.getElementById('tkTo').value.trim(), amount = parseInt(document.getElementById('tkAmt').value, 10);
        if(!to_username || !(amount>0)) return toast('กรุณาใส่ผู้รับและจำนวน');
        if(confirm(`โอน ${amount} โทเคนให้ @${to_username}?`) && await api('/token/transfer', {json:{to_username, amount}})){ toast('โอนแล้ว'); this.render(el); }
      }
      if(e.target.id==='tkRedeemBtn'){
        const amount = parseInt(document.getElementById('tkRedeem').value, 10);
        if(!(amount>0)) return;
        if(await api('/token/redeem', {json:{amount}})){ toast('แลกแล้ว เงินเข้ากระเป๋า'); fetchWallet().then(updateWalletChips); this.render(el); }
      }
    };
  },
  async market(){
    const [d, mine] = await Promise.all([api('/token/offers'), api('/token/offers?mine=true')]); if(!d) return;
    const row = o=>`<div class="m-row"><span>${baht(o.price)}<small class="m-muted"> /โทเคน · เหลือ ${o.remaining.toLocaleString()} · ${esc(o.owner)}</small></span>
      ${o.is_mine ? `<button class="btn-ghost m-sm" data-cancel="${o.id}">ยกเลิก</button>`
        : `<button class="btn-primary m-sm" data-take="${o.id}" data-side="${o.side}" data-max="${o.remaining}" data-price="${o.price}">${o.side==='sell'?'ซื้อ':'ขายให้'}</button>`}</div>`;
    const my = mine ? [...mine.sell, ...mine.buy].sort((a,b)=>b.id-a.id) : [];
    document.getElementById('tkMarket').innerHTML = `<div class="m-split"><div>
        <div class="m-card"><h3>🟢 ประกาศขาย (ถูกสุดก่อน)</h3>${d.sell.map(row).join('') || '<p class="m-muted">ยังไม่มีคนประกาศขาย</p>'}</div>
        <div class="m-card"><h3>🔵 ประกาศซื้อ (ให้ราคาสูงสุดก่อน)</h3>${d.buy.map(row).join('') || '<p class="m-muted">ยังไม่มีคนประกาศซื้อ</p>'}</div></div>
      <div><div class="m-card m-form"><h3>📣 ลงประกาศ</h3><select id="toSide" class="m-input"><option value="sell">ประกาศขายโทเคน</option><option value="buy">ประกาศซื้อโทเคน</option></select>
          <input id="toAmt" class="m-input" type="number" min="1" placeholder="จำนวนโทเคน"><input id="toPrice" class="m-input" type="number" min="0.01" step="0.01" placeholder="ราคาต่อโทเคน (บาท)">
          <button class="btn-primary" id="toPost">ลงประกาศ</button></div>
        <div class="m-card"><h3>📋 ประกาศของฉัน</h3>${my.length ? my.map(o=>`<div class="m-row"><span>${esc(o.side_label)} ${o.amount.toLocaleString()} @ ${baht(o.price)}
          <br><small class="m-muted">เหลือ ${o.remaining.toLocaleString()} · ${esc(o.date)} · ${o.status==='open'?'เปิดอยู่':o.status==='filled'?'ครบแล้ว':'ยกเลิกแล้ว'}</small></span>
          ${o.status==='open'?`<button class="btn-ghost m-sm" data-cancel="${o.id}">ยกเลิก</button>`:''}</div>`).join('') : '<p class="m-muted">ยังไม่มีประกาศ</p>'}</div></div></div>`;
  },
});
