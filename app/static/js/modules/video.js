/* modules/video.js — วิดีโอความรู้: อัปโหลด, ดู, นับยอดวิว, ลบของตัวเอง (รหัสวิดีโอใช้แนบในคอร์สเรียนได้)
   API: GET/POST /video · GET /video/{id}/file · POST /video/{id}/view · DELETE /video/{id} */
registerModule('video', {
  sub: 'คลังวิดีโอความรู้ของสมาชิก · แนบในคอร์สเรียนได้ด้วยรหัสวิดีโอ',
  async render(el){
    const d = await api('/video'); if(!d) return;
    el.innerHTML = `<div class="m-split"><div class="m-grid m-grid-wide">${d.videos.map(v=>`<div class="m-card m-product">
        <video controls preload="metadata" src="/video/${v.id}/file" data-vid="${v.id}"></video>
        <b>${esc(v.title)}</b><p class="m-muted">${esc(v.description)}</p>
        <small class="m-muted">รหัส #${v.id} · ${esc(v.owner)} · 👁 ${v.views} · ${esc(v.date)}</small>
        ${v.is_mine?`<button class="btn-ghost m-sm" data-vdel="${v.id}">ลบ</button>`:''}</div>`).join('') || '<p class="m-muted">ยังไม่มีวิดีโอ</p>'}</div>
      <div class="m-card m-form"><h3>⬆️ อัปโหลดวิดีโอ</h3><input id="vdTitle" class="m-input" placeholder="ชื่อวิดีโอ"><textarea id="vdDesc" class="m-input" rows="2" placeholder="รายละเอียด"></textarea>
        <input id="vdFile" class="m-input" type="file" accept="video/mp4,video/webm,video/ogg,video/quicktime"><small class="m-muted">ไม่เกิน ${d.max_mb} MB</small>
        <button class="btn-primary" id="vdUp">อัปโหลด</button></div></div>`;
    el.querySelectorAll('video[data-vid]').forEach(v=>v.addEventListener('play', ()=>{ if(!v.dataset.counted){ v.dataset.counted=1; fetch(`/video/${v.dataset.vid}/view`, {method:'POST'}); } }));
    el.onclick = async e=>{
      if(e.target.dataset.vdel && confirm('ลบวิดีโอนี้?') && await api(`/video/${e.target.dataset.vdel}`, {method:'DELETE'})) this.render(el);
      if(e.target.id==='vdUp'){
        if(!State.me) return toast('กรุณาเข้าสู่ระบบก่อน');
        const f = document.getElementById('vdFile').files[0], title = document.getElementById('vdTitle').value.trim();
        if(!f || !title) return toast('กรุณาใส่ชื่อและเลือกไฟล์');
        const fd = new FormData(); fd.append('file', f); fd.append('title', title); fd.append('description', document.getElementById('vdDesc').value);
        e.target.disabled = true; e.target.textContent = 'กำลังอัปโหลด…';
        const r = await api('/video', {method:'POST', body:fd});
        e.target.disabled = false; e.target.textContent = 'อัปโหลด';
        if(r){ toast(`อัปโหลดแล้ว (รหัส #${r.id})`); this.render(el); }
      }
    };
  },
});
