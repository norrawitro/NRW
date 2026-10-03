/* profile.js — หน้าโปรไฟล์ (/members/profile): แก้ชื่อ/email/เบอร์/รหัสผ่าน, สถิติจริง, โพสต์ของฉัน, ธีมมืด
   API: GET/PATCH /members/me · POST /members/me/password · GET /members/me/posts · GET /analytics/me */
(function(){
  const $ = id => document.getElementById(id);
  const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  let _t; const toast = m => { const t=$('toast'); t.textContent=m; t.classList.add('on'); clearTimeout(_t); _t=setTimeout(()=>t.classList.remove('on'),2500); };

  // ธีมมืด (key เดียวกับหน้าหลัก)
  const getDark = ()=>{ try{ return JSON.parse(localStorage.getItem('nrw_dark')||'false'); }catch(e){ return false; } };
  const applyDark = d => { document.documentElement.setAttribute('data-theme', d?'dark':''); if($('darkToggle')) $('darkToggle').checked = d; };
  applyDark(getDark());
  if($('darkToggle')) $('darkToggle').onchange = e => { try{ localStorage.setItem('nrw_dark', JSON.stringify(e.target.checked)); }catch(err){} applyDark(e.target.checked); };

  // แก้ไขข้อมูล
  const FIELDS = {
    full_name:{title:'แก้ไขชื่อ-นามสกุล', inputs:[['full_name','ชื่อ-นามสกุล','text']]},
    email:{title:'แก้ไข Email', inputs:[['email','Email','email']]},
    phone:{title:'แก้ไขเบอร์โทรศัพท์', inputs:[['phone','เบอร์โทร (เว้นว่างเพื่อลบ)','tel']]},
    password:{title:'เปลี่ยนรหัสผ่าน', inputs:[['current','รหัสผ่านปัจจุบัน','password'],['new','รหัสผ่านใหม่ (อย่างน้อย 8 ตัว)','password'],['confirm','ยืนยันรหัสผ่านใหม่','password']]},
  };
  let editing = null;
  function open(key){
    editing = key;
    $('modalTitle').textContent = FIELDS[key].title;
    $('modalFields').innerHTML = FIELDS[key].inputs.map(([n,l,t])=>{
      const cur = key==='password' ? '' : (($('v-'+n)||{}).textContent||'').trim();
      return `<label for="f-${n}">${l}</label><input id="f-${n}" name="${n}" type="${t}" value="${esc(cur==='—'?'':cur)}">`;
    }).join('');
    $('modalErr').textContent = '';
    $('modalBg').classList.add('open');
    $('modalFields').querySelector('input').focus();
  }
  const close = ()=>{ $('modalBg').classList.remove('open'); editing = null; };
  document.querySelectorAll('[data-edit]').forEach(b=>b.addEventListener('click', ()=>open(b.dataset.edit)));
  $('modalCancel').onclick = close;
  $('modalBg').addEventListener('click', e=>{ if(e.target.id==='modalBg') close(); });
  $('modalForm').onsubmit = async e=>{
    e.preventDefault();
    const v = Object.fromEntries(new FormData(e.target).entries());
    let url = '/members/me', method = 'PATCH', body = v;
    if(editing==='password'){
      if(v.new !== v.confirm){ $('modalErr').textContent = 'รหัสผ่านใหม่ไม่ตรงกัน'; return; }
      url = '/members/me/password'; method = 'POST'; body = {current:v.current, new:v.new};
    }
    $('modalSave').disabled = true;
    try{
      const r = await fetch(url, {method, headers:{'Content-Type':'application/json'}, body:JSON.stringify(body), credentials:'same-origin'});
      const d = await r.json().catch(()=>({}));
      if(r.status===401){ window.location='/members/login'; return; }
      if(!r.ok){ $('modalErr').textContent = typeof d.detail==='string' ? d.detail : 'ข้อมูลไม่ถูกต้อง (เช่น email ผิดรูปแบบ หรือรหัสสั้นเกินไป)'; return; }
      if(editing!=='password') ['full_name','email','phone'].forEach(k=>{ if(k in d && $('v-'+k)) $('v-'+k).textContent = d[k] || '—'; });
      toast(editing==='password' ? 'เปลี่ยนรหัสผ่านแล้ว' : 'บันทึกแล้ว');
      close();
    } finally{ $('modalSave').disabled = false; }
  };

  // สถิติ
  (async ()=>{
    try{
      const a = await (await fetch('/analytics/me', {credentials:'same-origin'})).json();
      $('st-posts').textContent = a.posts; $('st-orders').textContent = a.orders;
      $('st-balance').textContent = '฿' + Number(a.balance).toLocaleString('th-TH', {maximumFractionDigits:0});
      $('st-token').textContent = Number(a.token).toLocaleString();
    }catch(e){}
  })();

  // โพสต์ของฉัน — โครงเดียวกับ "ประกาศจากระบบ": กดถูกใจ, ดู/เขียนความเห็น, ลบ
  const CAT = {announce:['ประกาศ','#4F46E5'], update:['อัปเดตระบบ','#06B6D4'], event:['กิจกรรม','#F59E0B']};
  const call = async (url, opts={}) => {
    if(opts.json !== undefined){ opts.method = opts.method||'POST'; opts.headers = {'Content-Type':'application/json'}; opts.body = JSON.stringify(opts.json); delete opts.json; }
    const r = await fetch(url, {credentials:'same-origin', ...opts});
    const d = await r.json().catch(()=>null);
    if(!r.ok){ toast((d && typeof d.detail==='string') ? d.detail : 'เกิดข้อผิดพลาด'); return null; }
    return d;
  };
  function postCard(p){
    const [label, color] = CAT[p.cat] || [p.cat, '#5B5F76'];
    const mod = p.mod ? `<span class="pp-badge ${p.mod.status==='rejected'?'no':''}">${p.mod.status==='pending'?'⏳ รอผู้ดูแลอนุมัติ':'❌ ไม่อนุมัติ'+(p.mod.reason?': '+esc(p.mod.reason):'')}</span>` : '';
    return `<div class="pp-post" id="pp-${p.id}"><div class="pp-head"><div class="pp-av" style="background:${color}">${esc((p.author||'?')[0])}</div>
        <div><b style="font-size:.88rem">${esc(p.author)}</b><div style="font-size:.75rem;color:var(--ink-soft)">${esc(p.when)}</div></div>
        <span class="pp-tag" style="background:${color}1a;color:${color}">${esc(label)}</span>
        <button data-pdel="${p.id}" title="ลบโพสต์" style="background:none;border:none;cursor:pointer;color:var(--danger)">🗑️</button></div>
      ${mod ? `<div style="margin-bottom:6px">${mod}</div>` : ''}<div class="pp-body">${esc(p.text)}</div>
      <div class="pp-acts"><button class="${p.liked?'liked':''}" data-plike="${p.id}">👍 ${p.liked?'ถูกใจแล้ว':'ถูกใจ'} ${p.likes?'('+p.likes+')':''}</button>
        <button data-ptoggle="${p.id}">💬 ความเห็น ${p.comments?'('+p.comments+')':''}</button></div>
      <div class="pp-comments" id="ppc-${p.id}"><div id="ppcl-${p.id}"></div>
        <div class="pp-cin"><input id="ppci-${p.id}" maxlength="1000" placeholder="เขียนความเห็น…"><button data-psend="${p.id}">ส่ง</button></div></div></div>`;
  }
  async function loadPosts(){
    const d = await call('/news/posts?mine=true&limit=50');
    const posts = d ? d.posts : [];
    $('myPosts').innerHTML = `<div class="pp-compose"><textarea id="ppNew" rows="2" maxlength="5000" placeholder="เขียนโพสต์ใหม่…"></textarea>
        <select id="ppCat" style="border-radius:10px;border:1.5px solid var(--line);background:var(--surface-2);color:var(--ink)"><option value="announce">ประกาศ</option><option value="update">อัปเดตระบบ</option><option value="event">กิจกรรม</option></select>
        <button class="btn-p" id="ppPost">โพสต์</button></div>` +
      (posts.length ? posts.map(postCard).join('') : `<div class="empty-state"><div class="empty-ico">📭</div><p>ยังไม่มีโพสต์ — เขียนโพสต์แรกด้านบนได้เลย</p></div>`);
  }
  async function loadComments(id){
    const d = await call(`/news/posts/${id}/comments`); if(!d) return;
    $('ppcl-'+id).innerHTML = d.comments.length ? d.comments.map(c=>`<div class="pp-c"><div class="pp-cav">${esc((c.author||'?')[0])}</div>
      <div class="pp-cbody"><div style="font-size:.7rem;color:var(--ink-soft);font-weight:600">${esc(c.author)} · ${esc(c.when)}</div>${esc(c.text)}</div></div>`).join('')
      : '<p style="font-size:.75rem;color:var(--ink-soft)">ยังไม่มีความเห็น</p>';
  }
  $('myPosts').addEventListener('click', async e=>{
    const b = e.target.closest('button'); if(!b) return;
    const d = b.dataset;
    if(b.id==='ppPost'){
      const text = $('ppNew').value.trim(); if(!text) return;
      if(await call('/news/posts', {json:{text, cat:$('ppCat').value}})){ toast('โพสต์แล้ว'); loadPosts(); }
    }
    if(d.plike){ const r = await call(`/news/posts/${d.plike}/like`, {method:'POST'});
      if(r){ b.classList.toggle('liked', r.liked); b.textContent = `👍 ${r.liked?'ถูกใจแล้ว':'ถูกใจ'} ${r.likes?'('+r.likes+')':''}`; } }
    if(d.ptoggle){ const sec = $('ppc-'+d.ptoggle); if(sec.classList.toggle('open')) loadComments(d.ptoggle); }
    if(d.psend){ const inp = $('ppci-'+d.psend), text = inp.value.trim(); if(!text) return;
      if(await call(`/news/posts/${d.psend}/comments`, {json:{text}})){ inp.value = ''; loadComments(d.psend); } }
    if(d.pdel && confirm('ลบโพสต์นี้?') && await call(`/news/posts/${d.pdel}`, {method:'DELETE'})){ toast('ลบแล้ว'); loadPosts(); }
  });
  $('myPosts').addEventListener('keydown', e=>{ if(e.key==='Enter' && e.target.id && e.target.id.startsWith('ppci-')) e.target.nextElementSibling.click(); });
  loadPosts();
})();
