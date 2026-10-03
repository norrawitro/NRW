/* modules/health.js — สุขภาพ/ออกกำลังกาย: บันทึกกิจกรรม, กราฟ 7 วัน, คำแนะนำจาก AI, ได้โทเคน (1 ต่อ 30 นาที สูงสุด 5/วัน)
   API: GET/POST /health · GET /health/tip */
registerModule('health', {
  sub: 'บันทึกการออกกำลังกาย รับคำแนะนำจาก AI และสะสมโทเคน',
  async render(el){
    if(!State.me) return loginGate(el, 'ระบบสุขภาพ');
    const d = await api('/health'); if(!d) return;
    el.innerHTML = `<div class="m-split"><div class="m-card"><h3>📈 7 วันล่าสุด</h3><div class="m-stats">${stat('นาทีรวม', d.total_minutes)}${stat('ก้าวรวม', d.total_steps.toLocaleString())}${stat('เป้า WHO', '150 นาที')}</div>
        ${bars(d.days, 'minutes', 'day')}<div class="m-card m-ai"><b>🤖 โค้ช AI</b><div id="hlTip" class="m-muted">กำลังคิด…</div></div>
        ${d.logs.map(l=>`<div class="m-row"><span>${esc(l.day)} · ${esc(l.activity)}</span><span>${l.minutes} นาที${l.steps?` · ${l.steps.toLocaleString()} ก้าว`:''}${l.tokens?` · +${l.tokens}🪙`:''}</span></div>`).join('')}</div>
      <div class="m-card m-form"><h3>➕ บันทึกวันนี้</h3><select id="hlAct" class="m-input">${d.activities.map(a=>`<option>${esc(a)}</option>`).join('')}</select>
        <input id="hlMin" class="m-input" type="number" min="0" max="600" placeholder="กี่นาที"><input id="hlSteps" class="m-input" type="number" min="0" placeholder="จำนวนก้าว (ไม่บังคับ)">
        <button class="btn-primary" id="hlAdd">บันทึก</button><p class="m-muted">ทุก 30 นาที = 1 โทเคน (สูงสุด 5 ต่อวัน)</p></div></div>`;
    el.onclick = async e=>{
      if(e.target.id!=='hlAdd') return;
      const body = {activity:document.getElementById('hlAct').value, minutes:+document.getElementById('hlMin').value||0, steps:+document.getElementById('hlSteps').value||0};
      if(!body.minutes && !body.steps) return toast('ใส่นาทีหรือจำนวนก้าว');
      const r = await api('/health', {json:body});
      if(r){ toast('บันทึกแล้ว' + (r.tokens?` · +${r.tokens} โทเคน`:'')); this.render(el); }
    };
    const tip = await api('/health/tip');
    const box = document.getElementById('hlTip');
    if(box && tip) box.textContent = tip.tip;
  },
});
