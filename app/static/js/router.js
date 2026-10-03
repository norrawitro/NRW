/* router.js — showView() สลับหน้า + หน้าต่างรายละเอียดระบบที่ยังไม่เปิด (drawer) */
/* ============================================================
   ROUTER
   ============================================================ */
function showView(view, anchor){
  if(!document.getElementById('view-'+view) && !MODULE_VIEWS[view]) view = 'home';
  State.view = view;
  history.replaceState(null, '', view==='home' ? location.pathname : '#'+view);
  State.anchor = anchor;
  document.querySelectorAll('.view-section').forEach(v=>v.classList.add('hidden'));
  document.body.classList.remove('sidebar-open');
  let target = document.getElementById('view-'+view);
  if(!target && MODULE_VIEWS[view]){ target = document.getElementById('view-module'); renderModuleView(view, target); }
  if(target) target.classList.remove('hidden');
  renderSidebar();
  window.scrollTo({top:0, behavior:'smooth'});
  if(view==='news'){ renderNewsComposerCats(); renderNewsFilters(); renderNewsFeed(); }
  if(view==='cloud'){ fetchCloud().then(()=>{ renderStorage(); renderBreadcrumb(); renderFileGrid(); }); }
  if(view==='wallet'){ fetchWallet().then(()=>{ renderWallet(); updateWalletChips(); }); }
  if(view==='ai'){ renderAIQuick(); renderAIMessages(); }
  if(view==='home'){ renderHomeFeed(); if(typeof loadHomeAd==='function') loadHomeAd(); }
}

/** วาดหน้าของระบบที่ register ไว้ใน js/modules/ */
function renderModuleView(id, el){
  const m = MODULES.find(x=>x.id===id) || {icon:'ℹ️', label:MODULE_VIEWS[id].title||id, phase:1, code:'—', reason:''};
  const ph = PHASES[m.phase];
  el.innerHTML = `<div class="view-header">
      <a class="back-link" href="#" data-view="home">← หน้าแรก</a>
      <div><div class="view-title">${m.icon} ${esc(m.label)} ${m.code!=='—'?`<span class="m-phase" style="color:${ph.color}">รหัส ${m.code} · ช่วงที่ ${m.phase}</span>`:''}</div>
        <div class="view-sub">${esc(MODULE_VIEWS[id].sub || m.reason || '')}</div></div>
    </div><div id="moduleBody"></div>`;
  MODULE_VIEWS[id].render(document.getElementById('moduleBody'));
}

/* ============================================================
   MODULE DETAIL DRAWER (ระบบที่ยังไม่เปิดใช้งาน)
   ============================================================ */
function openDrawer(moduleId){
  const m = MODULES.find(x=>x.id===moduleId);
  if(!m) return;
  const followed = !!State.followed[m.id];
  document.getElementById('drawerContent').innerHTML = `
    <div class="dtile" style="background:${PHASES[m.phase].color}" title="${m.icon} ${m.label}">${m.icon}</div>
    <h3>${m.label}</h3>
    <div class="code">รหัสระบบ #${m.code}</div>
    <span class="phase-pill" style="background:${PHASES[m.phase].color}1a;color:${PHASES[m.phase].color}">${PHASES[m.phase].dot} ${PHASES[m.phase].label}</span>
    <h4>เหตุผลที่จัดลำดับไว้ตรงนี้</h4>
    <p>${m.reason}</p>
    <h4>เชื่อมโยงกับระบบ</h4>
    <div class="conn-list">${m.conn.map(c=>`<span>🔗 ${c}</span>`).join('')}</div>
    <button class="follow-btn ${followed?'on':''}" id="followBtn" title="${followed?'คลิกเพื่อยกเลิกการติดตาม':'คลิกเพื่อรับแจ้งเตือนเมื่อระบบนี้พร้อมใช้งาน'}">${followed?'✓ ติดตามแล้ว':'🔔 แจ้งเตือนเมื่อพร้อมใช้งาน'}</button>
  `;
  document.getElementById('followBtn').onclick = ()=>{
    State.followed[m.id] = !State.followed[m.id];
    openDrawer(moduleId);
  };
  document.getElementById('drawerOverlay').classList.add('open');
  document.getElementById('moduleDrawer').classList.add('open');
}
function closeDrawer(){
  document.getElementById('drawerOverlay').classList.remove('open');
  document.getElementById('moduleDrawer').classList.remove('open');
}
