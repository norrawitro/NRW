/* modules/search.js — ช่องค้นหาด้านบน: หาระบบ, หน้าช่วยเหลือ, สินค้า, ประกาศ (ใช้ลูกศร ↑↓ + Enter ได้) */
(function(){
  const input = document.getElementById('searchInput');
  const box = document.getElementById('searchResults');
  let items = [], sel = -1, products = null;
  const INFO = [['help','❓','คู่มือการใช้งาน'],['about','ℹ️','เกี่ยวกับ Nora-Web'],['privacy','🔒','นโยบายความเป็นส่วนตัว'],
                ['terms','📜','เงื่อนไขการใช้งาน'],['contact','✉️','ติดต่อทีมงาน']];

  async function loadProducts(){
    if(products) return;
    try{ products = (await (await fetch('/shop/products')).json()).products || []; }catch(e){ products = []; }
  }
  function run(q){
    q = q.trim().toLowerCase();
    if(!q){ box.classList.add('hidden'); return; }
    const has = s => String(s||'').toLowerCase().includes(q);
    items = [
      ...MODULES.filter(m=>has(m.label)||has(m.reason)).map(m=>({icon:m.icon, label:m.label, sub:isLive(m)?'เปิดใช้งาน':'เร็วๆ นี้', go:()=>isLive(m)?showView(m.view||m.id):openDrawer(m.id)})),
      ...INFO.filter(i=>has(i[2])).map(([a,ic,l])=>({icon:ic, label:l, sub:'ช่วยเหลือ', go:()=>showView('info', a)})),
      ...(products||[]).filter(p=>has(p.name)||has(p.description)).slice(0,5).map(p=>({icon:'🛒', label:p.name, sub:baht(p.price), go:()=>showView('shop')})),
      ...Object.values(State.postsCache||{}).filter(p=>has(p.text)).slice(0,5).map(p=>({icon:'📰', label:p.text.slice(0,60), sub:p.author, go:()=>showView('news')})),
    ].slice(0,10);
    sel = items.length ? 0 : -1;
    draw();
  }
  function draw(){
    box.innerHTML = items.length ? items.map((it,i)=>`<a data-sr="${i}" class="${i===sel?'sel':''}"><span>${it.icon}</span><span>${esc(it.label)}</span><span class="sr-kind">${esc(it.sub)}</span></a>`).join('')
      : '<div class="sr-empty">ไม่พบผลลัพธ์</div>';
    box.classList.remove('hidden');
  }
  function open(i){ const it = items[i]; box.classList.add('hidden'); input.value=''; if(it) it.go(); }

  input.addEventListener('focus', ()=>{ if(input.value) run(input.value); });
  input.addEventListener('input', async ()=>{ run(input.value); if(!products){ await loadProducts(); run(input.value); } });
  input.addEventListener('keydown', e=>{
    if(e.key==='Escape'){ box.classList.add('hidden'); input.blur(); }
    if(!items.length) return;
    if(e.key==='ArrowDown'||e.key==='ArrowUp'){ e.preventDefault(); sel=(sel+(e.key==='ArrowDown'?1:-1)+items.length)%items.length; draw(); }
    if(e.key==='Enter' && sel>=0){ e.preventDefault(); open(sel); }
  });
  box.addEventListener('mousedown', e=>{ const a = e.target.closest('[data-sr]'); if(a){ e.preventDefault(); open(+a.dataset.sr); } });
  document.addEventListener('click', e=>{ if(!e.target.closest('.search')) box.classList.add('hidden'); });
})();
