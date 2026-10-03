/* main.js — เริ่มทำงานตอนเปิดหน้า */
/* ============================================================
   เริ่มทำงาน
   ============================================================ */
applyTheme();
renderSidebar();
renderPhaseLegend();
renderLauncher();
renderHero();
fetchWallet().then(updateWalletChips);
const live = MODULES.filter(isLive).length;
document.getElementById('liveCount').textContent = `เปิดใช้งานแล้ว ${live}/${MODULES.length} ระบบ`;
loadMe().then(()=>showView(location.hash.slice(1) || 'home'));   // รู้ก่อนว่าใคร login แล้วค่อยวาดหน้า
window.addEventListener('hashchange', ()=>{ const v = location.hash.slice(1); if(v && v!==State.view) showView(v); });
