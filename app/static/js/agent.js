/* agent.js — 🛠️ AI Agent ในหน้าศูนย์ AI (เฉพาะเจ้าของ: ผู้ดูแล + รหัสผ่าน Agent) — ลูกค้าไม่เห็นส่วนนี้เลย
   ส่งข้อความ/คำสั่งเข้า Hermes ใน tmux บน WSL · สถานะ CPU/GPU/Ollama ค้างไว้บนจอ อัปเดตทุก 2.5 วินาที
   API: GET /agent/state · POST /agent/unlock|lock|send|model|stop|reset · GET /agent/status */
const AgentUI = {
  timer: null, busy: false,
  async call(url, body){
    const o = {credentials:'same-origin', headers:{'X-WKW-Agent':'1'}};
    if(body!==undefined){ o.method = 'POST'; o.headers['Content-Type'] = 'application/json'; o.body = JSON.stringify(body); }
    let r; try{ r = await fetch(url, o); }catch(e){ return {ok:false, status:0, data:{detail:'เชื่อมต่อเซิร์ฟเวอร์ไม่ได้'}}; }
    let data = {}; try{ data = await r.json(); }catch(e){}
    return {ok:r.ok, status:r.status, data};
  },
  box(){
    let el = document.getElementById('agentBox');
    if(!el){ el = document.createElement('div'); el.id = 'agentBox'; document.getElementById('view-ai').appendChild(el); }
    return el;
  },
  async mount(){
    this.stopPoll();
    const old = document.getElementById('agentBox');
    if(!(State.me && State.me.is_admin)){ if(old) old.remove(); return; }
    const r = await this.call('/agent/state');
    if(!r.ok){ if(old) old.remove(); return; }           // ไม่ใช่เจ้าของ → ไม่แสดงอะไรเลย
    this.state = r.data;
    if(!r.data.enabled) return this.drawDisabled();
    return r.data.unlocked ? this.drawPanel() : this.drawLock();
  },
  drawDisabled(){
    this.box().innerHTML = `<div class="m-card ag-card"><h3>🛠️ AI Agent <small class="m-muted">(เฉพาะเจ้าของ)</small></h3>
      <p class="m-muted">ยังไม่ได้ตั้งรหัสผ่าน — รันใน WSL: <code>python set_agent_password.py</code> แล้ว <code>bash restart.sh</code></p></div>`;
  },
  drawLock(msg){
    this.stopPoll();
    this.box().innerHTML = `<div class="m-card ag-card ag-lock"><h3>🔒 AI Agent <small class="m-muted">(เฉพาะเจ้าของ)</small></h3>
      <p class="m-muted">ใส่รหัสผ่าน Agent เพื่อควบคุม Hermes บนเครื่อง</p>
      <div class="m-row"><input id="agPass" class="m-input" type="password" autocomplete="current-password" placeholder="รหัสผ่าน Agent"><button class="btn-primary" id="agUnlock">ปลดล็อก</button></div>
      ${msg?`<p class="ag-err">${esc(msg)}</p>`:''}</div>`;
    const go = async ()=>{
      const r = await this.call('/agent/unlock', {password:document.getElementById('agPass').value});
      if(r.ok) this.mount(); else this.drawLock(r.data.detail || 'ปลดล็อกไม่สำเร็จ');
    };
    document.getElementById('agUnlock').onclick = go;
    document.getElementById('agPass').onkeydown = e=>{ if(e.key==='Enter') go(); };
    document.getElementById('agPass').focus();
  },
  drawPanel(){
    const s = this.state;
    this.box().innerHTML = `<div class="m-card ag-card">
      <div class="m-row"><h3>🛠️ AI Agent <small class="m-muted">→ tmux <code>${esc(s.target)}</code></small></h3>
        <span><small class="m-muted" id="agLeft"></small> <button class="btn-ghost m-sm" id="agLock">🔒 ล็อก</button></span></div>
      <div class="ag-status" id="agStatus"><span class="m-muted">กำลังอ่านสถานะ…</span></div>
      <div class="ag-models"><small class="m-muted">โมเดล:</small> ${s.models.map(m=>`<button class="btn-ghost m-sm" data-agmodel="${m.id}" title="ส่ง: ${esc(m.command)}">${esc(m.label)}</button>`).join(' ')}</div>
      <pre class="ag-screen" id="agScreen">…</pre>
      <textarea id="agText" class="m-input ag-text" rows="2" maxlength="4000" placeholder="พิมพ์ข้อความถึง Agent… (Enter = ส่ง, Shift+Enter = ขึ้นบรรทัด)"></textarea>
      <div class="ag-cmds"><button class="btn-ghost" id="agQueue" title="ใส่ /queue ลงช่องพิมพ์ (ยังไม่ส่ง)">📥 Queue</button>
        <button class="btn-ghost ag-stop" id="agStop" title="${esc(s.stop==='C-c'?'กด Ctrl+C':'ส่ง '+s.stop)}">⏹ Stop</button>
        <button class="btn-ghost" id="agReset" title="ส่ง ${esc(s.reset)}">🔄 Reset</button>
        <button class="btn-primary" id="agSend">ส่ง ➤</button></div>
      <details class="ag-hist"><summary>ประวัติคำสั่ง</summary><div id="agHist"></div></details></div>`;
    const t = document.getElementById('agText');
    t.onkeydown = e=>{ if(e.key==='Enter' && !e.shiftKey && !e.isComposing){ e.preventDefault(); this.send(); } };
    this.box().onclick = e=>this.click(e);
    this.poll(); this.timer = setInterval(()=>this.poll(), 2500);
  },
  async click(e){
    const m = e.target.closest('[data-agmodel]');
    if(m) return this.act('/agent/model', {id:+m.dataset.agmodel}, `เปลี่ยนโมเดล: ${m.textContent}`);
    if(e.target.id==='agQueue'){ const t = document.getElementById('agText'); if(!t.value.startsWith('/queue ')) t.value = '/queue ' + t.value; t.focus(); t.setSelectionRange(t.value.length, t.value.length); }
    if(e.target.id==='agStop') return this.act('/agent/stop', {}, 'ส่ง Stop แล้ว');
    if(e.target.id==='agReset' && confirm('Reset บทสนทนาของ Agent?')) return this.act('/agent/reset', {}, 'ส่ง Reset แล้ว');
    if(e.target.id==='agSend') return this.send();
    if(e.target.id==='agLock'){ await this.call('/agent/lock', {}); this.drawLock(); }
  },
  async send(){
    const t = document.getElementById('agText'), text = t.value.trim();
    if(!text || this.busy) return;
    if(await this.act('/agent/send', {text}, 'ส่งแล้ว')) t.value = '';
  },
  async act(url, body, msg){
    this.busy = true;
    const r = await this.call(url, body);
    this.busy = false;
    if(r.status===401){ this.drawLock('หมดเวลา — ใส่รหัสผ่านอีกครั้ง'); return false; }
    if(!r.ok){ toast(r.data.detail || 'ส่งไม่สำเร็จ'); return false; }
    toast(msg); setTimeout(()=>this.poll(), 400); return true;
  },
  bar(label, pct, extra=''){
    const v = pct==null ? null : Math.max(0, Math.min(100, pct));
    return `<div class="ag-meter"><span>${label}</span><div class="ag-track"><i style="width:${v||0}%;background:${v>85?'#e5484d':v>60?'#f59e0b':'#22c55e'}"></i></div><b>${v==null?'—':v.toFixed(0)+'%'}</b>${extra}</div>`;
  },
  async poll(){
    if(State.view!=='ai' || !document.getElementById('agStatus')){ this.stopPoll(); return; }
    if(document.hidden) return;
    const r = await this.call('/agent/status');
    if(r.status===401) return this.drawLock('หมดเวลา — ใส่รหัสผ่านอีกครั้ง');
    if(!r.ok) return;
    const d = r.data, g = d.gpus[0];
    const models = d.ollama.models.length ? d.ollama.models.map(m=>`<div class="ag-model"><b>${esc(m.name)}</b> <small class="m-muted">${esc(m.size||'')}</small>
        <div class="ag-split"><i class="cpu" style="width:${m.cpu_pct||0}%"></i><i class="gpu" style="width:${m.gpu_pct||0}%"></i></div>
        <small>CPU ${m.cpu_pct??'—'}% · GPU ${m.gpu_pct??'—'}%</small></div>`).join('')
      : `<small class="m-muted">${d.ollama.online?'ยังไม่มีโมเดลโหลดอยู่':'⚠️ เชื่อมต่อ Ollama ไม่ได้'}</small>`;
    document.getElementById('agStatus').innerHTML = `<div class="ag-meters">${this.bar('CPU', d.cpu)}${this.bar('RAM', d.mem)}
        ${this.bar('GPU', d.gpu, g?`<small class="m-muted">VRAM ${(g.mem_used_mb/1024).toFixed(1)}/${(g.mem_total_mb/1024).toFixed(1)} GB${g.temp?` · ${g.temp}°C`:''}</small>`:'<small class="m-muted">ไม่พบ GPU</small>')}</div>
      <div class="ag-ollama"><small class="m-muted">Ollama (ollama ps):</small>${models}</div>
      <div class="ag-tmux">${d.tmux.alive?`🟢 tmux <code>${esc(d.tmux.target)}</code> ทำงานอยู่`:`🔴 ไม่พบ tmux session <code>${esc(d.tmux.target)}</code>`} <small class="m-muted">· อัปเดต ${esc(d.time)}</small></div>`;
    const scr = document.getElementById('agScreen'), atBottom = scr.scrollTop + scr.clientHeight >= scr.scrollHeight - 30;
    scr.textContent = d.screen || (d.tmux.alive ? '' : `ยังไม่มี tmux session ชื่อ ${d.tmux.target}\nเริ่มด้วย: tmux new -s ${d.tmux.target}  แล้วรัน hermes ในนั้น`);
    if(atBottom) scr.scrollTop = scr.scrollHeight;
    const left = document.getElementById('agLeft'); if(left) left.textContent = `ล็อกอัตโนมัติใน ${Math.ceil(d.expires_in/60)} นาที`;
    document.getElementById('agHist').innerHTML = d.history.map(h=>`<div class="m-row"><small>${esc(h.time)} · ${esc(h.action)}</small><small class="m-muted">${esc(h.detail)}</small></div>`).join('') || '<small class="m-muted">ยังไม่มี</small>';
  },
  stopPoll(){ clearInterval(this.timer); this.timer = null; },
};
