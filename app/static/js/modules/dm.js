/* modules/dm.js — ข้อความส่วนตัว (Direct Message): กล่องข้อความ, ค้นหาสมาชิก, คุย 1-1 แนบรูปได้
   เปิดคุยกับใครจากที่ไหนก็ได้: openDm('username') หรือปุ่ม dmButton('username') (ui_kit.js)
   API: GET /dm/inbox · GET /dm/users?q= · GET/POST /dm/with/{username} · GET /dm/unread */
registerModule('dm', {
  sub: 'ส่งข้อความส่วนตัวถึงสมาชิกคนไหนก็ได้ · นัดรับของ คุยงาน ต่อรองราคา แนบรูปได้',
  async render(el){
    if(!State.me){ loginGate(el, 'ข้อความส่วนตัว'); return; }
    this.el = el; this.peer = State.dmTarget || this.peer || null; State.dmTarget = null; this.last = 0;
    el.innerHTML = `<div class="dm-wrap ${this.peer?'has-peer':''}" id="dmWrap">
      <div class="m-card dm-side"><input id="dmSearch" class="m-input" placeholder="🔍 ค้นหาสมาชิก (ชื่อ หรือ username)" autocomplete="off">
        <div id="dmFound"></div><div id="dmInbox"><p class="m-muted">กำลังโหลด…</p></div></div>
      <div class="m-card dm-main" id="dmMain"></div></div>`;
    el.onclick = e=>{
      const c = e.target.closest('[data-peer]'); if(c){ e.preventDefault(); return this.open(c.dataset.peer); }
      if(e.target.id==='dmSend') return this.send();
      if(e.target.id==='dmBack'){ this.peer = null; document.getElementById('dmWrap').classList.remove('has-peer'); this.drawMain(); }
    };
    let t; document.getElementById('dmSearch').oninput = e=>{ clearTimeout(t); t = setTimeout(()=>this.search(e.target.value.trim()), 250); };
    this.drawMain(); await this.loadInbox();
    if(this.peer) this.open(this.peer);
    clearInterval(this.timer);
    this.timer = setInterval(()=>{ if(State.view!=='dm'){ clearInterval(this.timer); return; }
      this.tick = (this.tick||0)+1; if(this.peer) this.poll(); if(this.tick%4===0) this.loadInbox(); }, 3000);
  },
  async loadInbox(){
    const d = await api('/dm/inbox'); const box = document.getElementById('dmInbox'); if(!d || !box) return;
    box.innerHTML = d.conversations.length ? d.conversations.map(c=>`<a href="#" class="dm-conv ${c.username===this.peer?'on':''}" data-peer="${esc(c.username)}">
        <span class="dm-av">${esc(c.initial)}</span><span class="dm-meta"><b>${esc(c.name)}</b><small>${esc(c.last)}</small></span>
        <span class="dm-right"><small class="m-muted">${esc(c.time.split(' ')[1]||'')}</small>${c.unread?`<b class="dm-badge">${c.unread}</b>`:''}</span></a>`).join('')
      : '<p class="m-muted">ยังไม่มีข้อความ — ค้นหาสมาชิกด้านบนเพื่อเริ่มคุย</p>';
    refreshBadges();
  },
  async search(q){
    const box = document.getElementById('dmFound');
    if(!q){ box.innerHTML = ''; return; }
    const d = await api('/dm/users?q='+encodeURIComponent(q)); if(!d) return;
    box.innerHTML = d.users.map(u=>`<a href="#" class="dm-conv" data-peer="${esc(u.username)}"><span class="dm-av">${esc(u.initial)}</span>
      <span class="dm-meta"><b>${esc(u.name)}</b><small>@${esc(u.username)}</small></span></a>`).join('') || '<p class="m-muted">ไม่พบสมาชิก</p>';
  },
  drawMain(){
    const main = document.getElementById('dmMain'); if(!main) return;
    if(!this.peer){ main.innerHTML = '<div class="m-center dm-empty"><div style="font-size:42px">✉️</div><p class="m-muted">เลือกบทสนทนา หรือค้นหาสมาชิกเพื่อเริ่มคุย</p></div>'; return; }
    main.innerHTML = `<div class="dm-head"><button class="btn-ghost m-sm" id="dmBack">←</button><b id="dmPeerName">@${esc(this.peer)}</b></div>
      <div class="m-chat-log dm-log" id="dmLog"></div>
      <div class="dm-compose">${imagePicker('dm')}<div class="m-row"><input id="dmText" class="m-input" maxlength="2000" placeholder="พิมพ์ข้อความ… (Enter เพื่อส่ง)"><button class="btn-primary" id="dmSend">ส่ง</button></div></div>`;
    document.getElementById('dmText').onkeydown = e=>{ if(e.key==='Enter' && !e.isComposing) this.send(); };
  },
  open(username){
    this.peer = username.toLowerCase(); this.last = 0;
    document.getElementById('dmWrap').classList.add('has-peer');
    this.drawMain(); this.poll(true);
    document.querySelectorAll('.dm-conv').forEach(c=>c.classList.toggle('on', c.dataset.peer===this.peer));
  },
  async poll(first){
    const peer = this.peer;
    const d = await api(`/dm/with/${encodeURIComponent(peer)}?after=${this.last}`);
    if(!d){ if(first){ this.peer = null; this.drawMain(); } return; }
    if(peer!==this.peer) return;
    const nm = document.getElementById('dmPeerName'); if(nm) nm.textContent = `${d.with.name} (@${d.with.username})`;
    const log = document.getElementById('dmLog'); if(!log) return;
    if(first && !d.messages.length) log.innerHTML = '<p class="m-muted m-center">เริ่มบทสนทนาได้เลย 👋</p>';
    if(!d.messages.length) return;
    if(this.last===0) log.innerHTML = '';
    log.insertAdjacentHTML('beforeend', d.messages.map(m=>`<div class="m-msg ${m.mine?'mine':''}"><small>${esc(m.time)}</small>`
      + (m.text ? `<div>${esc(m.text)}</div>` : '')
      + (m.images.length ? `<div class="dm-imgs">${m.images.map(u=>`<a href="${esc(u)}" target="_blank" rel="noopener"><img src="${esc(u)}" alt="" loading="lazy"></a>`).join('')}</div>` : '')
      + '</div>').join(''));
    this.last = d.messages[d.messages.length-1].id;
    log.scrollTop = log.scrollHeight;
    if(d.messages.some(m=>!m.mine)) this.loadInbox();
  },
  async send(){
    const input = document.getElementById('dmText'), text = input.value.trim(), images = pickedImages('dm');
    if(!text && !images.length) return;
    input.value = ''; PICKED.dm = []; redrawPicker('dm');
    if(await api(`/dm/with/${encodeURIComponent(this.peer)}`, {json:{text, images}})){ await this.poll(); this.loadInbox(); }
  },
});
