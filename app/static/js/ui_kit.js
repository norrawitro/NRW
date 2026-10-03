/* ui_kit.js — ชิ้นส่วนหน้าตาที่ทุกระบบใช้ร่วมกัน ("รูปแบบเดียวกัน": รูป + ข้อความ + ราคา + ปุ่ม)
   imagePicker('mk')        → HTML ช่องแนบรูป (สูงสุด 5 รูป, อัปโหลดไป POST /media/images ทันทีที่เลือก)
   pickedImages('mk')       → [url, ...] ส่งไปกับ body เป็น images
   gallery(images, '🛍️')    → รูปหลัก + รูปย่อ (ไม่มีรูป = ไอคอน)
   itemCard({images, icon, tag:{text,cls}, status, mod, title, text, price, unit, meta, actions})
                            → การ์ดมาตรฐาน (actions = HTML ปุ่ม, ผู้เรียกต้อง esc เอง) */
const UI_MAX_IMAGES = 5;
const PICKED = {};

function imagePicker(id, urls=[]){
  PICKED[id] = urls.slice(0, UI_MAX_IMAGES);
  return `<div class="ui-picker" id="pick-${id}"><div class="ui-thumbs">${pickerThumbs(id)}</div>
    <label class="btn-ghost m-sm ui-addimg">📷 แนบรูป (สูงสุด ${UI_MAX_IMAGES})<input type="file" accept="image/*" multiple hidden data-picker="${id}"></label></div>`;
}
function pickedImages(id){ return (PICKED[id]||[]).slice(); }
function pickerThumbs(id){
  return (PICKED[id]||[]).map((u,i)=>`<span class="ui-thumb"><img src="${esc(u)}" alt=""><button type="button" data-unpick="${id}" data-i="${i}" title="ลบรูป">×</button></span>`).join('');
}
function redrawPicker(id){ const b = document.querySelector(`#pick-${id} .ui-thumbs`); if(b) b.innerHTML = pickerThumbs(id); }

document.addEventListener('change', async e=>{
  const inp = e.target.closest && e.target.closest('input[data-picker]'); if(!inp) return;
  const id = inp.dataset.picker, files = [...inp.files]; inp.value = '';
  for(const f of files){
    if((PICKED[id]||[]).length >= UI_MAX_IMAGES){ toast(`แนบได้สูงสุด ${UI_MAX_IMAGES} รูป`); break; }
    if(f.size > 5*1024*1024){ toast('รูปใหญ่เกิน 5 MB'); continue; }
    const fd = new FormData(); fd.append('file', f);
    const r = await api('/media/images', {method:'POST', body:fd});
    if(r){ (PICKED[id] = PICKED[id]||[]).push(r.url); redrawPicker(id); }
  }
});
document.addEventListener('click', e=>{
  const un = e.target.closest && e.target.closest('[data-unpick]');
  if(un){ PICKED[un.dataset.unpick].splice(+un.dataset.i, 1); redrawPicker(un.dataset.unpick); return; }
  const g = e.target.closest && e.target.closest('[data-gimg]');
  if(g){ const main = g.closest('.ui-gallery').querySelector('.ui-main'); main.src = g.dataset.gimg; main.parentElement.href = g.dataset.gimg; }
});

function gallery(images, icon='🖼️'){
  if(!images || !images.length) return `<div class="m-noimg">${icon}</div>`;
  return `<div class="ui-gallery"><a href="${esc(images[0])}" target="_blank" rel="noopener"><img class="ui-main" src="${esc(images[0])}" alt="" loading="lazy"></a>
    ${images.length>1 ? `<div class="ui-strip">${images.map(u=>`<img src="${esc(u)}" data-gimg="${esc(u)}" alt="" loading="lazy">`).join('')}</div>` : ''}</div>`;
}

function itemCard(o){
  const price = o.price==null ? '<span></span>' : `<span class="m-price">${o.price>0 ? baht(o.price) : 'ฟรี'}${esc(o.unit||'')}</span>`;
  return `<div class="m-card m-product ui-item">${gallery(o.images, o.icon)}
    <div class="m-row">${o.tag ? `<span class="badge ${o.tag.cls||''}">${esc(o.tag.text)}</span>` : '<span></span>'}<small class="m-muted">${esc(o.status||'')}</small></div>
    ${modBadge(o.mod)}<b>${esc(o.title)}</b>${o.text ? `<p class="m-muted ui-text">${esc(o.text)}</p>` : ''}
    <div class="m-row">${price}<small class="m-muted">${esc(o.meta||'')}</small></div>${o.actions||''}</div>`;
}
