/* tts.js — อ่านออกเสียงด้วยเครื่องของผู้ใช้เอง (Web Speech API ในเบราว์เซอร์) — เซิร์ฟเวอร์ไม่ต้องแปลงเสียง
   Speech.toggle(id, text)  เล่น/หยุด ข้อความ (ปุ่ม 🔊 ท้ายข้อความ AI)
   Speech.auto              อ่านอัตโนมัติเมื่อ AI ตอบเสร็จ (จำไว้ในเบราว์เซอร์)
   Speech.unlock()          เรียกตอนผู้ใช้กดส่ง — iPhone/บางเบราว์เซอร์ยอมให้พูดได้ต่อเมื่อเริ่มจากการกดของผู้ใช้ */
const Speech = {
  supported: 'speechSynthesis' in window && 'SpeechSynthesisUtterance' in window,
  playing: null, auto: false, warned: false,
  init(){
    try{ this.auto = localStorage.getItem('wkw_tts_auto')==='1'; }catch(e){}
    if(this.supported) speechSynthesis.onvoiceschanged = ()=>{ this._voice = undefined; };
  },
  voice(){
    if(this._voice !== undefined) return this._voice;
    const vs = this.supported ? speechSynthesis.getVoices() : [];
    this._voice = vs.find(v=>/^th(-|_|$)/i.test(v.lang) && v.localService) || vs.find(v=>/^th(-|_|$)/i.test(v.lang)) || null;
    return this._voice;
  },
  /** ตัดข้อความเป็นช่วงสั้น ๆ (Chrome หยุดพูดเองถ้าประโยคยาวเกิน ~15 วินาที) + ล้างสัญลักษณ์ที่ไม่ควรอ่าน */
  chunks(text){
    const clean = text.replace(/[\u{1F300}-\u{1FAFF}\u{2600}-\u{27BF}\u{FE0F}]/gu, ' ').replace(/[*#_`>|~]/g, ' ')
      .replace(/https?:\/\/\S+/g, ' ลิงก์ ').replace(/\s*จบ\s*$/, '').replace(/[ \t]+/g, ' ').trim();
    const out = [];
    clean.split(/(?<=[.!?。\n])\s+|\n+/).forEach(part=>{
      for(let s = part.trim(); s; ){
        if(s.length <= 180){ out.push(s); break; }
        let cut = s.lastIndexOf(' ', 180); if(cut < 60) cut = 180;
        out.push(s.slice(0, cut)); s = s.slice(cut).trim();
      }
    });
    return out.filter(Boolean);
  },
  unlock(){
    if(!this.supported || this.unlocked) return;
    const u = new SpeechSynthesisUtterance(' '); u.volume = 0; speechSynthesis.speak(u); this.unlocked = true;
  },
  speak(id, text){
    if(!this.supported){ toast('เบราว์เซอร์นี้อ่านออกเสียงไม่ได้ — ลอง Chrome หรือ Safari'); return; }
    this.stop();
    const v = this.voice(), parts = this.chunks(text);
    if(!parts.length) return;
    if(!v && /[฀-๿]/.test(text) && !this.warned){
      this.warned = true;
      toast('เครื่องนี้ยังไม่มีเสียงภาษาไทย — เปิดได้ที่ ตั้งค่าเครื่อง → การเข้าถึง → อ่านออกเสียง (Text-to-speech) → ภาษาไทย');
    }
    this.playing = id; this.mark();
    parts.forEach((p, i)=>{
      const u = new SpeechSynthesisUtterance(p);
      if(v) u.voice = v;
      u.lang = v ? v.lang : 'th-TH'; u.rate = 1; u.pitch = 1;
      if(i === parts.length - 1){ u.onend = u.onerror = ()=>{ if(this.playing===id){ this.playing = null; this.mark(); } }; }
      speechSynthesis.speak(u);
    });
  },
  stop(){
    if(this.supported) speechSynthesis.cancel();
    this.playing = null; this.mark();
  },
  toggle(id, text){ this.playing===id ? this.stop() : this.speak(id, text); },
  setAuto(on){
    this.auto = on;
    try{ localStorage.setItem('wkw_tts_auto', on ? '1' : '0'); }catch(e){}
    if(on){ this.unlock(); toast('🔊 เปิดอ่านอัตโนมัติ — คำตอบใหม่จะอ่านให้ฟังทันที'); } else this.stop();
  },
  /** อัปเดตไอคอนปุ่ม 🔊/⏹ ของทุกข้อความ */
  mark(){
    document.querySelectorAll('[data-speak]').forEach(b=>{
      const on = b.dataset.speak === String(this.playing);
      b.textContent = on ? '⏹' : '🔊'; b.title = on ? 'หยุดอ่าน' : 'ฟังข้อความนี้'; b.classList.toggle('on', on);
    });
  },
};
Speech.init();
