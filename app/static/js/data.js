/* data.js — ข้อมูลระบบ 21 ระบบ (PHASES, MODULES), หมวดโพสต์, State และ DataLayer (เรียก API กระเป๋าเงิน/คลาวด์) */
/* ============================================================
   ข้อมูลหมวดหมู่ (4 ช่วงพัฒนา ตามแผนลำดับพัฒนา 21 ระบบหลัก)
   ============================================================ */
const PHASES = {
  1:{label:'ช่วงที่ 1 · แกนกลางรากฐาน', color:'var(--phase1)', dot:'🔴'},
  2:{label:'ช่วงที่ 2 · พาณิชย์ & ธุรกิจ', color:'var(--phase2)', dot:'🟠'},
  3:{label:'ช่วงที่ 3 · การทำงาน & ความรู้', color:'var(--phase3)', dot:'🟡'},
  4:{label:'ช่วงที่ 4 · ชุมชน & เทคโนโลยีล้ำ', color:'var(--phase4)', dot:'🟢'},
};

/* รหัส/ลำดับ/เหตุผล/เชื่อมโยง อ้างอิงจากแผนลำดับพัฒนาที่วางไว้ */
const MODULES = [
  {code:1,  id:'news',   label:'ข่าวสาร/ประกาศ',        icon:'📰', phase:1, reason:'หน้าแรก + สื่อสารภายใน — ต้องมีก่อน', conn:['จัดการข้อมูล/คลาวด์'], view:'news'},
  {code:2,  id:'cloud',  label:'จัดการข้อมูล/คลาวด์',     icon:'☁️', phase:1, reason:'ที่เก็บไฟล์/เอกสาร — ทุกระบบใช้ร่วมกัน', conn:['ข่าวสาร/ประกาศ'], view:'cloud'},
  {code:7,  id:'wallet', label:'การเงิน/กระเป๋าเงินกลาง', icon:'💳', phase:1, reason:'ระบบชำระเงินกลาง — ทุกธุรกิจต้องอาศัย', conn:['ศูนย์ AI/บอทอัตโนมัติ'], view:'wallet'},
  {code:11, id:'ai',     label:'ศูนย์ AI/บอทอัตโนมัติ',   icon:'🤖', phase:1, reason:'ตัวช่วยกลาง — ประมวลผล, แจ้งเตือน, เชื่อมระบบ', conn:['การเงิน/กระเป๋าเงินกลาง'], view:'ai'},

  {code:3,  id:'shop',    label:'ขายออนไลน์',          icon:'🛒', phase:2, reason:'สร้างรายได้เร็วที่สุด อาศัยแกนกลางครบแล้ว', conn:['กระเป๋าเงินกลาง','จัดการข้อมูล/คลาวด์','ศูนย์ AI']},
  {code:17, id:'logistics',label:'คลังสินค้า/ขนส่ง',     icon:'🚚', phase:2, reason:'ต่อจากระบบขายโดยตรง', conn:['ขายออนไลน์','กระเป๋าเงินกลาง','ศูนย์ AI']},
  {code:12, id:'rental',  label:'มือสอง/เช่า',           icon:'♻️', phase:2, reason:'ใช้แพลตฟอร์มร่วมกับระบบขาย', conn:['ขายออนไลน์','กระเป๋าเงินกลาง','คลังสินค้า/ขนส่ง']},
  {code:21, id:'wanted',  label:'ประกาศซื้อ',            icon:'🔎', phase:2, reason:'ฝั่งผู้ซื้อของตลาด — บอกว่าต้องการอะไร ให้ผู้ขายมาเสนอ', conn:['มือสอง/เช่า','กระเป๋าเงินกลาง','แชทเรียลไทม์']},
  {code:19, id:'token',   label:'สินทรัพย์ดิจิทัล/โทเคน', icon:'🪙', phase:2, reason:'ต่อยอดจากกระเป๋าเงินกลาง', conn:['กระเป๋าเงินกลาง','ขายออนไลน์','ครีเอเตอร์/สมาชิก VIP']},
  {code:18, id:'analytics',label:'แดชบอร์ดวิเคราะห์',     icon:'📊', phase:2, reason:'ดึงข้อมูลจากทุกระบบธุรกิจมาแสดงผล', conn:['ทุกระบบธุรกิจ']},

  {code:6,  id:'chat',    label:'แชทเรียลไทม์',          icon:'💬', phase:3, reason:'ติดต่อกันได้ทุกที่ในแพลตฟอร์ม', conn:['ทุกระบบ']},
  {code:8,  id:'course',  label:'คอร์สเรียนออนไลน์',      icon:'🎓', phase:3, reason:'ใช้ระบบวิดีโอ + จ่ายเงิน + สมาชิก', conn:['วิดีโอ/สตรีมมิ่ง','กระเป๋าเงินกลาง']},
  {code:9,  id:'jobs',    label:'ตลาดงาน/ฟรีแลนซ์',      icon:'💼', phase:3, reason:'จ่ายค่าแรง + โฆษณางาน + คุยงาน', conn:['กระเป๋าเงินกลาง','โฆษณา','แชทเรียลไทม์']},
  {code:10, id:'workspace',label:'พื้นที่ทำงานร่วมกัน',    icon:'🧩', phase:3, reason:'ใช้ไฟล์ + แชท + AI ช่วยงานร่วมกัน', conn:['จัดการข้อมูล/คลาวด์','แชทเรียลไทม์','ศูนย์ AI']},
  {code:16, id:'ads',     label:'โฆษณา/สร้างรายได้',      icon:'📢', phase:3, reason:'วางโฆษณาและจ่ายค่าโฆษณาทั่วแพลตฟอร์ม', conn:['ทุกระบบ']},

  {code:5,  id:'video',   label:'วิดีโอความรู้/สตรีมมิ่ง',icon:'🎥', phase:4, reason:'ใช้ร่วมกับคอร์สเรียนและกิจกรรม', conn:['คอร์สเรียนออนไลน์','กิจกรรม/สัมมนา','โฆษณา']},
  {code:4,  id:'games',   label:'เกม/บันเทิง',           icon:'🎮', phase:4, reason:'ใช้โทเคนเป็นรางวัล เสริมสิทธิ VIP', conn:['สินทรัพย์ดิจิทัล/โทเคน','วิดีโอ/สตรีมมิ่ง']},
  {code:14, id:'events',  label:'กิจกรรม/สัมมนา/ตั๋ว',    icon:'🎫', phase:4, reason:'จ่ายค่าตั๋ว + ประกาศ + สตรีมสด', conn:['วิดีโอ/สตรีมมิ่ง','กระเป๋าเงินกลาง','ข่าวสาร/ประกาศ']},
  {code:15, id:'creator', label:'ครีเอเตอร์/สมาชิก VIP',  icon:'⭐', phase:4, reason:'รับรายได้จากการบอกรับ + โทเคน', conn:['กระเป๋าเงินกลาง','สินทรัพย์ดิจิทัล/โทเคน','โฆษณา']},
  {code:13, id:'iot',     label:'จัดการอุปกรณ์ IoT',      icon:'📡', phase:4, reason:'บันทึกข้อมูล + ควบคุมด้วย AI + คิดค่าบริการ', conn:['จัดการข้อมูล/คลาวด์','ศูนย์ AI','กระเป๋าเงินกลาง']},
  {code:20, id:'health',  label:'สุขภาพ/ออกกำลังกาย',     icon:'🏃', phase:4, reason:'AI แนะนำ + แลกคะแนนเป็นโทเคน', conn:['ศูนย์ AI','สินทรัพย์ดิจิทัล/โทเคน']},
];

