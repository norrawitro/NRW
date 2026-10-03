/* manage_content.js — แท็บ "อนุมัติเนื้อหา" ในแผงผู้ดูแล: ตรวจโพสต์/สินค้า/ประกาศ/คอร์ส/งาน/โฆษณา/วิดีโอ/กิจกรรม/โพสต์ครีเอเตอร์/หลักฐานออกกำลังกาย
   API: GET /manage/api/moderation?status=&kind= · POST /manage/api/moderation/{id}/approve|reject {reason} */
Tabs.content = async function(){
  $('body').innerHTML = `<div class="m-card"><div class="m-row" style="flex-wrap:wrap">
      <select id="mcStatus" class="m-input" style="max-width:180px"><option value="pending">รออนุมัติ</option><option value="approved">อนุมัติแล้ว</option><option value="rejected">ไม่อนุมัติ</option></select>
      <select id="mcKind" class="m-input" style="max-width:240px"><option value="">ทุกประเภท</option></select></div>
    <div id="mcList"><p class="m-muted">กำลังโหลด…</p></div></div>`;
  $('mcStatus').onchange = $('mcKind').onchange = ()=>Tabs.loadContent();
  Tabs.loadContent(true);
};

Tabs.loadContent = async function(first){
  const d = await api(`/manage/api/moderation?status=${$('mcStatus').value}&kind=${$('mcKind').value}`); if(!d) return;
  const total = Object.values(d.pending_counts).reduce((a,b)=>a+b, 0);
  $('pendingCount').textContent = total ? `(${total})` : '';
  if(first) $('mcKind').innerHTML = '<option value="">ทุกประเภท</option>' + Object.entries(d.labels).map(([k,l])=>
    `<option value="${k}">${esc(l)}${d.pending_counts[k]?` (${d.pending_counts[k]})`:''}</option>`).join('');
  $('mcList').innerHTML = d.items.length ? d.items.map(i=>`<div class="m-card mc-item">
      <div class="mc-media">${i.video ? `<video controls preload="none" src="${esc(i.video)}"></video>`
        : i.image ? `<a href="${esc(i.image)}" target="_blank"><img src="${esc(i.image)}" alt="ดูรูปเต็ม"></a>` : `<div class="m-noimg">${esc(i.kind_label.split(' ')[0])}</div>`}</div>
      <div><small class="m-muted">${esc(i.kind_label)} · โดย ${esc(i.owner)} · ${esc(i.date)}</small>
        <h3>${esc(i.title)}</h3><div class="m-pre">${esc(i.detail)}</div>
        ${i.link ? `<p class="m-muted">ลิงก์: ${esc(i.link)}</p>` : ''}
        ${i.status!=='pending' ? `<p class="m-muted">${i.status==='approved'?'✅ อนุมัติ':'❌ ไม่อนุมัติ'}โดย ${esc(i.decided_by||'—')}${i.reason?` · เหตุผล: ${esc(i.reason)}`:''}</p>` : ''}
        <div class="mc-acts">${i.status!=='approved'?`<button class="btn-primary m-sm" data-mc="${i.id}" data-mcact="approve">✅ อนุมัติ</button>`:''}
          ${i.status!=='rejected'?`<button class="btn-ghost m-sm" data-mc="${i.id}" data-mcact="reject">${i.status==='approved'?'🚫 ซ่อน/ถอนการอนุมัติ':'❌ ไม่อนุมัติ'}</button>`:''}</div></div></div>`).join('')
    : '<p class="m-muted" style="padding:20px 0">ไม่มีรายการ 🎉</p>';
};

document.addEventListener('click', async e=>{
  const b = e.target.closest('[data-mc]'); if(!b) return;
  let reason = '';
  if(b.dataset.mcact==='reject'){ reason = prompt('เหตุผล (เจ้าของจะเห็นข้อความนี้)'); if(!reason) return; }
  if(await api(`/manage/api/moderation/${b.dataset.mc}/${b.dataset.mcact}`, {json:{reason}})){ toast(b.dataset.mcact==='approve'?'อนุมัติแล้ว':'บันทึกแล้ว'); Tabs.loadContent(); }
});
Tabs.content();
