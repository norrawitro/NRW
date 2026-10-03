/* modules/games.js — เกม/บันเทิง: เกมจับคู่ภาพ + เกมคิดเลขเร็ว, ตารางอันดับ, ได้โทเคน (สูงสุด 5 รอบ/วัน)
   API: POST /games/score · GET /games/leaderboard?game= */
const EMOJIS = ['🍎','🚗','🐱','🌙','⚽','🎸','🌵','🍩'];
registerModule('games', {
  sub: 'เล่นเกมสั้น ๆ สะสมคะแนนขึ้นตารางอันดับ และรับโทเคนเป็นรางวัล',
  async render(el){
    el.innerHTML = `<div class="m-tabs"><button class="m-tab on" data-game="memory">🧠 จับคู่ภาพ</button><button class="m-tab" data-game="quickmath">➗ คิดเลขเร็ว</button></div>
      <div class="m-split"><div class="m-card" id="gmBoard"></div><div class="m-card"><h3>🏆 อันดับ</h3><div id="gmTop"></div></div></div>`;
    el.onclick = e=>{ const g = e.target.closest('[data-game]'); if(g){ el.querySelectorAll('.m-tab').forEach(t=>t.classList.toggle('on', t===g)); this.start(g.dataset.game); } };
    this.start('memory');
  },
  async top(game){
    const d = await api('/games/leaderboard?game='+game);
    document.getElementById('gmTop').innerHTML = d && d.top.length ? d.top.map((t,i)=>`<div class="m-row"><span>${['🥇','🥈','🥉'][i]||i+1+'.'} ${esc(t.name)}</span><b>${t.score}</b></div>`).join('') : '<p class="m-muted">ยังไม่มีคะแนน</p>';
  },
  async finish(game, score){
    if(!State.me){ toast(`ได้ ${score} คะแนน — เข้าสู่ระบบเพื่อบันทึกคะแนน`); return; }
    const r = await api('/games/score', {json:{game, score}});
    if(r) toast(`ได้ ${score} คะแนน` + (r.reward?` · +${r.reward} โทเคน (เหลือวันนี้ ${r.left_today})`:' · วันนี้รับโทเคนครบแล้ว'));
    this.top(game);
  },
  start(game){
    clearInterval(this.timer); this.top(game);
    game==='memory' ? this.memory() : this.quickmath();
  },
  memory(){
    const cards = [...EMOJIS, ...EMOJIS].sort(()=>Math.random()-.5);
    let open = [], matched = 0, moves = 0;
    const box = document.getElementById('gmBoard');
    box.innerHTML = `<h3>จับคู่ให้ครบด้วยจำนวนครั้งน้อยที่สุด</h3><div class="m-memory">${cards.map((c,i)=>`<button class="m-mcard" data-i="${i}">?</button>`).join('')}</div><p class="m-muted" id="gmInfo">เปิดแล้ว 0 ครั้ง</p>`;
    box.querySelectorAll('.m-mcard').forEach(b=>b.onclick = ()=>{
      if(open.length===2 || b.classList.contains('up')) return;
      b.textContent = cards[b.dataset.i]; b.classList.add('up'); open.push(b);
      if(open.length<2) return;
      moves++; document.getElementById('gmInfo').textContent = `เปิดแล้ว ${moves} ครั้ง`;
      const [a, c] = open;
      if(cards[a.dataset.i]===cards[c.dataset.i]){ open = []; if(++matched===EMOJIS.length) this.finish('memory', Math.max(10, 1000 - (moves-8)*40)); }
      else setTimeout(()=>{ a.textContent = c.textContent = '?'; a.classList.remove('up'); c.classList.remove('up'); open = []; }, 700);
    });
  },
  quickmath(){
    let score = 0, left = 30, q;
    const box = document.getElementById('gmBoard');
    const next = ()=>{ const a = 2+Math.floor(Math.random()*20), b = 2+Math.floor(Math.random()*20), op = Math.random()<.5?'+':'×';
      q = {text:`${a} ${op} ${b}`, ans: op==='+'?a+b:a*b}; document.getElementById('gmQ').textContent = q.text + ' = ?'; };
    box.innerHTML = `<h3>ตอบให้ถูกมากที่สุดใน 30 วินาที</h3><div class="m-quiz" id="gmQ"></div><input id="gmA" class="m-input" type="number" placeholder="คำตอบ แล้วกด Enter">
      <p class="m-muted">เวลา <b id="gmT">30</b> วิ · คะแนน <b id="gmS">0</b></p>`;
    next(); document.getElementById('gmA').focus();
    document.getElementById('gmA').onkeydown = e=>{
      if(e.key!=='Enter' || left<=0) return;
      if(+e.target.value===q.ans){ score += 10; document.getElementById('gmS').textContent = score; }
      e.target.value = ''; next();
    };
    this.timer = setInterval(()=>{
      if(State.view!=='games'){ clearInterval(this.timer); return; }
      document.getElementById('gmT').textContent = --left;
      if(left<=0){ clearInterval(this.timer); this.finish('quickmath', Math.min(score, 1000)); }
    }, 1000);
  },
});