const META_ITEMS = [
  {id:'profile', label:'ตั้งค่าสมาชิก', icon:'👤', href:'/members/profile'},
  {id:'help',    label:'คู่มือการใช้งาน', icon:'❓', view:'info'},
];

const POST_CATS = {
  announce:{label:'ประกาศ', color:'var(--primary)'},
  update:{label:'อัปเดตระบบ', color:'var(--cyan)'},
  event:{label:'กิจกรรม', color:'var(--gold)'},
};

/* ============================================================
   สถานะ (mock data ทั้งหมด — Data Layer แยกจาก UI)
   ============================================================ */
const State = {
  dark:false,
  sidebarOpen: window.innerWidth>880,
  view:'home',
  followed:{},
  posts:[
    {id:4, cat:'announce', author:'ทีมงาน WKW', when:'วันนี้', text:'เปิดตัวระบบสมาชิกแล้ว! แต่ละบัญชีจะมีพื้นที่ข้อมูลเป็นของตนเอง และเมื่อใช้งานระบบ POS ข้อมูลจะถูกจัดเก็บแยกตามบัญชีโดยอัตโนมัติ ปลอดภัย ไม่ปะปนกัน ✅', color:'var(--primary)'},
    {id:3, cat:'update', author:'ทีมพัฒนา', when:'เมื่อวาน', text:'อัปเดตระบบคลาวด์: เพิ่มพื้นที่จัดเก็บและปรับปรุงความเร็วในการอัปโหลดไฟล์ให้เร็วขึ้น 2 เท่า', color:'var(--cyan)'},
    {id:2, cat:'announce', author:'ทีมงาน WKW', when:'2 วันก่อน', text:'ระบบแกนกลาง 4 ระบบ (ข่าวสาร, คลาวด์, กระเป๋าเงิน, AI) เปิดใช้งานครบแล้วตามแผนช่วงที่ 1 🎉 ระบบถัดไปคือฝั่งพาณิชย์ในช่วงที่ 2', color:'var(--primary)'},
    {id:1, cat:'event', author:'ทีมงาน WKW', when:'3 วันก่อน', text:'เตรียมพบกับระบบขายออนไลน์และคลังสินค้า/ขนส่งเร็ว ๆ นี้ — เชื่อมกับกระเป๋าเงินกลางโดยตรง', color:'var(--gold)'},
  ],
  newsFilter:'all',
  postsCache:{},  // id -> post (สำหรับ share button)
  wallet:{
    balance:0, token:0, tx:[],
  },
  storage:{used:0, total:50},
  cloudPath:[{id:null, name:'หน้าแรก'}],  // id=null = root
  cloudItems:[],  // items ของโฟลเดอร์ปัจจুবัน (โหลดจาก API)
  aiMessages:[
    {who:'ai', text:'สวัสดีครับ ผมคือ AI ผู้ช่วยของ WKW 🤖 ผมเชื่อมข้อมูลจากระบบกระเป๋าเงิน คลาวด์ และข่าวสารไว้แล้ว ถามอะไรก็ได้เลยครับ'},
  ],
};

