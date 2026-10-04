/* modules/hr_schedule.js — ตารางกะรายสัปดาห์ (แถว = พนักงาน, คอลัมน์ = วัน) ใช้ผ่าน HrSchedule.render(box)
   กดช่อง → แก้กะ (เวลา, พัก, สถานะ มาทำงาน/ขาด/ลา) · คัดลอกจากสัปดาห์ก่อน · ยืนยันมาทำงานถึงวันนี้
   API: GET /hr/shifts?start=&days=7 · POST /hr/shifts · DELETE /hr/shifts/{id} · POST /hr/shifts/copy-week · POST /hr/shifts/confirm */
const HrSchedule = {
  PRESETS: [['เช้า','08:00','17:00',60],['สาย','10:00','19:00',60],['บ่าย','13:00','22:00',60],['ดึก','22:00','06:00',60]],
  DAYS: ['อา.','จ.','อ.','พ.','พฤ.','ศ.','ส.'],
  iso(d){ return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`; },
  parse(s){ const [y,m,d] = s.split('-').map(Number); return new Date(y, m-1, d); },
  monday(d){ const x = new Date(d); x.setDate(x.getDate() - ((x.getDay()+6)%7)); return x; },
  dayLabel(s){ const d = this.parse(s); return `${this.DAYS[d.getDay()]} ${d.getDate()}/${d.getMonth()+1}`; },
  async render(box){
    this.box = box; this.start = this.start || this.iso(this.monday(new Date()));
    const d = await api(`/hr/shifts?start=${this.start}&days=7`); if(!d) return;
    this.data = d;
    const today = this.iso(new Date()), cls = {planned:'hr-planned', worked:'hr-worked', absent:'hr-absent', leave:'hr-leave'};
    const cell = (st, day)=>{ const s = d.shifts.find(x=>x.staff_id===st.id && x.day===day);
      return `<td class="hr-cell ${day===today?'hr-today':''}" data-cell="${st.id}|${day}">${s ? `<div class="hr-shift ${cls[s.status]}"><b>${esc(s.start)}–${esc(s.end)}</b><small>${s.status==='planned'?s.hours+' ชม.':esc(s.status_label)}</small></div>` : '<span class="hr-add">+</span>'}</td>`; };
    const hours = st=>d.shifts.filter(x=>x.staff_id===st.id && ['planned','worked'].includes(x.status)).reduce((a,x)=>a+x.hours,0);
    box.innerHTML = `<div class="m-row hr-nav"><span><button class="btn-ghost m-sm" data-week="-7">◀</button>
        <b>${esc(this.dayLabel(d.days[0]))} – ${esc(this.dayLabel(d.days[6]))}</b>
        <button class="btn-ghost m-sm" data-week="7">▶</button> <button class="btn-ghost m-sm" data-week="0">สัปดาห์นี้</button></span>
      <span><button class="btn-ghost m-sm" id="hrCopy">📋 คัดลอกจากสัปดาห์ก่อน</button> <button class="btn-primary m-sm" id="hrConfirm">✅ ยืนยันมาทำงาน (ถึงวันนี้)</button></span></div>
      ${d.staff.length ? `<div class="m-card" style="overflow-x:auto"><table class="m-table hr-grid"><tr><th>พนักงาน</th>${d.days.map(x=>`<th class="${x===today?'hr-today':''}">${esc(this.dayLabel(x))}</th>`).join('')}<th>รวม</th></tr>
        ${d.staff.map(st=>`<tr><td><b>${esc(st.name)}</b><br><small class="m-muted">${esc(st.position)}</small></td>${d.days.map(x=>cell(st, x)).join('')}<td><b>${hours(st)}</b> ชม.</td></tr>`).join('')}</table></div>
        <p class="m-muted hr-legend"><span class="hr-shift hr-planned">ตามตาราง</span> <span class="hr-shift hr-worked">มาทำงาน</span> <span class="hr-shift hr-absent">ขาด</span> <span class="hr-shift hr-leave">ลา</span> — กดช่องเพื่อลงกะหรือแก้สถานะ · เงินเดือนนับเฉพาะ "มาทำงาน"</p>`
        : '<div class="m-card m-center"><p class="m-muted">ยังไม่มีพนักงาน — ไปที่แท็บ 👥 พนักงาน เพื่อเพิ่มก่อน</p></div>'}
      <div id="hrEdit"></div>`;
    box.onclick = e=>this.click(e);
  },
  async click(e){
    const w = e.target.closest('[data-week]');
    if(w){ const n = +w.dataset.week; const d = n ? this.parse(this.start) : this.monday(new Date()); d.setDate(d.getDate()+n); this.start = this.iso(d); return this.render(this.box); }
    const c = e.target.closest('[data-cell]'); if(c) return this.edit(...c.dataset.cell.split('|'));
    const p = e.target.closest('[data-preset]'); if(p){ const [, s, en, b] = this.PRESETS[+p.dataset.preset]; this.v('heStart').value = s; this.v('heEnd').value = en; this.v('heBreak').value = b; return; }
    const st = e.target.closest('[data-hestatus]'); if(st) return this.save(st.dataset.hestatus);
    if(e.target.id==='heSave') return this.save(null);
    if(e.target.id==='heDel' && confirm('ลบกะนี้?') && await api(`/hr/shifts/${this.cur.id}`, {method:'DELETE'})){ toast('ลบแล้ว'); return this.render(this.box); }
    if(e.target.id==='heClose') document.getElementById('hrEdit').innerHTML = '';
    if(e.target.id==='hrCopy'){ const prev = this.parse(this.start); prev.setDate(prev.getDate()-7);
      const r = await api('/hr/shifts/copy-week', {json:{from_start:this.iso(prev), to_start:this.start}}); if(r){ toast(`คัดลอกแล้ว ${r.copied} กะ`); this.render(this.box); } }
    if(e.target.id==='hrConfirm' && confirm('เปลี่ยนกะ "ตามตาราง" ในสัปดาห์นี้ที่ถึงวันนี้แล้ว เป็น "มาทำงาน" ทั้งหมด?')){
      const r = await api('/hr/shifts/confirm', {json:{start:this.start, days:7}}); if(r){ toast(`ยืนยันแล้ว ${r.confirmed} กะ`); this.render(this.box); } }
  },
  v(id){ return document.getElementById(id); },
  edit(staffId, day){
    staffId = +staffId;
    const st = this.data.staff.find(x=>x.id===staffId), s = this.data.shifts.find(x=>x.staff_id===staffId && x.day===day);
    this.cur = {staff_id:staffId, day, id:s?s.id:null};
    const box = document.getElementById('hrEdit');
    box.innerHTML = `<div class="m-card m-form hr-editor"><div class="m-row"><h3>${esc(st.name)} — ${esc(this.dayLabel(day))}</h3><button class="btn-ghost m-sm" id="heClose">✕</button></div>
      <div>${this.PRESETS.map((p,i)=>`<button class="btn-ghost m-sm" data-preset="${i}">${p[0]} ${p[1]}–${p[2]}</button>`).join(' ')}</div>
      <div class="m-row"><label>เข้า<input id="heStart" class="m-input" type="time" value="${s?s.start:'09:00'}"></label>
        <label>เลิก<input id="heEnd" class="m-input" type="time" value="${s?s.end:'18:00'}"></label>
        <label>พัก (นาที)<input id="heBreak" class="m-input" type="number" min="0" value="${s?s.break_min:60}"></label></div>
      <label>หมายเหตุ<input id="heNote" class="m-input" maxlength="200" value="${esc(s?s.note:'')}"></label>
      <div class="m-row"><button class="btn-primary" id="heSave">💾 บันทึกกะ</button>${s?'<button class="btn-ghost" id="heDel">🗑 ลบ</button>':''}</div>
      <p class="m-muted">บันทึกพร้อมสถานะ:</p>
      <div><button class="btn-ghost m-sm hr-worked" data-hestatus="worked">✅ มาทำงาน</button> <button class="btn-ghost m-sm hr-absent" data-hestatus="absent">❌ ขาด</button>
        <button class="btn-ghost m-sm hr-leave" data-hestatus="leave">🌴 ลา</button> <button class="btn-ghost m-sm" data-hestatus="planned">🗓 ตามตาราง</button></div></div>`;
    box.scrollIntoView({behavior:'smooth', block:'center'});
  },
  async save(status){
    const old = this.data.shifts.find(x=>x.id===this.cur.id);
    const body = {staff_id:this.cur.staff_id, day:this.cur.day, start:this.v('heStart').value, end:this.v('heEnd').value,
      break_min:parseInt(this.v('heBreak').value,10)||0, note:this.v('heNote').value.trim(), status:status || (old ? old.status : 'planned')};
    if(!body.start || !body.end) return toast('กรุณาใส่เวลาเข้า-เลิก');
    if(await api('/hr/shifts', {json:body})){ toast('บันทึกแล้ว'); this.render(this.box); }
  },
};
