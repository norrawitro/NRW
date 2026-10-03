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

  // สถิติ + โพสต์ของฉัน
  const CAT = {announce:'ประกาศ', update:'อัปเดตระบบ', event:'กิจกรรม'};
  (async ()=>{
    try{
      const a = await (await fetch('/analytics/me', {credentials:'same-origin'})).json();
      $('st-posts').textContent = a.posts; $('st-orders').textContent = a.orders;
      $('st-balance').textContent = '฿' + Number(a.balance).toLocaleString('th-TH', {maximumFractionDigits:0});
      $('st-token').textContent = Number(a.token).toLocaleString();
    }catch(e){}
    try{
      const d = await (await fetch('/members/me/posts', {credentials:'same-origin'})).json();
      $('myPosts').innerHTML = d.posts.length ? d.posts.map(p=>`<div class="post-card">
        <div class="post-header"><span class="post-cat">${esc(CAT[p.cat]||p.cat)}</span><span class="post-date">${esc(p.when)}</span></div>
        <div class="post-text">${esc(p.text)}</div><div class="post-footer"><span class="post-stat">👍 ${p.likes}</span><span class="post-stat">💬 ${p.comments}</span></div></div>`).join('')
        : `<div class="empty-state"><div class="empty-ico">📭</div><p>ยังไม่มีโพสต์</p><p style="font-size:.8rem;margin-top:6px">ไปที่หน้า <a href="/#news" style="color:var(--primary);font-weight:600">ข่าวสาร</a> เพื่อเขียนโพสต์แรก</p></div>`;
    }catch(e){}
  })();
})();
