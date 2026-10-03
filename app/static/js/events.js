/* events.js — ผูกปุ่มและคลิกทั้งหมด (event wiring) */
/* ============================================================
   EVENT WIRING
   ============================================================ */
document.getElementById('hamburger').onclick = ()=>{
  // มือถือ: เปิด/ปิดเมนูแบบลอย  ·  จอใหญ่: ซ่อน/แสดงเมนู
  document.body.classList.toggle(window.innerWidth<=880 ? 'sidebar-open' : 'sidebar-collapsed');
};
document.getElementById('themeBtn').onclick = ()=>{
  State.dark = !State.dark;
  try{ localStorage.setItem('nrw_dark', JSON.stringify(State.dark)); }catch(e){}
  applyTheme();
};
document.getElementById('drawerOverlay').onclick = closeDrawer;
document.getElementById('drawerClose').onclick = closeDrawer;
document.getElementById('submitPost').onclick = submitPostFn;

document.addEventListener('click', async (e)=>{

  // ── like ──────────────────────────────────────────────────
  const likeBtn = e.target.closest('.like-btn[data-like]');
  if(likeBtn){ await toggleLike(likeBtn.dataset.like, likeBtn); return; }

  // ── share post ────────────────────────────────────────────
  const shareBtn = e.target.closest('.share-btn[data-share]');
  if(shareBtn){
    const post = State.postsCache[shareBtn.dataset.share];
    const text = post ? post.text.slice(0,50) : '';
    const url = window.location.href;
    if(navigator.share){
      try{ await navigator.share({title:'WKW', text, url}); }catch(err){ /* user cancelled */ }
    } else if(navigator.clipboard){
      try{ await navigator.clipboard.writeText(text ? text+'… '+url : url); alert('คัดลอกลิงก์แล้ว'); }catch(err){ alert('คัดลอกไม่ได้ — '+url); }
    }
    return;
  }

  // ── comment toggle ────────────────────────────────────────
  const commentToggleBtn = e.target.closest('.comment-toggle-btn[data-comment-toggle]');
  if(commentToggleBtn){
    const pid = commentToggleBtn.dataset.commentToggle;
    const sec = document.getElementById(`comments-${pid}`);
    const isOpen = sec.classList.toggle('open');
    if(isOpen) await loadComments(pid);
    return;
  }

  // ── delete post ───────────────────────────────────────────
  const delPostBtn = e.target.closest('[data-del-post]');
  if(delPostBtn){
    if(!confirm('ลบโพสต์นี้?')) return;
    const r = await fetch(`/news/posts/${delPostBtn.dataset.delPost}`, {method:'DELETE'});
    if(r.ok){ await renderNewsFeed(); await renderHomeFeed(); }
    return;
  }

  // ── data-view (SPA navigation) ────────────────────────────
  const viewEl = e.target.closest('[data-view]');
  if(viewEl){ e.preventDefault(); closeDrawer(); showView(viewEl.dataset.view, viewEl.dataset.anchor); return; }

  // ── data-module ───────────────────────────────────────────
  const modEl = e.target.closest('[data-module]');
  if(modEl){
    e.preventDefault();
    const m = MODULES.find(x=>x.id===modEl.dataset.module);
    if(!m) return;
    if(isLive(m)){ showView(m.view||m.id); } else { openDrawer(m.id); }
    return;
  }

  // ── news filter ───────────────────────────────────────────
  const filterEl = e.target.closest('[data-filter]');
  if(filterEl){ State.newsFilter = filterEl.dataset.filter; renderNewsFilters(); renderNewsFeed(); return; }

  // ── post category chip ────────────────────────────────────
  const catEl = e.target.closest('#newPostCatRow [data-cat]');
  if(catEl){ document.querySelectorAll('#newPostCatRow .cat-chip').forEach(c=>c.classList.remove('on')); catEl.classList.add('on'); return; }

  // ── cloud breadcrumb ──────────────────────────────────────
  const crumbEl = e.target.closest('[data-crumb]');
  if(crumbEl){ State.cloudPath = State.cloudPath.slice(0, +crumbEl.dataset.crumb+1); renderBreadcrumb(); fetchCloud().then(renderFileGrid); return; }

  // ── delete cloud item ─────────────────────────────────────
  const delEl = e.target.closest('[data-del]');
  if(delEl){ e.stopPropagation(); if(!confirm('ลบรายการนี้?')) return; DataLayer.deleteCloudItem(delEl.dataset.del, delEl.dataset.delType); return; }

  // ── open cloud folder ─────────────────────────────────────
  const cardEl = e.target.closest('.file-card');
  if(cardEl && !e.target.closest('[data-del]')){
    const item = State.cloudItems.find(i=>String(i.id)===cardEl.dataset.item && i.type===cardEl.dataset.type);
    if(item && item.type==='folder'){ State.cloudPath.push({id:item.id, name:item.name}); renderBreadcrumb(); fetchCloud().then(renderFileGrid); }
    else if(item && item.type==='file'){ window.location = `/cloud/download/${item.id}`; }
    return;
  }

  // ── AI quick reply ────────────────────────────────────────
  const quickEl = e.target.closest('[data-quick]');
  if(quickEl){ sendAIMessage(quickEl.dataset.quick); return; }
});

