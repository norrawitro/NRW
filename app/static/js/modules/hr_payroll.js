/* modules/hr_payroll.js — เงินเดือนรายเดือน ใช้ผ่าน HrPayroll.render(box)
   ตารางสรุป → กด "สลิป" ดูรายละเอียด, เพิ่มรายการบวก/หัก, จ่าย (โอนเข้ากระเป๋า / บันทึกว่าจ่ายเอง), ส่งออก CSV
   API: GET /hr/payroll?month= · POST /hr/adjusts · DELETE /hr/adjusts/{id} · POST /hr/payroll/{id}/pay · GET /hr/payroll/export.csv */
const HrPayroll = {
  MONTHS: ['มกราคม','กุมภาพันธ์','มีนาคม','เมษายน','พฤษภาคม','มิถุนายน','กรกฎาคม','สิงหาคม','กันยายน','ตุลาคม','พฤศจิกายน','ธันวาคม'],
  monthLabel(m){ const [y, mo] = m.split('-').map(Number); return `${this.MONTHS[mo-1]} ${y+543}`; },
  async render(box){
    this.box = box; this.month = this.month || new Date().toISOString().slice(0,7);
    const d = await api('/hr/payroll?month='+this.month); if(!d) return;
    this.data = d; const t = d.totals;
    box.innerHTML = `<div class="m-row"><label class="hr-month">เดือน <input id="prMonth" class="m-input" type="month" value="${this.month}"></label>
        <a class="btn-ghost m-sm" href="/hr/payroll/export.csv?month=${this.month}">⬇️ ส่งออก Excel (CSV)</a></div>
      <div class="st-cards"><div class="m-card st-card"><small>รวมรับ (ก่อนหัก)</small><b>${baht(t.gross)}</b></div>
        <div class="m-card st-card"><small>ประกันสังคม</small><b>${baht(t.social_security)}</b></div>
        <div class="m-card st-card"><small>รวมหัก</small><b>${baht(t.deductions)}</b></div>
        <div class="m-card st-card"><small>ยอดจ่ายสุทธิ</small><b>${baht(t.net)}</b></div></div>
      <div class="m-card" style="overflow-x:auto">${d.rows.length ? `<table class="m-table"><tr><th>พนักงาน</th><th>วัน/ชม.</th><th>OT</th><th>รวมรับ</th><th>หัก</th><th>สุทธิ</th><th>สถานะ</th><th></th></tr>
        ${d.rows.map((r,i)=>`<tr><td><b>${esc(r.staff.name)}</b><br><small class="m-muted">${esc(r.pay_type_label)} ${baht(r.staff.rate)}</small></td>
          <td>${r.days_worked} วัน<br><small class="m-muted">${r.regular_hours} ชม.${r.days_absent?` · ขาด ${r.days_absent}`:''}${r.days_leave?` · ลา ${r.days_leave}`:''}</small></td>
          <td>${r.ot_hours?r.ot_hours+' ชม.':'—'}</td><td>${baht(r.gross)}</td><td>${baht(r.deductions)}</td><td><b>${baht(r.net)}</b></td>
          <td>${r.paid?`<span class="badge st-approved">จ่ายแล้ว</span>`:r.planned_unconfirmed?`<span class="badge st-pending" title="ยังไม่ยืนยันการมาทำงาน">⚠️ รอยืนยัน ${r.planned_unconfirmed} กะ</span>`:'<span class="badge">ยังไม่จ่าย</span>'}</td>
          <td><button class="btn-ghost m-sm" data-slip="${i}">🧾 สลิป</button></td></tr>`).join('')}</table>`
        : '<p class="m-muted">ยังไม่มีข้อมูลเดือนนี้ — เพิ่มพนักงานและลงกะในตารางงานก่อน</p>'}</div><div id="prSlip"></div>`;
    document.getElementById('prMonth').onchange = e=>{ if(e.target.value){ this.month = e.target.value; this.render(box); } };
    box.onclick = e=>this.click(e);
    if(this.openIdx!==undefined && d.rows[this.openIdx]) this.slip(this.openIdx);
  },
  async click(e){
    const s = e.target.closest('[data-slip]'); if(s) return this.slip(+s.dataset.slip);
    const del = e.target.closest('[data-adjdel]');
    if(del && await api(`/hr/adjusts/${del.dataset.adjdel}`, {method:'DELETE'})) return this.render(this.box);
    if(e.target.id==='adjAdd'){
      const sign = document.getElementById('adjSign').value==='-' ? -1 : 1, amount = +document.getElementById('adjAmt').value, note = document.getElementById('adjNote').value.trim();
      if(!(amount>0) || !note) return toast('กรุณาใส่จำนวนเงินและรายละเอียด');
      if(await api('/hr/adjusts', {json:{staff_id:this.cur.staff.id, month:this.month, amount:sign*amount, note}})){ toast('เพิ่มรายการแล้ว'); this.render(this.box); }
    }
    const pay = e.target.closest('[data-pay]');
    if(pay){
      const r = this.cur, how = pay.dataset.pay==='wallet' ? `โอน ${baht(r.net)} จากกระเป๋าของคุณเข้ากระเป๋า @${r.staff.username}` : `บันทึกว่าจ่าย ${baht(r.net)} ให้ ${r.staff.name} แล้ว (เงินสด/โอนธนาคาร)`;
      if(!confirm(how+'?\nจ่ายแล้วแก้ไขเดือนนี้ไม่ได้')) return;
      if(await api(`/hr/payroll/${r.staff.id}/pay`, {json:{month:this.month, method:pay.dataset.pay}})){ toast('จ่ายเงินเดือนแล้ว'); fetchWallet().then(updateWalletChips); this.render(this.box); }
    }
    if(e.target.id==='slipPrint') window.print();
  },
  slip(i){
    const r = this.data.rows[i]; this.cur = r; this.openIdx = i;
    const line = (t, v, neg)=>v ? `<div class="m-row"><span>${t}</span><span class="${neg?'m-minus':''}">${neg?'-':''}${baht(v)}</span></div>` : '';
    const box = document.getElementById('prSlip');
    box.innerHTML = `<div class="m-card hr-slip"><div class="m-row"><h3>🧾 สลิปเงินเดือน ${esc(this.monthLabel(this.month))}</h3><span><button class="btn-ghost m-sm" id="slipPrint">🖨 พิมพ์</button></span></div>
      <p><b>${esc(r.staff.name)}</b> ${r.staff.position?'· '+esc(r.staff.position):''} · ${esc(r.pay_type_label)} ${baht(r.staff.rate)}${r.pay_type==='monthly'?'/เดือน':r.pay_type==='daily'?'/วัน':'/ชม.'}</p>
      <p class="m-muted">มาทำงาน ${r.days_worked} วัน · ${r.regular_hours} ชม. · OT ${r.ot_hours} ชม. · ขาด ${r.days_absent} · ลา ${r.days_leave} · ค่าแรงต่อชม. ${baht(r.hourly_rate)}${r.pay_type==='monthly'?' · <i>รายเดือนได้เต็มเดือน หักเฉพาะวันที่บันทึกว่า "ขาด"</i>':''}</p>
      <div class="m-split"><div><h4>รายรับ</h4>${line(r.pay_type==='monthly'?'เงินเดือน':'ค่าจ้าง', r.base)}${line('ค่าล่วงเวลา (OT)', r.ot_pay)}
          ${r.adjusts.filter(a=>a.amount>0).map(a=>`<div class="m-row"><span>${esc(a.note)} ${r.paid?'':`<button class="btn-ghost m-sm" data-adjdel="${a.id}">✕</button>`}</span><span>${baht(a.amount)}</span></div>`).join('')}
          <div class="m-row hr-total"><span>รวมรับ</span><b>${baht(r.gross + r.absent_deduct)}</b></div></div>
        <div><h4>รายการหัก</h4>${line('หักขาดงาน', r.absent_deduct, true)}${line('ประกันสังคม 5%', r.social_security, true)}
          ${r.adjusts.filter(a=>a.amount<0).map(a=>`<div class="m-row"><span>${esc(a.note)} ${r.paid?'':`<button class="btn-ghost m-sm" data-adjdel="${a.id}">✕</button>`}</span><span class="m-minus">-${baht(-a.amount)}</span></div>`).join('')}
          <div class="m-row hr-total"><span>รวมหัก</span><b>${baht(r.deductions + r.absent_deduct)}</b></div></div></div>
      <div class="m-row hr-net"><span>เงินได้สุทธิ</span><b>${baht(r.net)}</b></div>
      ${r.paid ? `<p><span class="badge st-approved">✅ จ่ายแล้ว ${esc(r.paid.date)} · ${r.paid.method==='wallet'?'โอนเข้ากระเป๋า':'จ่ายนอกระบบ'}</span></p>` : `
        ${r.planned_unconfirmed?`<p class="badge st-pending">⚠️ ยังมี ${r.planned_unconfirmed} กะที่ยังไม่ยืนยันการมาทำงาน — ไม่ถูกนับในเงินเดือน</p>`:''}
        <div class="m-form hr-adj"><b>➕ รายการบวก/หัก เพิ่มเติม</b><div class="m-row"><select id="adjSign" class="m-input" style="width:auto"><option value="+">บวก (โบนัส/เบี้ยขยัน/ค่าคอม)</option><option value="-">หัก (เบิกล่วงหน้า/ค่าเสียหาย)</option></select>
          <input id="adjAmt" class="m-input" type="number" min="0" step="0.01" placeholder="บาท" style="width:120px"></div>
          <div class="m-row"><input id="adjNote" class="m-input" maxlength="200" placeholder="รายละเอียด"><button class="btn-ghost m-sm" id="adjAdd">เพิ่ม</button></div></div>
        <div class="m-row">${r.staff.username?`<button class="btn-primary" data-pay="wallet">💸 โอนเข้ากระเป๋า @${esc(r.staff.username)}</button>`:'<small class="m-muted">ผูกบัญชีพนักงานเพื่อโอนเข้ากระเป๋าได้</small>'}
          <button class="btn-ghost" data-pay="manual">💵 บันทึกว่าจ่ายแล้ว</button></div>`}</div>`;
    box.scrollIntoView({behavior:'smooth', block:'start'});
  },
};
