/* ai.js — ศูนย์ AI: ปุ่มคำถามด่วน, แสดงข้อความ, sendAIMessage() → POST /ai/chat
   ข้อความ AI มีปุ่ม 🔊 ท้ายข้อความ + สวิตช์อ่านอัตโนมัติ (เสียงจากเครื่องผู้ใช้ — tts.js) */
/* ============================================================
   RENDER: AI
   ============================================================ */
const AI_QUICK = ['เช็คยอดเงินฉัน', 'มีไฟล์ใหม่ไหม', 'สรุปข่าวสารล่าสุด', 'แนะนำระบบที่ควรเปิดต่อไป'];
function renderAIQuick(){
  document.getElementById('aiQuick').innerHTML = AI_QUICK.map(q=>`<span class="cat-chip" data-quick="${q}" style="cursor:pointer;">${q}</span>`).join('')
    + (Speech.supported ? `<label class="tts-auto" title="อ่านคำตอบใหม่ให้ฟังอัตโนมัติ ด้วยเสียงในเครื่องของคุณ"><input type="checkbox" id="ttsAuto" ${Speech.auto?'checked':''}> 🔊 อ่านอัตโนมัติ</label>` : '');
  const t = document.getElementById('ttsAuto'); if(t) t.onchange = ()=>Speech.setAuto(t.checked);
}
function renderAIMessages(){
  const el = document.getElementById('aiMessages');
  el.innerHTML = State.aiMessages.map((m, i)=>`<div class="msg ${m.who}" style="white-space:pre-wrap">${esc(m.text)}${m.who==='ai' && Speech.supported
    ? `<button type="button" class="tts-btn" data-speak="${i}" title="ฟังข้อความนี้">🔊</button>` : ''}</div>`).join('');
  el.onclick = e=>{ const b = e.target.closest('[data-speak]'); if(b){ const m = State.aiMessages[+b.dataset.speak]; if(m) Speech.toggle(+b.dataset.speak, m.text); } };
  Speech.mark();
  el.scrollTop = el.scrollHeight;
}
async function sendAIMessage(text){
  if(!text.trim()) return;
  if(Speech.auto) Speech.unlock();      // เริ่มจากการกดของผู้ใช้ → มือถืออนุญาตให้พูดตอนคำตอบมาถึง
  State.aiMessages.push({who:'user', text});
  renderAIMessages();
  const btn = document.getElementById('aiSend');
  btn.disabled = true; btn.textContent = '…';
  try{
    const r = await fetch('/ai/chat', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({message: text})
    });
    if(r.status===401){ alert('กรุณาเข้าสู่ระบบก่อน'); window.location='/members/login'; return; }
    const d = await r.json();
    State.aiMessages.push({who:'ai', text: d.reply || 'ไม่ได้รับคำตอบ'});
  } catch(e){
    State.aiMessages.push({who:'ai', text:'เชื่อมต่อไม่สำเร็จ กรุณาลองใหม่อีกครั้ง'});
  }
  renderAIMessages();
  btn.disabled = false; btn.textContent = 'ส่ง';
  const last = State.aiMessages.length - 1;
  if(Speech.auto && State.aiMessages[last].who==='ai') Speech.speak(last, State.aiMessages[last].text);
}
