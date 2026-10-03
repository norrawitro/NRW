/* news.js — ข่าวสาร: postCard(), fetchPosts(), feed, ถูกใจ, ความเห็น, โพสต์ใหม่ */
/* ============================================================
   RENDER: NEWS
   ============================================================ */
function esc(s){return String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
function postCard(p){
  const cat = POST_CATS[p.cat] || {label:p.cat, color:'var(--ink-soft)'};
  return `<div class="post" data-post-id="${p.id}">
    <div class="post-head">
      <div class="post-av" style="background:${cat.color}">${esc(p.author[0])}</div>
      <div><div style="font-weight:600;font-size:13.5px;">${esc(p.author)}</div><div style="font-size:12px;color:var(--ink-soft)">${esc(p.when)}</div></div>
      <span class="post-tag" style="background:${cat.color}1a;color:${cat.color}">${cat.label}</span>
      ${p.is_mine ? `<button class="post-del-btn" data-del-post="${p.id}" title="ลบโพสต์ของฉัน" style="margin-left:4px;background:none;border:none;cursor:pointer;font-size:13px;color:var(--danger)">🗑️</button>` : ''}
    </div>
    <div class="post-body">${esc(p.text)}</div>
    <div class="post-actions">
      <button class="like-btn ${p.liked?'liked':''}" data-like="${p.id}" title="กดถูกใจ">
        👍 ${p.liked?'ถูกใจแล้ว':'ถูกใจ'} <span class="like-count">${p.likes>0?'('+p.likes+')':''}</span>
      </button>
      <button class="comment-toggle-btn" data-comment-toggle="${p.id}" title="แสดงความเห็น">
        💬 ความเห็น <span>${p.comments>0?'('+p.comments+')':''}</span>
      </button>
      <button class="share-btn" data-share="${p.id}" title="แชร์โพสต์">↗️ แชร์</button>
    </div>
    <div class="comment-section" id="comments-${p.id}">
      <div class="comment-list" id="comment-list-${p.id}"></div>
      <div class="comment-input-row">
        <input type="text" placeholder="เขียนความเห็น…" id="comment-input-${p.id}">
        <button onclick="submitComment(${p.id})">ส่ง</button>
      </div>
    </div>
  </div>`;
}

// ── API: โหลดโพสต์จาก server ──────────────────────────────
async function fetchPosts(cat='all'){
  try{
    const r = await fetch(`/news/posts?cat=${cat}&limit=50`);
    const d = await r.json();
    const posts = d.posts || [];
    posts.forEach(p=>{ State.postsCache[p.id] = p; });
    return posts;
  } catch(e){ return []; }
}

async function renderNewsFeed(){
  const list = await fetchPosts(State.newsFilter);
  document.getElementById('newsFeed').innerHTML = list.length ? list.map(postCard).join('') :
    `<p style="color:var(--ink-soft);font-size:14px;text-align:center;padding:30px;">ยังไม่มีประกาศในหมวดนี้</p>`;
}

async function renderHomeFeed(){
  const list = await fetchPosts('all');
  document.getElementById('homePostFeed').innerHTML = list.slice(0,3).map(postCard).join('');
}
function renderNewsComposerCats(){
  document.getElementById('newPostCatRow').innerHTML = Object.entries(POST_CATS).map(([k,c],i)=>
    `<span class="cat-chip ${i===0?'on':''}" data-cat="${k}" title="หมวด: ${c.label}">${c.label}</span>`).join('');
}
function renderNewsFilters(){
  document.getElementById('newsFilterRow').innerHTML = `<span class="cat-chip ${State.newsFilter==='all'?'on':''}" data-filter="all" title="แสดงทุกหมวด">ทั้งหมด</span>` +
    Object.entries(POST_CATS).map(([k,c])=>`<span class="cat-chip ${State.newsFilter===k?'on':''}" data-filter="${k}" title="กรอง: ${c.label}">${c.label}</span>`).join('');
}

/* ============================================================
   NEWS FUNCTIONS
   ============================================================ */
async function toggleLike(postId, btn){
  const r = await fetch(`/news/posts/${postId}/like`, {method:'POST'});
  if(r.status===401){ alert('กรุณาเข้าสู่ระบบก่อน'); window.location='/members/login'; return; }
  const d = await r.json();
  btn.classList.toggle('liked', d.liked);
  btn.innerHTML = `👍 ${d.liked?'ถูกใจแล้ว':'ถูกใจ'} <span class="like-count">${d.likes>0?'('+d.likes+')':''}</span>`;
}

async function loadComments(postId){
  const r = await fetch(`/news/posts/${postId}/comments`);
  const d = await r.json();
  const el = document.getElementById(`comment-list-${postId}`);
  el.innerHTML = d.comments.length ? d.comments.map(c=>`
    <div class="comment-item">
      <div class="comment-av">${esc(c.author[0])}</div>
      <div class="comment-body">
        <div class="comment-author">${esc(c.author)} · ${esc(c.when)}</div>
        ${esc(c.text)}
      </div>
    </div>`).join('') : '<p style="font-size:12px;color:var(--ink-soft);padding:4px 0;">ยังไม่มีความเห็น</p>';
}

async function submitComment(postId){
  const input = document.getElementById(`comment-input-${postId}`);
  const text = input.value.trim();
  if(!text) return;
  const r = await fetch(`/news/posts/${postId}/comments`, {
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({text})
  });
  if(r.status===401){ alert('กรุณาเข้าสู่ระบบก่อน'); window.location='/members/login'; return; }
  input.value = '';
  await loadComments(postId);
}

async function submitPostFn(){
  const text = document.getElementById('newPostText').value.trim();
  if(!text) return;
  const cat = document.querySelector('#newPostCatRow .cat-chip.on')?.dataset.cat || 'announce';
  const btn = document.getElementById('submitPost');
  btn.disabled = true; btn.textContent = 'กำลังโพสต์…';
  try{
    const r = await fetch('/news/posts', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({text, cat})
    });
    if(r.status===401){ alert('กรุณาเข้าสู่ระบบก่อนโพสต์'); window.location='/members/login'; return; }
    if(!r.ok){ const er=await r.json(); alert(er.detail||'เกิดข้อผิดพลาด'); return; }
    document.getElementById('newPostText').value = '';
    await renderNewsFeed();
  } finally{ btn.disabled=false; btn.textContent='โพสต์'; }
}
