/* modules/analytics.js — แดชบอร์ดวิเคราะห์: สรุปของฉัน + ภาพรวมระบบ (ผู้ดูแล)
   API: GET /analytics/me · GET /analytics/admin */
function bars(rows, key, label){
  const max = Math.max(1, ...rows.map(r=>r[key]));
  return `<div class="m-bars">${rows.map(r=>`<div class="m-bar" title="${esc(r[label])}: ${r[key].toLocaleString()}">
    <div style="height:${Math.round(r[key]/max*100)}%"></div><small>${esc(r[label])}</small></div>`).join('')}</div>`;
}
function stat(label, value){ return `<div class="m-stat"><div class="m-stat-v">${value}</div><div class="m-muted">${label}</div></div>`; }

registerModule('analytics', {
  sub: 'ตัวเลขจริงจากทุกระบบ — ของฉัน และภาพรวมทั้งแพลตฟอร์ม (ผู้ดูแล)',
  async render(el){
    if(!State.me){ loginGate(el, 'แดชบอร์ด'); return; }
    const me = await api('/analytics/me');
    if(!me) return;
    el.innerHTML = `<div class="m-card"><h3>👤 ของฉัน</h3><div class="m-stats">
        ${stat('ยอดเงิน', baht(me.balance))}${stat('โทเคน', me.token.toLocaleString())}${stat('ออเดอร์', me.orders)}
        ${stat('ใช้จ่ายรวม', baht(me.spent))}${stat('ซื้อ/เช่ามือสอง', me.market_bought)}${stat('ประกาศของฉัน', me.market_listings)}
        ${stat('ไฟล์', me.files)}${stat('โพสต์', me.posts)}</div>
        <h4 class="m-muted">ใช้จ่าย 14 วันล่าสุด (บาท)</h4>${bars(me.daily_spent, 'total', 'day')}</div><div id="anAdmin"></div>`;
    if(!State.me.is_admin) return;
    const a = await api('/analytics/admin');
    if(!a) return;
    document.getElementById('anAdmin').innerHTML = `<div class="m-card"><h3>🛠️ ภาพรวมระบบ</h3><div class="m-stats">
        ${stat('สมาชิก', `${a.active_users}/${a.users}`)}${stat('ยอดขายรวม', baht(a.sales))}${stat('ออเดอร์', a.orders)}
        ${stat('เงินในกระเป๋าทั้งหมด', baht(a.money_in_wallets))}${stat('คำขอเงินรออนุมัติ', a.pending_wallet_requests)}
        ${stat('ประกาศมือสอง', a.market_active)}${stat('ดีลมือสอง', a.market_deals)}</div>
        <h4 class="m-muted">ยอดขาย 14 วันล่าสุด (บาท)</h4>${bars(a.daily_sales, 'total', 'day')}
        <div class="m-split"><div><h4 class="m-muted">ออเดอร์ตามสถานะ</h4>${bars(a.orders_by_status, 'count', 'label')}</div>
        <div><h4 class="m-muted">สินค้าขายดี</h4>${a.top_products.length ? a.top_products.map(p=>`<div class="m-row"><span>${esc(p.name)}</span><b>${p.qty} ชิ้น</b></div>`).join('') : '<p class="m-muted">ยังไม่มียอดขาย</p>'}</div></div></div>`;
  },
});
