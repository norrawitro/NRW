/* modules/hr.js — พนักงาน/เงินเดือน (4 แท็บ) สมาชิกทุกคนจัดการพนักงานของตัวเองได้
   📅 ตารางงาน: modules/hr_schedule.js (HrSchedule) · 💰 เงินเดือน: modules/hr_payroll.js (HrPayroll)
   👥 พนักงาน + 🙋 งานของฉัน: ไฟล์นี้
   API: GET/POST /hr/staff · PUT /hr/staff/{id} · GET /hr/me */
registerModule('hr', {
  sub: 'จัดตารางกะพนักงาน · บันทึกมาทำงาน/ขาด/ลา · คำนวณเงินเดือน OT ประกันสังคม · จ่ายเข้ากระเป๋าเงิน',
  async render(el){
    if(!State.me){ loginGate(el, 'พนักงาน/เงินเดือน'); return; }
    this.el = el;
    el.innerHTML = `<div class="m-tabs"><button class="m-tab" data-hrtab="schedule">📅 ตารางงาน</button><button class="m-tab" data-hrtab="payroll">💰 เงินเดือน</button>
      <button class="m-tab" data-hrtab="staff">👥 พนักงาน</button><button class="m-tab" data-hrtab="me">🙋 งานของฉัน</button></div><div id="hrBody"></div>`;
    el.onclick = e=>{
      const t = e.target.closest('[data-hrtab]'); if(t) return this.tab(t.dataset.hrtab);
      const ed = e.target.closest('[data-staffedit]'); if(ed) return this.staffForm(this.staff.find(s=>s.id==ed.dataset.staffedit));
      if(e.target.id==='sfNew') return this.staffForm(null);
      if(e.target.id==='sfSave') return this.saveStaff();
      if(e.target.id==='sfCancel') document.getElementById('sfPanel').innerHTML = '';
    };
    const d = await api('/hr/staff');
    this.tab(d && d.staff.length ? 'schedule' : 'staff');
  },
  tab(name){
    this.el.querySelectorAll('[data-hrtab]').forEach(b=>b.classList.toggle('on', b.dataset.hrtab===name));
    const body = document.getElementById('hrBody');
    if(name==='schedule') return HrSchedule.render(body);
    if(name==='payroll') return HrPayroll.render(body);
    if(name==='me') return this.mine(body);
    return this.staffList(body);
  },
  async staffList(body){
    const d = await api('/hr/staff'); if(!d) return;
    this.staff = d.staff;
    body.innerHTML = `<div class="m-split"><div class="m-card"><div class="m-row"><h3>👥 พนักงานของฉัน (${d.staff.length})</h3><button class="btn-primary m-sm" id="sfNew">➕ เพิ่มพนักงาน</button></div>
      ${d.staff.length ? `<div style="overflow-x:auto"><table class="m-table"><tr><th>ชื่อ</th><th>ค่าจ้าง</th><th>OT</th><th>ประกันสังคม</th><th>บัญชี</th><th></th></tr>
        ${d.staff.map(s=>`<tr class="${s.active?'':'m-muted'}"><td><b>${esc(s.name)}</b>${s.active?'':' (พักงาน)'}<br><small class="m-muted">${esc(s.position)}</small></td>
          <td>${baht(s.rate)}<br><small class="m-muted">${esc(s.pay_type_label)}</small></td><td>×${s.ot_multiplier}</td><td>${s.social_security?'หัก 5%':'—'}</td>
          <td>${s.username?'@'+esc(s.username):'<small class="m-muted">ไม่ผูก</small>'}</td><td><button class="btn-ghost m-sm" data-staffedit="${s.id}">แก้ไข</button></td></tr>`).join('')}</table></div>`
        : '<p class="m-muted">ยังไม่มีพนักงาน — กด ➕ เพิ่มพนักงาน เพื่อเริ่มจัดตารางและคำนวณเงินเดือน</p>'}</div>
      <div id="sfPanel"></div></div>`;
    if(!d.staff.length) this.staffForm(null);
  },
  staffForm(s){
    this.editing = s;
    document.getElementById('sfPanel').innerHTML = `<div class="m-card m-form"><h3>${s?'✏️ แก้ไขพนักงาน':'➕ เพิ่มพนักงาน'}</h3>
      <label>ชื่อ<input id="sfName" class="m-input" maxlength="120" value="${esc(s?s.name:'')}"></label>
      <label>ตำแหน่ง<input id="sfPos" class="m-input" maxlength="120" value="${esc(s?s.position:'')}" placeholder="เช่น แคชเชียร์, พนักงานครัว"></label>
      <label>ประเภทค่าจ้าง<select id="sfType" class="m-input">${[['monthly','รายเดือน'],['daily','รายวัน'],['hourly','รายชั่วโมง']].map(([v,t])=>`<option value="${v}" ${s&&s.pay_type===v?'selected':''}>${t}</option>`).join('')}</select></label>
      <label>อัตรา (บาท — เงินเดือน / ต่อวัน / ต่อชั่วโมง)<input id="sfRate" class="m-input" type="number" min="1" step="0.01" value="${s?s.rate:''}"></label>
      <label>อัตรา OT (เท่าของค่าแรงต่อชั่วโมง)<input id="sfOt" class="m-input" type="number" min="1" max="5" step="0.5" value="${s?s.ot_multiplier:1.5}"></label>
      <label><input type="checkbox" id="sfSso" ${!s||s.social_security?'checked':''}> หักประกันสังคม 5% (สูงสุด 750 บาท)</label>
      <label>ผูกบัญชีสมาชิก (ไม่บังคับ) — พนักงานจะเห็นตารางงาน/สลิป และรับเงินเดือนเข้ากระเป๋าได้<input id="sfUser" class="m-input" placeholder="username เช่น somchai" value="${esc(s&&s.username?s.username:'')}"></label>
      ${s?`<label><input type="checkbox" id="sfActive" ${s.active?'checked':''}> ยังทำงานอยู่</label>`:''}
      <div class="m-row"><button class="btn-primary" id="sfSave">บันทึก</button>${s?'<button class="btn-ghost" id="sfCancel">ยกเลิก</button>':''}</div></div>`;
  },
  async saveStaff(){
    const v = id=>document.getElementById(id);
    const body = {name:v('sfName').value.trim(), position:v('sfPos').value.trim(), pay_type:v('sfType').value, rate:+v('sfRate').value,
      ot_multiplier:+v('sfOt').value||1.5, social_security:v('sfSso').checked, username:v('sfUser').value.trim(), active:v('sfActive') ? v('sfActive').checked : true};
    if(!body.name || !(body.rate>0)) return toast('กรุณาใส่ชื่อและอัตราค่าจ้าง');
    const r = await api(this.editing ? `/hr/staff/${this.editing.id}` : '/hr/staff', {method:this.editing?'PUT':'POST', json:body});
    if(r){ toast('บันทึกแล้ว'); this.staffList(document.getElementById('hrBody')); }
  },
  async mine(body){
    const d = await api('/hr/me'); if(!d) return;
    if(!d.jobs.length){ body.innerHTML = '<div class="m-card m-center"><div style="font-size:40px">🙋</div><p class="m-muted">คุณยังไม่ได้เป็นพนักงานของใคร — ให้นายจ้างใส่ username ของคุณตอนเพิ่มพนักงาน</p></div>'; return; }
    const cls = {planned:'', worked:'st-approved', absent:'st-rejected', leave:'st-pending'};
    body.innerHTML = `<div class="m-split"><div class="m-card"><h3>📅 ตารางงานของฉัน</h3>${d.shifts.length ? d.shifts.map(s=>`<div class="m-row"><span><b>${esc(HrSchedule.dayLabel(s.day))}</b> ${esc(s.start)}–${esc(s.end)}<br><small class="m-muted">${esc(s.employer)} · ${s.hours} ชม.${s.note?' · '+esc(s.note):''}</small></span>
        <span class="badge ${cls[s.status]}">${esc(s.status_label)}</span></div>`).join('') : '<p class="m-muted">ยังไม่มีกะงานช่วงนี้</p>'}</div>
      <div class="m-card"><h3>🧾 สลิปเงินเดือน</h3>${d.payslips.length ? d.payslips.map(p=>`<div class="m-row"><span><b>${esc(HrPayroll.monthLabel(p.month))}</b><br><small class="m-muted">${esc(p.employer)} · ${esc(p.method)} · ${esc(p.date)}</small></span>
        <span style="text-align:right">${baht(p.net)}<br><small class="m-muted">รับ ${baht(p.gross)} · หัก ${baht(p.deductions)}</small></span></div>`).join('') : '<p class="m-muted">ยังไม่มีสลิป</p>'}</div></div>`;
  },
});
