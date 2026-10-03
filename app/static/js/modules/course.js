/* modules/course.js — คอร์สเรียนออนไลน์: ดูคอร์ส, ลงทะเบียน (จ่ายผู้สอน), เรียนทีละบท, สร้างคอร์สของตัวเอง
   API: GET/POST /course · GET /course/{id} · POST /course/{id}/lessons · /enroll · /lessons/{lid}/done */
registerModule('course', {
  sub: 'เรียนหรือเปิดสอนคอร์สของคุณเอง · จ่ายผ่านกระเป๋าเงิน (เงินเข้าผู้สอนทันที)',
  async render(el){
    this.el = el;
    const d = await api('/course'); if(!d) return;
    el.innerHTML = `<div class="m-split"><div class="m-grid">${d.courses.map(c=>`<div class="m-card m-product">
        <b>${esc(c.title)}</b><p class="m-muted">${esc(c.description)}</p>
        <small class="m-muted">👩‍🏫 ${esc(c.instructor)} · ${c.lessons} บท · ${c.students} ผู้เรียน</small>
        <div class="m-row"><span class="m-price">${c.price>0?baht(c.price):'ฟรี'}</span>
        <button class="${c.enrolled||c.is_mine?'btn-ghost':'btn-primary'} m-sm" data-open="${c.id}">${c.is_mine?'จัดการ':c.enrolled?'เข้าเรียน':'ดูคอร์ส'}</button></div></div>`).join('') || '<p class="m-muted">ยังไม่มีคอร์ส</p>'}</div>
      <div class="m-card m-form"><h3>➕ เปิดคอร์สใหม่</h3><input id="crTitle" class="m-input" placeholder="ชื่อคอร์ส">
        <textarea id="crDesc" class="m-input" rows="3" placeholder="รายละเอียด"></textarea><input id="crPrice" class="m-input" type="number" min="0" placeholder="ราคา (0 = ฟรี)">
        <button class="btn-primary" id="crNew">สร้างคอร์ส</button></div></div><div id="crDetail"></div>`;
    el.onclick = e=>this.click(e);
  },
  async click(e){
    const t = e.target;
    if(t.dataset.open) return this.open(t.dataset.open);
    if(t.id==='crNew'){
      if(!State.me) return toast('กรุณาเข้าสู่ระบบก่อน');
      const body = {title:document.getElementById('crTitle').value.trim(), description:document.getElementById('crDesc').value.trim(), price:+document.getElementById('crPrice').value||0};
      const r = await api('/course', {json:body}); if(r){ toast('สร้างคอร์สแล้ว เพิ่มบทเรียนได้เลย'); await this.render(this.el); this.open(r.id); }
    }
    if(t.dataset.enroll && confirm('ลงทะเบียนคอร์สนี้?') && await api(`/course/${t.dataset.enroll}/enroll`, {method:'POST'})){ toast('ลงทะเบียนแล้ว'); fetchWallet().then(updateWalletChips); this.open(t.dataset.enroll); }
    if(t.dataset.done && await api(`/course/${this.cid}/lessons/${t.dataset.done}/done`, {method:'POST'})) this.open(this.cid);
    if(t.id==='lsAdd'){
      const body = {title:document.getElementById('lsTitle').value.trim(), content:document.getElementById('lsBody').value, video_id:+document.getElementById('lsVideo').value||null};
      if(body.title && await api(`/course/${this.cid}/lessons`, {json:body})){ toast('เพิ่มบทเรียนแล้ว'); this.open(this.cid); }
    }
  },
  async open(id){
    if(!State.me) return toast('กรุณาเข้าสู่ระบบก่อน');
    this.cid = id;
    const c = await api(`/course/${id}`); if(!c) return;
    const box = document.getElementById('crDetail');
    box.innerHTML = `<div class="m-card"><h3>📘 ${esc(c.title)} ${c.enrolled?`<small class="m-muted">เรียนแล้ว ${c.progress}</small>`:''}</h3><p>${esc(c.description)}</p>
      ${!c.enrolled && !c.is_mine ? `<button class="btn-primary" data-enroll="${c.id}">ลงทะเบียน ${c.price>0?baht(c.price):'(ฟรี)'}</button>` : ''}
      ${c.lessons.map((l,i)=>`<details class="m-lesson"><summary>${l.done?'✅':'📄'} บทที่ ${i+1}: ${esc(l.title)}</summary>
        ${l.content!==undefined ? `${l.video_id?`<video controls preload="none" src="/video/${l.video_id}/file"></video>`:''}<div class="m-pre">${esc(l.content)}</div>
        ${c.enrolled && !l.done ? `<button class="btn-ghost m-sm" data-done="${l.id}">เรียนจบบทนี้</button>`:''}` : '<p class="m-muted">🔒 ลงทะเบียนเพื่อดูเนื้อหา</p>'}</details>`).join('') || '<p class="m-muted">ยังไม่มีบทเรียน</p>'}
      ${c.is_mine ? `<div class="m-form"><h4>➕ เพิ่มบทเรียน</h4><input id="lsTitle" class="m-input" placeholder="ชื่อบท">
        <textarea id="lsBody" class="m-input" rows="4" placeholder="เนื้อหา"></textarea><input id="lsVideo" class="m-input" type="number" placeholder="รหัสวิดีโอจากระบบวิดีโอ (ไม่บังคับ)">
        <button class="btn-primary" id="lsAdd">เพิ่มบท</button></div>` : ''}</div>`;
    box.scrollIntoView({behavior:'smooth'});
  },
});
