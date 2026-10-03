/* modules/health.js — สุขภาพ/ออกกำลังกาย: บันทึกกิจกรรม + รูปหลักฐาน (บังคับ) → ผู้ดูแลอนุมัติ → ได้โทเคน
   กราฟ 7 วัน (นับเฉพาะที่อนุมัติแล้ว), คำแนะนำจาก AI
   API: GET /health · POST /health (multipart: activity, minutes, steps, file) · GET /health/tip · GET /health/evidence/{id} */
const HL_BADGE = {pending:'st-pending', approved:'st-approved', rejected:'st-rejected'};
registerModule('health', {
  sub: 'บันทึกการออกกำลังกายพร้อมรูปหลักฐาน · ผู้ดูแลอนุมัติแล้วได้โทเคน · มีโค้ช AI',
  async render(el){
    if(!State.me) return loginGate(el, 'ระบบสุขภาพ');
    const d = await api('/health'); if(!d) return;
    el.innerHTML = `<div class="m-split"><div class="m-card"><h3>📈 7 วันล่าสุด (ที่อนุมัติแล้ว)</h3>
        <div class="m-stats">${stat('นาทีรวม', d.total_minutes)}${stat('ก้าวรวม', d.total_steps.toLocaleString())}${stat('เป้า WHO', '150 นาที')}</div>
        ${bars(d.days, 'minutes', 'day')}<div class="m-card m-ai"><b>🤖 โค้ช AI</b><div id="hlTip" class="m-muted">กำลังคิด…</div></div>
        <h3>📝 รายการของฉัน</h3>
        ${d.logs.map(l=>`<div class="m-row"><span>${esc(l.day)} · ${esc(l.activity)} · ${l.minutes} นาที${l.steps?` · ${l.steps.toLocaleString()} ก้าว`:''}
            ${l.has_evidence?` · <a class="m-link" href="/health/evidence/${l.id}" target="_blank">📷 รูป</a>`:''}
            ${l.reason?`<br><small class="m-muted">เหตุผล: ${esc(l.reason)}</small>`:''}</span>
          <span><span class="badge ${HL_BADGE[l.status]}">${esc(l.status_label)}</span>${l.tokens?` +${l.tokens}🪙`:''}</span></div>`).join('') || '<p class="m-muted">ยังไม่มีรายการ</p>'}</div>
      <div class="m-card m-form"><h3>➕ บันทึกวันนี้</h3><select id="hlAct" class="m-input">${d.activities.map(a=>`<option>${esc(a)}</option>`).join('')}</select>
        <input id="hlMin" class="m-input" type="number" min="0" max="600" placeholder="กี่นาที"><input id="hlSteps" class="m-input" type="number" min="0" placeholder="จำนวนก้าว (ไม่บังคับ)">
        <label>📷 รูปหลักฐาน (บังคับ) — เช่น หน้าจอแอปนับก้าว, รูปขณะออกกำลังกาย<input id="hlPic" class="m-input" type="file" accept="image/*" capture="environment"></label>
        <button class="btn-primary" id="hlAdd">ส่งให้ผู้ดูแลตรวจ</button>
        <p class="m-muted">อนุมัติแล้ว: ทุก 30 นาที = 1 โทเคน (สูงสุด ${d.daily_tokens} ต่อวัน)</p></div></div>`;
    el.onclick = async e=>{
      if(e.target.id!=='hlAdd') return;
      const minutes = +document.getElementById('hlMin').value||0, steps = +document.getElementById('hlSteps').value||0;
      const pic = document.getElementById('hlPic').files[0];
      if(!minutes && !steps) return toast('ใส่นาทีหรือจำนวนก้าว');
      if(!pic) return toast('กรุณาแนบรูปหลักฐาน');
      const fd = new FormData();
      fd.append('activity', document.getElementById('hlAct').value); fd.append('minutes', minutes); fd.append('steps', steps); fd.append('file', pic);
      e.target.disabled = true;
      const r = await api('/health', {method:'POST', body:fd});
      e.target.disabled = false;
      if(r){ toast(r.status==='pending' ? 'ส่งแล้ว — รอผู้ดูแลตรวจรูปหลักฐาน' : `บันทึกแล้ว${r.tokens?` · +${r.tokens} โทเคน`:''}`); this.render(el); }
    };
    const tip = await api('/health/tip');
    const box = document.getElementById('hlTip');
    if(box && tip) box.textContent = tip.tip;
  },
});
