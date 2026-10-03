/* modules/ads.js — โฆษณา: ซื้อพื้นที่โฆษณาบนหน้าแรก (คิดตามจำนวนวัน), ดูยอดแสดงผล/คลิก, ผู้ดูแลปิดโฆษณาได้
   ยังแสดงโฆษณา 1 ชิ้นบนหน้าแรก (#homeAd) ด้วย
   API: GET /ads/serve · GET/POST /ads · GET /ads/admin/all · POST /ads/{id}/toggle */
registerModule('ads', {
  sub: 'ลงโฆษณาบนหน้าแรกของ Nora-Web · จ่ายจากกระเป๋าเงิน',
  async render(el){
    if(!State.me) return loginGate(el, 'ระบบโฆษณา');
    const d = await api('/ads'); if(!d) return;
    el.innerHTML = `<div class="m-split"><div class="m-card"><h3>📢 โฆษณาของฉัน</h3>${d.ads.map(a=>`<div class="m-row"><span><b>${esc(a.title)}</b> ${modBadge(a.mod)}<br><small class="m-muted">ถึง ${esc(a.ends)} · แสดง ${a.views} · คลิก ${a.clicks}</small></span>
        <span class="badge ${a.running?'st-approved':'st-rejected'}">${a.running?'กำลังแสดง':'หยุดแล้ว'}</span></div>`).join('') || '<p class="m-muted">ยังไม่มีโฆษณา</p>'}</div>
      <div class="m-card m-form"><h3>➕ ซื้อโฆษณา (${baht(d.price_per_day)}/วัน)</h3><input id="adTitle" class="m-input" maxlength="100" placeholder="หัวข้อ">
        <input id="adText" class="m-input" maxlength="300" placeholder="ข้อความ"><input id="adLink" class="m-input" placeholder="ลิงก์ https://… (ไม่บังคับ)">
        <input id="adDays" class="m-input" type="number" min="1" max="90" value="7"><button class="btn-primary" id="adBuy">ซื้อ</button></div></div><div id="adAdmin"></div>`;
    el.onclick = async e=>{
      if(e.target.id==='adBuy'){
        const days = +document.getElementById('adDays').value;
        if(!confirm(`ซื้อโฆษณา ${days} วัน ราคา ${baht(d.price_per_day*days)}?`)) return;
        const body = {title:document.getElementById('adTitle').value.trim(), text:document.getElementById('adText').value.trim(), link:document.getElementById('adLink').value.trim(), days};
        const r = await api('/ads', {json:body});
        if(r){ toastSubmitted(r, 'ลงโฆษณาแล้ว'); fetchWallet().then(updateWalletChips); this.render(el); }
      }
      if(e.target.dataset.adToggle && await api(`/ads/${e.target.dataset.adToggle}/toggle`, {method:'POST'})) this.render(el);
    };
    if(State.me.is_admin){
      const all = await api('/ads/admin/all');
      if(all) document.getElementById('adAdmin').innerHTML = `<div class="m-card"><h3>🛠️ โฆษณาทั้งหมด (ผู้ดูแล)</h3>${all.ads.map(a=>`<div class="m-row"><span>${esc(a.title)} <small class="m-muted">โดย ${esc(a.owner)} · ${esc(a.text)}</small></span>
        <button class="btn-ghost m-sm" data-ad-toggle="${a.id}">${a.is_active?'ปิด':'เปิด'}</button></div>`).join('') || '<p class="m-muted">ไม่มี</p>'}</div>`;
    }
  },
});
// โฆษณาบนหน้าแรก — router.js เรียกทุกครั้งที่กลับมาหน้าแรก
async function loadHomeAd(){
  const box = document.getElementById('homeAd'); if(!box) return;
  box.innerHTML = '';
  try{
    const d = await (await fetch('/ads/serve')).json();
    if(d.ad) box.innerHTML = `<div class="m-card m-ad"><small class="m-muted">ผู้สนับสนุน</small><b>${esc(d.ad.title)}</b><span>${esc(d.ad.text)}</span>
      ${d.ad.has_link?`<a class="btn-ghost m-sm" href="/ads/${d.ad.id}/go" target="_blank" rel="noopener sponsored">ดูเพิ่ม →</a>`:''}</div>`;
  }catch(e){}
}
