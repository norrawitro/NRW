/* modules/course.js — คอร์สเรียนออนไลน์แบบอินเตอร์แอกทีฟ
   ผู้เรียน: ซื้อคอร์ส → เรียนทีละบท (เนื้อหาด้านบน · คำถามปรนัย/อัตนัยด้านล่าง ตรวจทันที) → ถูกครบ = จบบท
   ผู้สอน:  สร้างคอร์ส → เพิ่มบทเรียน + ตัวสร้างคำถาม
   API: GET/POST /course · GET /course/{id} · POST /course/{id}/enroll · POST/DELETE /course/{id}/lessons
        POST /course/{id}/lessons/{lid}/done · POST /course/{id}/lessons/{lid}/questions/{qid}/answer */
registerModule('course', {
  sub: 'เรียนแบบมีแบบฝึกหัด ตรวจคำตอบทันที · หรือเปิดสอนคอร์สของคุณเอง (เงินเข้าผู้สอน)',
  async render(el){
    this.el = el; this.cid = null;
    const d = await api('/course'); if(!d) return;
    el.innerHTML = `<div class="m-split"><div class="m-grid">${d.courses.map(c=>`<div class="m-card m-product">
        ${gallery(c.images, '🎓')}${modBadge(c.mod)}<b>${esc(c.title)}</b><p class="m-muted">${esc(c.description)}</p>
        <small class="m-muted">👩‍🏫 ${esc(c.instructor)} · ${c.lessons} บท · ${c.students} ผู้เรียน${c.progress?` · เรียนแล้ว ${c.progress}`:''}</small>
        <div class="m-row"><span class="m-price">${c.price>0?baht(c.price):'ฟรี'}</span>
        ${c.is_mine ? `<button class="btn-ghost m-sm" data-open="${c.id}">⚙️ จัดการ</button>`
          : c.enrolled ? `<button class="btn-primary m-sm" data-open="${c.id}">▶ เข้าเรียน</button>`
          : `<span><button class="btn-ghost m-sm" data-open="${c.id}">ดูบทเรียน</button> <button class="btn-primary m-sm" data-buy="${c.id}" data-price="${c.price}">${c.price>0?'🛒 ซื้อคอร์ส':'ลงทะเบียนฟรี'}</button></span>`}</div></div>`).join('') || '<p class="m-muted">ยังไม่มีคอร์ส</p>'}</div>
      <div class="m-card m-form"><h3>➕ เปิดคอร์สใหม่</h3><input id="crTitle" class="m-input" placeholder="ชื่อคอร์ส">
        <textarea id="crDesc" class="m-input" rows="3" placeholder="รายละเอียด"></textarea><input id="crPrice" class="m-input" type="number" min="0" placeholder="ราคา (0 = ฟรี)">
        <label>รูปหน้าปกคอร์ส</label>${imagePicker('cr')}
        <button class="btn-primary" id="crNew">สร้างคอร์ส</button></div></div><div id="crDetail"></div>`;
    el.onclick = e=>this.click(e);
  },
  async click(e){
    const t = e.target.closest('button'); if(!t) return;
    const d = t.dataset;
    if(d.open) return this.open(d.open);
    if(d.buy) return this.buy(d.buy, +d.price);
    if(d.lesson) return this.showLesson(+d.lesson);
    if(d.check) return this.check(+d.check);
    if(t.id==='lsDone' && await api(`/course/${this.cid}/lessons/${this.lid}/done`, {method:'POST'})){ toast('จบบทนี้แล้ว ✅'); this.reload(); }
    if(t.id==='lsNext') return this.showLesson(this.next);
    if(t.id==='crNew') return this.create();
    if(t.id==='qAdd') return this.addQuestionRow();
    if(d.qdel) return t.closest('.m-qbuild').remove();
    if(t.id==='lsAdd') return this.addLesson();
    if(d.ldel && confirm('ลบบทเรียนนี้?') && await api(`/course/${this.cid}/lessons/${d.ldel}`, {method:'DELETE'})) this.reload();
  },
  async create(){
    if(!State.me) return toast('กรุณาเข้าสู่ระบบก่อน');
    const body = {title:document.getElementById('crTitle').value.trim(), description:document.getElementById('crDesc').value.trim(), price:+document.getElementById('crPrice').value||0, images:pickedImages('cr')};
    const r = await api('/course', {json:body});
    if(r){ toastSubmitted(r, 'สร้างคอร์สแล้ว เพิ่มบทเรียนได้เลย'); await this.render(this.el); this.open(r.id); }
  },
  async buy(id, price){
    if(!State.me) return toast('กรุณาเข้าสู่ระบบก่อน');
    if(!confirm(price>0 ? `ซื้อคอร์สนี้ ${baht(price)} (จ่ายจากกระเป๋าเงิน)?` : 'ลงทะเบียนคอร์สฟรีนี้?')) return;
    if(await api(`/course/${id}/enroll`, {method:'POST'})){ toast('พร้อมเรียนแล้ว 🎉'); fetchWallet().then(updateWalletChips); await this.render(this.el); this.open(id); }
  },
  async reload(){ const keep = this.lid; await this.open(this.cid, true); if(keep) this.showLesson(keep); },

  /* ── หน้าคอร์ส: รายชื่อบท (ซ้าย) + ห้องเรียน (ขวา) ── */
  async open(id, quiet){
    if(!State.me) return toast('กรุณาเข้าสู่ระบบก่อน');
    const c = await api(`/course/${id}`); if(!c) return;
    this.cid = id; this.c = c; this.lid = null;
    const box = document.getElementById('crDetail');
    const canLearn = c.enrolled || c.is_mine;
    box.innerHTML = `<div class="m-card"><h3>📘 ${esc(c.title)} ${modBadge(c.mod)}</h3><p class="m-muted">👩‍🏫 ${esc(c.instructor)}${c.enrolled?` · เรียนแล้ว ${c.progress} บท`:''}</p>
      ${!canLearn ? `<button class="btn-primary" data-buy="${c.id}" data-price="${c.price}">${c.price>0?`🛒 ซื้อคอร์ส ${baht(c.price)}`:'ลงทะเบียนฟรี'}</button>` : ''}
      <div class="m-course"><div class="m-lessons">${c.lessons.map((l,i)=>`<button class="m-lesson-btn" data-lesson="${l.id}">${l.done?'✅':canLearn?'📄':'🔒'} ${i+1}. ${esc(l.title)}</button>`).join('') || '<p class="m-muted">ยังไม่มีบทเรียน</p>'}</div>
        <div id="lsRoom" class="m-room"><p class="m-muted">${canLearn?'เลือกบทเรียนทางซ้ายเพื่อเริ่มเรียน':'🔒 ซื้อคอร์สเพื่อเข้าเรียน'}</p></div></div>
      ${c.is_mine ? this.builderHtml() : ''}</div>`;
    if(!quiet) box.scrollIntoView({behavior:'smooth'});
    if(canLearn){ const first = c.lessons.find(l=>!l.done) || c.lessons[0]; if(first && !quiet) this.showLesson(first.id); }
  },
  showLesson(lid){
    const c = this.c, i = c.lessons.findIndex(l=>l.id===lid), l = c.lessons[i];
    if(!l || l.content===undefined) return toast('ซื้อคอร์สเพื่อเข้าเรียน');
    this.lid = lid; this.next = c.lessons[i+1] ? c.lessons[i+1].id : null;
    document.querySelectorAll('.m-lesson-btn').forEach(b=>b.classList.toggle('on', +b.dataset.lesson===lid));
    const qs = l.questions || [];
    document.getElementById('lsRoom').innerHTML = `<h3>บทที่ ${i+1}: ${esc(l.title)} ${l.done?'<span class="badge st-approved">✅ จบแล้ว</span>':''}
        ${c.is_mine?`<button class="m-x" data-ldel="${l.id}" title="ลบบท">🗑</button>`:''}</h3>
      ${l.video_id?`<video controls preload="none" src="/video/${l.video_id}/file"></video>`:''}
      <div class="m-pre m-teach">${esc(l.content) || '<span class="m-muted">(ไม่มีเนื้อหา)</span>'}</div>
      ${qs.map((q,n)=>`<div class="m-quizq ${q.correct?'ok':''}" id="q-${q.id}"><b>ข้อ ${n+1}. ${esc(q.prompt)}</b>
        ${q.kind==='choice' ? q.choices.map((ch,k)=>`<label class="m-choice"><input type="radio" name="q${q.id}" value="${k}" ${q.my_answer==String(k)?'checked':''} ${q.correct?'disabled':''}> ${esc(ch)}</label>`).join('')
          : `<input class="m-input" id="qt-${q.id}" placeholder="พิมพ์คำตอบ" value="${esc(q.correct?q.my_answer:'')}" ${q.correct?'disabled':''}>`}
        <div class="m-row">${q.correct?'<span class="m-plus">✅ ถูกต้อง</span>':`<button class="btn-primary m-sm" data-check="${q.id}">ตรวจคำตอบ</button>`}
          <span class="m-muted" id="qf-${q.id}">${q.explanation?'💡 '+esc(q.explanation):''}${c.is_mine&&q.answer!==undefined?` · เฉลย: ${esc(q.kind==='choice'?q.choices[+q.answer]:q.answer)}`:''}</span></div></div>`).join('')}
      <div class="m-row">${c.enrolled && !l.done && !qs.length ? '<button class="btn-primary" id="lsDone">✅ เรียนจบบทนี้</button>' : '<span></span>'}
        ${this.next?'<button class="btn-ghost" id="lsNext">บทถัดไป ▶</button>':''}</div>`;
  },
  async check(qid){
    if(!this.c.enrolled) return toast('ผู้สอนดูเฉลยได้ — ผู้เรียนจึงจะตอบได้');
    const box = document.getElementById('q-'+qid);
    const picked = box.querySelector('input[type=radio]:checked'), typed = document.getElementById('qt-'+qid);
    const answer = picked ? picked.value : typed ? typed.value.trim() : '';
    if(!answer) return toast('เลือกหรือพิมพ์คำตอบก่อน');
    const r = await api(`/course/${this.cid}/lessons/${this.lid}/questions/${qid}/answer`, {json:{answer}}); if(!r) return;
    const fb = document.getElementById('qf-'+qid);
    if(!r.correct){ fb.innerHTML = '<span class="m-minus">❌ ยังไม่ถูก ลองใหม่อีกครั้ง</span>'; box.classList.add('shake'); setTimeout(()=>box.classList.remove('shake'), 400); return; }
    toast(r.lesson_done ? '🎉 ตอบถูกครบ จบบทนี้แล้ว!' : `✅ ถูกต้อง (${r.progress})`);
    this.reload();
  },

  /* ── ตัวสร้างบทเรียน (ผู้สอน) ── */
  builderHtml(){
    return `<div class="m-form m-builder"><h3>➕ เพิ่มบทเรียน</h3><input id="lsTitle" class="m-input" placeholder="ชื่อบท">
      <textarea id="lsBody" class="m-input" rows="5" placeholder="เนื้อหาที่สอน (แสดงด้านบน)"></textarea>
      <input id="lsVideo" class="m-input" type="number" placeholder="รหัสวิดีโอจากระบบวิดีโอ (ไม่บังคับ)">
      <h4>❓ คำถามท้ายบท (แสดงด้านล่าง)</h4><div id="qRows"></div>
      <button class="btn-ghost m-sm" id="qAdd">+ เพิ่มคำถาม</button> <button class="btn-primary" id="lsAdd">บันทึกบทเรียน</button></div>`;
  },
  addQuestionRow(){
    const div = document.createElement('div');
    div.className = 'm-qbuild m-card';
    div.innerHTML = `<div class="m-row"><select class="m-input qKind"><option value="choice">ปรนัย (เลือกตอบ)</option><option value="text">อัตนัย (พิมพ์ตอบ)</option></select>
        <button class="m-x" data-qdel="1" title="ลบคำถาม">✕</button></div>
      <input class="m-input qPrompt" placeholder="คำถาม">
      <div class="qChoiceBox"><textarea class="m-input qChoices" rows="3" placeholder="ตัวเลือก บรรทัดละ 1 ข้อ"></textarea>
        <input class="m-input qRight" type="number" min="1" placeholder="ข้อที่ถูก (เลข 1, 2, 3…)"></div>
      <div class="qTextBox" style="display:none"><input class="m-input qAccept" placeholder="คำตอบที่ถูก (หลายแบบคั่นด้วย | เช่น python|ไพธอน)"></div>
      <input class="m-input qExplain" placeholder="คำอธิบายหลังตอบถูก (ไม่บังคับ)">`;
    div.querySelector('.qKind').onchange = e=>{ const ch = e.target.value==='choice';
      div.querySelector('.qChoiceBox').style.display = ch?'':'none'; div.querySelector('.qTextBox').style.display = ch?'none':''; };
    document.getElementById('qRows').appendChild(div);
  },
  async addLesson(){
    const questions = [...document.querySelectorAll('.m-qbuild')].map(b=>{
      const kind = b.querySelector('.qKind').value;
      return {kind, prompt:b.querySelector('.qPrompt').value.trim(), explanation:b.querySelector('.qExplain').value.trim(),
        choices: kind==='choice' ? b.querySelector('.qChoices').value.split('\n').map(s=>s.trim()).filter(Boolean) : [],
        answer: kind==='choice' ? String((parseInt(b.querySelector('.qRight').value,10)||0)-1) : b.querySelector('.qAccept').value.trim()};
    }).filter(q=>q.prompt);
    const body = {title:document.getElementById('lsTitle').value.trim(), content:document.getElementById('lsBody').value,
                  video_id:+document.getElementById('lsVideo').value||null, questions};
    if(!body.title) return toast('กรุณาใส่ชื่อบท');
    if(questions.some(q=>!q.answer || q.answer==='-1')) return toast('ทุกคำถามต้องระบุคำตอบที่ถูก');
    if(await api(`/course/${this.cid}/lessons`, {json:body})){ toast('เพิ่มบทเรียนแล้ว'); this.open(this.cid, true); }
  },
});