document.getElementById('uploadBtn').onclick = ()=>{
  const input = document.createElement('input');
  input.type = 'file';
  input.onchange = async ()=>{
    if(!input.files || !input.files[0]) return;
    const btn = document.getElementById('uploadBtn');
    btn.disabled = true; btn.textContent = 'กำลังอัปโหลด…';
    const current = State.cloudPath[State.cloudPath.length-1].id;
    const fd = new FormData();
    fd.append('file', input.files[0]);
    if(current!==null) fd.append('folder_id', current);
    try{
      const r = await fetch('/cloud/upload', {method:'POST', body: fd});
      if(r.status===401){ alert('กรุณาเข้าสู่ระบบก่อน'); window.location='/members/login'; return; }
      if(!r.ok){ const er=await r.json(); alert(er.detail||'อัปโหลดล้มเหลว'); return; }
      await fetchCloud();
      renderStorage(); renderFileGrid();
    } finally{ btn.disabled=false; btn.textContent='⬆️ อัปโหลดไฟล์'; }
  };
  input.click();
};
document.getElementById('newFolderBtn').onclick = async ()=>{
  const name = prompt('ชื่อโฟลเดอร์ใหม่:');
  if(!name || !name.trim()) return;
  const current = State.cloudPath[State.cloudPath.length-1].id;
  await DataLayer.addCloudFolder(name.trim(), current);
};

let pendingTxType = null;
document.getElementById('topupBtn').onclick = ()=>{ pendingTxType='topup'; document.getElementById('txForm').classList.remove('hidden'); };
document.getElementById('withdrawBtn').onclick = ()=>{ pendingTxType='withdraw'; document.getElementById('txForm').classList.remove('hidden'); };
document.getElementById('txConfirm').onclick = async ()=>{
  const val = parseFloat(document.getElementById('txAmount').value);
  if(!val || val<=0) return;
  const btn = document.getElementById('txConfirm');
  btn.disabled = true; btn.textContent = 'กำลังทำ…';
  const note = document.getElementById('txNote').value.trim();
  const res = await DataLayer.addTransaction(
    note || (pendingTxType==='topup' ? 'เติมเงินเข้ากระเป๋า' : 'ถอนเงินออกจากกระเป๋า'),
    val, pendingTxType
  );
  btn.disabled = false; btn.textContent = 'ส่งคำขอ';
  if(res === null) return;  // ผิดพลาด (alert แล้ว)
  toast(pendingTxType==='topup' ? 'ส่งคำขอเติมเงินแล้ว — รอผู้ดูแลอนุมัติ' : 'ส่งคำขอถอนแล้ว — กันยอดไว้ รอผู้ดูแลโอน');
  document.getElementById('txAmount').value=''; document.getElementById('txNote').value='';
  document.getElementById('txForm').classList.add('hidden');
  renderWallet(); updateWalletChips();
};

document.getElementById('aiSend').onclick = ()=>{
  const input = document.getElementById('aiInput');
  sendAIMessage(input.value);
  input.value='';
};
document.getElementById('aiInput').addEventListener('keydown', (e)=>{
  if(e.key==='Enter'){ document.getElementById('aiSend').click(); }
});
