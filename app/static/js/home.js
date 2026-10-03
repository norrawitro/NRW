/* home.js — วาดเมนูด้านข้าง, ป้ายช่วงพัฒนา, ไอคอนระบบ, hero slides */
/* ============================================================
   RENDER: SIDEBAR
   ============================================================ */
function renderSidebar(){
  let html = `<a href="#" class="nav-item ${State.view==='home'?'active':''}" data-view="home" title="🏠 หน้าแรก — ภาพรวมทั้งหมด"><span class="ic" style="background:var(--primary-soft);color:var(--primary)">🏠</span>หน้าแรก</a>`;
  [1,2,3,4].forEach(phase=>{
    const items = MODULES.filter(m=>m.phase===phase);
    html += `<div class="nav-group-label"><span class="phase-dot" style="background:${PHASES[phase].color}"></span>${PHASES[phase].label}</div>`;
    items.forEach(m=>{
      const locked = !isLive(m);
      html += `<a href="#" class="nav-item ${locked?'locked':''} ${State.view===(m.view||m.id)?'active':''}" data-module="${m.id}" title="${m.icon} ${m.label}${locked?' (ยังไม่เปิด)':''} — ${m.reason||''}">
        <span class="ic" style="background:${PHASES[phase].color}1a;color:${PHASES[phase].color}">${m.icon}</span>${m.label}
        ${locked?'<span class="soon">เร็วๆ นี้</span>':''}
      </a>`;
    });
  });
  html += `<div class="nav-group-label">บัญชีของฉัน</div>`;
  META_ITEMS.forEach(m=>{
    const attrs = m.view ? `href="#" data-view="${m.view}"` : `href="${m.href}"`;
    html += `<a ${attrs} class="nav-item" title="${m.icon} ${m.label}"><span class="ic" style="background:var(--surface-2);color:var(--ink-soft)">${m.icon}</span>${m.label}</a>`;
  });
  if(State.me && State.me.is_admin){
    html += `<a href="/manage" class="nav-item" title="แผงผู้ดูแลระบบ"><span class="ic" style="background:var(--surface-2);color:var(--ink-soft)">🛠️</span>แผงผู้ดูแล</a>`;
  }
  if(State.me){
    html += `<a href="/members/logout" class="nav-item" title="ออกจากระบบ"><span class="ic" style="background:var(--surface-2);color:var(--ink-soft)">🚪</span>ออกจากระบบ</a>`;
  }
  document.getElementById('sidebar').innerHTML = html;
}

function renderPhaseLegend(){
  document.getElementById('phaseLegend').innerHTML = Object.entries(PHASES).map(([k,p])=>`
    <div class="item"><span class="phase-dot" style="background:${p.color}"></span>${p.label}</div>`).join('');
}

function renderLauncher(){
  document.getElementById('appGrid').innerHTML = MODULES.map(m=>{
    const locked = !isLive(m);
    return `<a href="#" class="app ${locked?'locked':''}" data-module="${m.id}" title="${m.icon} ${m.label}${locked?' — ยังไม่เปิด (เร็วๆ นี้)':''}\n${m.reason||''}">
      <div class="tile" style="background:${PHASES[m.phase].color}">${m.icon}${locked?'<span class="lock-badge">🔒</span>':''}</div>
      <div class="name">${m.label}</div>
    </a>`;
  }).join('');
}

async function renderHero(){
  // slide 1: hardcode (welcome) + slide 2: ประกาศล่าสุดจาก DB
  const posts = await fetchPosts('all');
  const latest = posts.find(p=>p.is_pinned) || posts[0];
  const slides = [
    {tag:'promo', label:'✨ ยินดีต้อนรับ', title:'Nora-Web — แพลตฟอร์มรวมทุกอย่างในที่เดียว', sub:'ครบ 20 ระบบ · ร้านค้า · คอร์สเรียน · ตลาดงาน · กิจกรรม · IoT และอีกมากมาย', bg:'linear-gradient(135deg,#4F46E5,#8B5CF6)'},
  ];
  if(latest){
    slides.push({tag:'news', label:'📢 ประกาศ', title: esc(latest.text.slice(0,80)) + (latest.text.length>80?'…':''),
      sub:`${esc(latest.author)} · ${esc(latest.when)}`, bg:'linear-gradient(135deg,#059669,#10B981)'});
  }
  document.getElementById('hero').innerHTML = slides.map((s,i)=>`
    <div class="hero-slide ${i===0?'on':''}" style="background:${s.bg}">
      <span class="hero-tag ${s.tag}">${s.label}</span>
      <div class="hero-title">${s.title}</div>
      <div class="hero-sub">${s.sub}</div>
    </div>`).join('');
}
