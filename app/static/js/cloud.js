/* cloud.js — คลาวด์: แถบพื้นที่, breadcrumb, ตารางไฟล์ */
/* ============================================================
   RENDER: CLOUD
   ============================================================ */
function renderStorage(){
  const s = State.storage;
  const usedTxt = s.used_bytes>0 && s.used<0.01 ? fmtSize(s.used_bytes) : `${s.used} GB`;
  document.getElementById('storageText').textContent = `${usedTxt} / ${s.total} GB`;
  document.getElementById('storageFill').style.width = Math.min(100, (s.used/s.total*100)).toFixed(1)+'%';
}
function renderBreadcrumb(){
  document.getElementById('cloudBreadcrumb').innerHTML = State.cloudPath.map((p,i)=>
    `<span class="seg" data-crumb="${i}">${esc(p.name)}</span>${i<State.cloudPath.length-1?'<span>›</span>':''}`).join('');
}
function renderFileGrid(){
  const current = State.cloudPath[State.cloudPath.length-1].id;
  const items = DataLayer.getCloudItems(current);
  document.getElementById('fileGrid').innerHTML = items.length ? items.map(it=>`
    <div class="file-card" data-item="${it.id}" data-type="${it.type}" title="${it.icon} ${esc(it.name)}${it.type==='folder'?' (โฟลเดอร์ '+it.count+' ไฟล์)':' ('+fmtSize(it.size)+')'}">
      <button class="del" data-del="${it.id}" data-del-type="${it.type}" title="ลบ ${esc(it.name)}">🗑️</button>
      <div class="fic">${it.icon}</div>
      <div class="fn">${esc(it.name)}</div>
      <div class="fm">${it.type==='folder' ? (it.count+' ไฟล์') : fmtSize(it.size)}</div>
    </div>`).join('') : `<p style="color:var(--ink-soft);font-size:14px;grid-column:1/-1;text-align:center;padding:30px;">โฟลเดอร์นี้ว่างเปล่า</p>`;
}
