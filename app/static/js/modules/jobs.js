/* modules/jobs.js — ตลาดงาน/ฟรีแลนซ์: ลงงาน, ยื่นข้อเสนอ, จ้าง (พักเงิน), งานเสร็จ = จ่ายฟรีแลนซ์, ยกเลิก = คืนเงิน
   API: GET /jobs?scope=open|mine · POST /jobs · /jobs/{id}/proposals · /hire/{pid} · /complete · /cancel */
registerModule('jobs', {
  sub: 'จ้างงานหรือรับงานฟรีแลนซ์ · เงินพักไว้กับระบบจนงานเสร็จ',
  async render(el){
    el.innerHTML = `<div class="m-tabs"><button class="m-tab on" data-tab="open">💼 งานที่เปิดรับ</button><button class="m-tab" data-tab="mine">📋 งานของฉัน</button><button class="m-tab" data-tab="new">➕ ลงงาน</button></div><div id="jbBody"></div>`;
    el.onclick = e=>this.click(e, el);
    this.show('open');
  },
  async click(e, el){
    const t = e.target, tab = t.closest('[data-tab]');
    if(tab){ el.querySelectorAll('.m-tab').forEach(x=>x.classList.toggle('on', x===tab)); return this.show(tab.dataset.tab); }
    if(t.dataset.propose){
      const message = prompt('ข้อเสนอของคุณ (ระยะเวลา/ประสบการณ์)'); if(!message) return;
      if(await api(`/jobs/${t.dataset.propose}/proposals`, {json:{message}})) toast('ยื่นข้อเสนอแล้ว');
    }
    if(t.dataset.hire && confirm('จ้างคนนี้? เงินค่าจ้างจะถูกพักไว้จนงานเสร็จ') && await api(`/jobs/${t.dataset.job}/hire/${t.dataset.hire}`, {method:'POST'})){ toast('จ้างแล้ว'); fetchWallet().then(updateWalletChips); this.show('mine'); }
    if(t.dataset.act && confirm(t.dataset.act==='complete'?'ยืนยันงานเสร็จ? เงินจะโอนให้ฟรีแลนซ์':'ยกเลิกงาน? (ถ้าจ้างแล้วจะคืนเงินให้)') && await api(`/jobs/${t.dataset.job}/${t.dataset.act}`, {method:'POST'})){ toast('เรียบร้อย'); fetchWallet().then(updateWalletChips); this.show('mine'); }
    if(t.id==='jbPost'){
      const body = {title:document.getElementById('jbTitle').value.trim(), description:document.getElementById('jbDesc').value.trim(), budget:+document.getElementById('jbBudget').value};
      if(await api('/jobs', {json:body})){ toast('ลงงานแล้ว'); el.querySelector('[data-tab=mine]').click(); }
    }
  },
  async show(tab){
    const box = document.getElementById('jbBody');
    if(tab!=='open' && !State.me) return loginGate(box, 'ตลาดงาน');
    if(tab==='new'){ box.innerHTML = `<div class="m-card m-form"><input id="jbTitle" class="m-input" placeholder="ชื่องาน"><textarea id="jbDesc" class="m-input" rows="4" placeholder="รายละเอียดงาน"></textarea>
      <input id="jbBudget" class="m-input" type="number" min="1" placeholder="งบประมาณ (บาท)"><button class="btn-primary" id="jbPost">ลงงาน</button></div>`; return; }
    const d = await api('/jobs?scope='+tab); if(!d) return;
    box.innerHTML = d.jobs.length ? d.jobs.map(j=>`<div class="m-card"><div class="m-row"><b>${esc(j.title)}</b><span class="m-price">${baht(j.budget)}</span></div>
      <p>${esc(j.description)}</p><small class="m-muted">ผู้จ้าง ${esc(j.client)} · ${esc(j.date)} · ${esc(j.status_label)}${j.freelancer?` · ฟรีแลนซ์ ${esc(j.freelancer)}`:''}</small>
      ${tab==='open' && !j.is_mine ? `<div><button class="btn-primary m-sm" data-propose="${j.id}">ยื่นข้อเสนอ</button></div>`:''}
      ${j.is_mine && j.status==='open' ? (j.proposals||[]).map(p=>`<div class="m-row"><span>🙋 ${esc(p.freelancer)}: ${esc(p.message)}</span><button class="btn-primary m-sm" data-job="${j.id}" data-hire="${p.id}">จ้าง</button></div>`).join('') || '<p class="m-muted">ยังไม่มีข้อเสนอ</p>' : ''}
      ${j.is_mine && j.status==='hired' ? `<div><button class="btn-primary m-sm" data-job="${j.id}" data-act="complete">✅ งานเสร็จ จ่ายเงิน</button></div>`:''}
      ${j.is_mine && ['open','hired'].includes(j.status) ? `<div><button class="btn-ghost m-sm" data-job="${j.id}" data-act="cancel">ยกเลิกงาน</button></div>`:''}</div>`).join('')
      : '<p class="m-muted">ยังไม่มีงาน</p>';
  },
});
