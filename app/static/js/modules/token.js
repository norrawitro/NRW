/* modules/token.js — สินทรัพย์ดิจิทัล/โทเคน: ยอดโทเคน, ประวัติ, โอนให้สมาชิก, แลกเป็นเงิน
   API: GET /token · POST /token/transfer · POST /token/redeem */
registerModule('token', {
  sub: 'ได้โทเคนจากการซื้อสินค้า · โอนให้เพื่อน · แลกเป็นเงินเข้ากระเป๋า',
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
        <b class="${h.amount>0?'m-plus':'m-minus'}">${h.amount>0?'+':''}${h.amount.toLocaleString()}</b></div>`).join('') : '<p class="m-muted">ยังไม่มีประวัติ — ซื้อสินค้าทุก ฿100 ได้ 1 โทเคน</p>'}</div></div>`;
    el.onclick = async e=>{
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
});
