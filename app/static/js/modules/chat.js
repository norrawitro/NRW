/* modules/chat.js — แชท: ห้องรวม + คุยส่วนตัว (ดึงข้อความใหม่ทุก 3 วินาทีขณะเปิดหน้านี้)
   API: GET /chat/rooms · GET /chat/messages?room=&after= · POST /chat/messages */
registerModule('chat', {
  sub: 'คุยกับสมาชิกทุกคนในห้องรวม หรือคุยส่วนตัวด้วย username',
  async render(el){
    if(!State.me){ loginGate(el, 'แชท'); return; }
    this.room = this.room || 'general'; this.last = 0;
    el.innerHTML = `<div class="m-split m-chat"><div class="m-card"><div class="m-chat-log" id="chLog"></div>
        <div class="m-row"><input id="chText" class="m-input" maxlength="2000" placeholder="พิมพ์ข้อความ… (Enter เพื่อส่ง)"><button class="btn-primary" id="chSend">ส่ง</button></div></div>
      <div class="m-card"><h3>ห้องแชท</h3><div id="chRooms"></div>
        <div class="m-row"><input id="chDm" class="m-input" placeholder="username เพื่อคุยส่วนตัว"><button class="btn-ghost m-sm" id="chDmBtn">เปิด</button></div></div></div>`;
    el.onclick = e=>{
      const r = e.target.closest('[data-room]');
      if(r) this.open(r.dataset.room);
      if(e.target.id==='chSend') this.send();
      if(e.target.id==='chDmBtn'){ const u = document.getElementById('chDm').value.trim().toLowerCase(); if(u) this.open('dm:'+u); }
    };
    document.getElementById('chText').onkeydown = e=>{ if(e.key==='Enter') this.send(); };
    await this.loadRooms();
    this.open(this.room);
    clearInterval(this.timer);
    this.timer = setInterval(()=>{ if(State.view!=='chat'){ clearInterval(this.timer); return; } this.poll(); }, 3000);
  },
  async loadRooms(){
    const d = await api('/chat/rooms'); if(!d) return;
    if(this.room.startsWith('dm:') && !d.rooms.some(r=>r.room===this.room)) d.rooms.push({room:this.room, label:'👤 '+this.room.slice(3)});
    document.getElementById('chRooms').innerHTML = d.rooms.map(r=>`<div class="m-row"><a href="#" class="m-link" data-room="${esc(r.room)}">${r.room===this.room?'▶ ':''}${esc(r.label)}</a></div>`).join('');
  },
  open(room){ this.room = room; this.last = 0; document.getElementById('chLog').innerHTML = ''; this.loadRooms(); this.poll(); },
  async poll(){
    const room = this.room;
    const d = await api(`/chat/messages?room=${encodeURIComponent(room)}&after=${this.last}`);
    if(!d || room!==this.room || !d.messages.length) return;
    const log = document.getElementById('chLog');
    if(!log) return;
    log.insertAdjacentHTML('beforeend', d.messages.map(m=>`<div class="m-msg ${m.mine?'mine':''}"><small>${esc(m.sender)} · ${esc(m.time)}</small><div>${esc(m.text)}</div></div>`).join(''));
    this.last = d.messages[d.messages.length-1].id;
    log.scrollTop = log.scrollHeight;
  },
  async send(){
    const input = document.getElementById('chText'), text = input.value.trim();
    if(!text) return;
    input.value = '';
    if(await api('/chat/messages', {json:{room:this.room, text}})) this.poll();
  },
});
