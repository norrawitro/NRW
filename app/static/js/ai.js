/* ai.js — ศูนย์ AI: ปุ่มคำถามด่วน, แสดงข้อความ, sendAIMessage() → POST /ai/chat */
/* ============================================================
   RENDER: AI
   ============================================================ */
const AI_QUICK = ['เช็คยอดเงินฉัน', 'มีไฟล์ใหม่ไหม', 'สรุปข่าวสารล่าสุด', 'แนะนำระบบที่ควรเปิดต่อไป'];
function renderAIQuick(){
  document.getElementById('aiQuick').innerHTML = AI_QUICK.map(q=>`<span class="cat-chip" data-quick="${q}" style="cursor:pointer;">${q}</span>`).join('');
}
function renderAIMessages(){
  const el = document.getElementById('aiMessages');
  el.innerHTML = State.aiMessages.map(m=>`<div class="msg ${m.who}" style="white-space:pre-wrap">${esc(m.text)}</div>`).join('');
  el.scrollTop = el.scrollHeight;
}
async function sendAIMessage(text){
  if(!text.trim()) return;
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
}
