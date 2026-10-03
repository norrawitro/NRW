/* modules/workspace.js — พื้นที่ทำงานร่วมกัน: บอร์ดงาน 3 ช่อง, เชิญสมาชิก, โน้ตร่วม
   API: GET/POST /workspace · GET /workspace/{id} · POST /members · /tasks · /tasks/{tid} · PUT /notes */
const WS_COLS = {todo:'📝 ต้องทำ', doing:'⏳ กำลังทำ', done:'✅ เสร็จ'};
registerModule('workspace', {
  sub: 'บอร์ดงานและโน้ตของทีม — เชิญสมาชิกด้วย username',
  async render(el){
    if(!State.me) return loginGate(el, 'พื้นที่ทำงาน');
    this.el = el;
    const d = await api('/workspace'); if(!d) return;
    el.innerHTML = `<div class="m-tabs">${d.workspaces.map(w=>`<button class="m-tab ${w.id==this.ws?'on':''}" data-ws="${w.id}">${esc(w.name)}</button>`).join('')}
      <button class="m-tab" id="wsNew">➕ สร้างพื้นที่</button></div><div id="wsBody"><p class="m-muted">${d.workspaces.length?'เลือกพื้นที่ทำงานด้านบน':'ยังไม่มีพื้นที่ทำงาน — กด ➕ สร้างพื้นที่'}</p></div>`;
    el.onclick = e=>this.click(e);
    if(!this.ws && d.workspaces.length) this.ws = d.workspaces[0].id;
    if(this.ws) this.open(this.ws);
  },
  async click(e){
    const t = e.target;
    if(t.dataset.ws){ this.ws = +t.dataset.ws; return this.render(this.el); }
    if(t.id==='wsNew'){ const name = prompt('ชื่อพื้นที่ทำงาน'); if(name){ const r = await api('/workspace', {json:{name}}); if(r){ this.ws = r.id; this.render(this.el); } } }
    if(t.id==='wsInvite'){ const username = prompt('username ที่จะเชิญ'); if(username && await api(`/workspace/${this.ws}/members`, {json:{username}})){ toast('เชิญแล้ว'); this.open(this.ws); } }
    if(t.id==='wsAdd'){ const title = document.getElementById('wsTask').value.trim(); if(title && await api(`/workspace/${this.ws}/tasks`, {json:{title}})) this.open(this.ws); }
    if(t.dataset.move && await api(`/workspace/${this.ws}/tasks/${t.dataset.task}`, {json:{status:t.dataset.move}})) this.open(this.ws);
    if(t.id==='wsSave' && await api(`/workspace/${this.ws}/notes`, {method:'PUT', json:{notes:document.getElementById('wsNotes').value}})) toast('บันทึกโน้ตแล้ว');
  },
  async open(id){
    const w = await api(`/workspace/${id}`); if(!w) return;
    const order = Object.keys(WS_COLS);
    document.getElementById('wsBody').innerHTML = `<div class="m-row"><span>👥 ${w.members.map(m=>esc(m.name)).join(', ')}</span>${w.is_owner?'<button class="btn-ghost m-sm" id="wsInvite">+ เชิญ</button>':''}</div>
      <div class="m-row"><input id="wsTask" class="m-input" placeholder="งานใหม่…"><button class="btn-primary m-sm" id="wsAdd">เพิ่ม</button></div>
      <div class="m-kanban">${order.map(s=>`<div class="m-card"><h3>${WS_COLS[s]}</h3>${w.tasks.filter(t=>t.status===s).map(t=>`<div class="m-task">${esc(t.title)}
        <div>${order.indexOf(s)>0?`<button class="m-x" data-task="${t.id}" data-move="${order[order.indexOf(s)-1]}">◀</button>`:''}
        ${order.indexOf(s)<2?`<button class="m-x" data-task="${t.id}" data-move="${order[order.indexOf(s)+1]}">▶</button>`:''}
        <button class="m-x" data-task="${t.id}" data-move="delete">🗑</button></div></div>`).join('')}</div>`).join('')}</div>
      <div class="m-card"><h3>🗒️ โน้ตทีม</h3><textarea id="wsNotes" class="m-input" rows="6">${esc(w.notes)}</textarea><button class="btn-primary" id="wsSave">บันทึกโน้ต</button></div>`;
  },
});