/* ============================================================
   Data Layer — ทุกการเข้าถึงข้อมูลผ่านฟังก์ชันนี้เท่านั้น
   (ภายหลังสลับไปเรียก API จริงได้โดยไม่แตะ UI)
   ============================================================ */
const DataLayer = {
  getHeroSlides: () => ([
    {tag:'promo', label:'✨ ยินดีต้อนรับ', title:'WKW (Workkaweb) — แพลตฟอร์มรวมทุกอย่างในที่เดียว', sub:'ระบบแกนกลางครบ 4 ระบบ · Module Registry พร้อมขยาย 21 ระบบ', bg:'linear-gradient(135deg,#4F46E5,#8B5CF6)'},
    {tag:'news', label:'📢 ประกาศ', title:'ช่วงที่ 1 เสร็จสมบูรณ์! ข่าวสาร · คลาวด์ · กระเป๋าเงิน · AI ใช้งานได้แล้ว', sub:'ระบบถัดไปตามแผน: ขายออนไลน์ และ คลังสินค้า/ขนส่ง (ช่วงที่ 2)', bg:'linear-gradient(135deg,#059669,#10B981)'},
  ]),
  getModules: () => MODULES,
  getPosts: (filter) => State.posts.filter(p => filter==='all'||!filter ? true : p.cat===filter),
  addPost: (text, cat) => { State.posts.unshift({id:Date.now(), cat, author:'ก (คุณ)', when:'เมื่อสักครู่', text, color:'var(--violet)'}); },
  getWallet: () => State.wallet,
  addTransaction: async (desc, amount, type) => {
    const r = await fetch('/wallet/tx', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({type, amount, desc})
    });
    if(r.status===401){ alert('กรุณาเข้าสู่ระบบก่อน'); window.location='/members/login'; return null; }
    if(!r.ok){ const er=await r.json(); alert(er.detail||'เกิดข้อผิดพลาด'); return null; }
    return await fetchWallet();
  },
  getCloudPath: () => State.cloudPath,
  getCloudItems: (folderId) => State.cloudItems,
  addCloudFolder: async (name, parent) => {
    const r = await fetch('/cloud/folders', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({name, parent_id: parent===null?null:parent})
    });
    if(r.status===401){ alert('กรุณาเข้าสู่ระบบก่อน'); window.location='/members/login'; return null; }
    if(!r.ok){ const er=await r.json(); alert(er.detail||'เกิดข้อผิดพลาด'); return null; }
    return await fetchCloud();
  },
  deleteCloudItem: async (id, type) => {
    const r = await fetch(`/cloud/items/${id}?type=${encodeURIComponent(type||'')}`, {method:'DELETE'});
    if(r.status===401){ alert('กรุณาเข้าสู่ระบบก่อน'); window.location='/members/login'; return null; }
    if(!r.ok){ const er=await r.json(); alert(er.detail||'เกิดข้อผิดพลาด'); return null; }
    return await fetchCloud();
  },
  getAIMessages: () => State.aiMessages,
};
