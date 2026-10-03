/* modules/events.js — กิจกรรม/สัมมนา/ตั๋ว: ดูกิจกรรม, ซื้อตั๋ว (ได้รหัสตั๋ว), ผู้จัดสร้างกิจกรรม/ดูผู้เข้าร่วม/เช็คอิน
   API: GET/POST /events · POST /events/{id}/tickets · GET /attendees · POST /checkin */
registerModule('events', {
  sub: 'สัมมนา เวิร์กช็อป และกิจกรรม · ซื้อตั๋วผ่านกระเป๋าเงิน เช็คอินด้วยรหัสตั๋ว',
  async render(el){
    this.el = el;
    const d = await api('/events'); if(!d) return;
    el.innerHTML = `<div class="m-split"><div>${d.events.map(e=>`<div class="m-card"><div class="m-row"><b>${esc(e.title)}</b><span class="m-price">${e.price>0?baht(e.price):'ฟรี'}</span></div>
        ${modBadge(e.mod)}<p>${esc(e.description)}</p><small class="m-muted">🗓 ${esc(e.when)} · 📍 ${esc(e.place)} · ผู้จัด ${esc(e.organizer)} · ${e.sold}/${e.capacity} ที่นั่ง</small>
        <div>${e.my_ticket?`<span class="badge st-approved">🎫 ตั๋วของฉัน: ${esc(e.my_ticket)}</span>`
          : !e.past && e.sold<e.capacity ? `<button class="btn-primary m-sm" data-buy="${e.id}" data-price="${e.price}">ซื้อตั๋ว</button>` : `<span class="badge st-rejected">${e.past?'จบแล้ว':'เต็ม'}</span>`}
        ${e.is_mine?` <button class="btn-ghost m-sm" data-att="${e.id}">ผู้เข้าร่วม / เช็คอิน</button>`:''}</div><div id="att-${e.id}"></div></div>`).join('') || '<p class="m-muted">ยังไม่มีกิจกรรม</p>'}</div>
      <div class="m-card m-form"><h3>➕ จัดกิจกรรม</h3><input id="evTitle" class="m-input" placeholder="ชื่อกิจกรรม"><textarea id="evDesc" class="m-input" rows="3" placeholder="รายละเอียด"></textarea>
        <label>วันเวลา<input id="evWhen" class="m-input" type="datetime-local"></label><input id="evPlace" class="m-input" placeholder="สถานที่ หรือลิงก์ออนไลน์">
        <input id="evPrice" class="m-input" type="number" min="0" placeholder="ราคาตั๋ว (0 = ฟรี)"><input id="evCap" class="m-input" type="number" min="1" value="50" placeholder="จำนวนที่นั่ง">
        <button class="btn-primary" id="evNew">สร้างกิจกรรม</button></div></div>`;
    el.onclick = e=>this.click(e);
  },
  async click(e){
    const t = e.target;
    if(t.dataset.buy){
      if(!State.me) return toast('กรุณาเข้าสู่ระบบก่อน');
      if(!confirm(`ซื้อตั๋ว ${+t.dataset.price>0?baht(t.dataset.price):'ฟรี'}?`)) return;
      const r = await api(`/events/${t.dataset.buy}/tickets`, {method:'POST'});
      if(r){ alert(`ได้ตั๋วแล้ว! รหัสตั๋วของคุณ: ${r.code}\nแสดงรหัสนี้กับผู้จัดตอนเช็คอิน`); fetchWallet().then(updateWalletChips); this.render(this.el); }
    }
    if(t.dataset.att) this.attendees(t.dataset.att);
    if(t.dataset.checkin){
      const code = document.getElementById('ci-'+t.dataset.checkin).value.trim();
      const r = code && await api(`/events/${t.dataset.checkin}/checkin`, {json:{code}});
      if(r){ toast(`เช็คอิน ${r.name} แล้ว`); this.attendees(t.dataset.checkin); }
    }
    if(t.id==='evNew'){
      if(!State.me) return toast('กรุณาเข้าสู่ระบบก่อน');
      const when = document.getElementById('evWhen').value;
      if(!when) return toast('กรุณาเลือกวันเวลา');
      const body = {title:document.getElementById('evTitle').value.trim(), description:document.getElementById('evDesc').value.trim(),
        starts_at:new Date(when).toISOString(), place:document.getElementById('evPlace').value.trim(),
        price:+document.getElementById('evPrice').value||0, capacity:+document.getElementById('evCap').value||50};
      const r = await api('/events', {json:body});
      if(r){ toastSubmitted(r, 'สร้างกิจกรรมแล้ว'); this.render(this.el); }
    }
  },
  async attendees(id){
    const d = await api(`/events/${id}/attendees`); if(!d) return;
    document.getElementById('att-'+id).innerHTML = `<div class="m-row"><input id="ci-${id}" class="m-input" placeholder="รหัสตั๋ว"><button class="btn-primary m-sm" data-checkin="${id}">เช็คอิน</button></div>
      ${d.attendees.map(a=>`<div class="m-row"><span>${esc(a.name)} <small class="m-muted">${esc(a.code)}</small></span><span>${a.checked_in?'✅ '+esc(a.checked_in):'—'}</span></div>`).join('') || '<p class="m-muted">ยังไม่มีผู้ซื้อตั๋ว</p>'}`;
  },
});
