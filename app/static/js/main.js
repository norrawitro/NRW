/* main.js — เริ่มทำงานตอนเปิดหน้า */
/* ============================================================
   เริ่มทำงาน
   ============================================================ */
renderSidebar();
renderPhaseLegend();
renderLauncher();
renderHero();
fetchWallet().then(updateWalletChips);
showView('home');
