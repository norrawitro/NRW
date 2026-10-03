/* wallet.js — กระเป๋าเงิน: ยอดเงิน, ตารางธุรกรรม, ป้ายยอดเงินมุมขวาบน */
/* ============================================================
   RENDER: WALLET
   ============================================================ */
function renderWallet(){
  const w = State.wallet;
  document.getElementById('walletBalanceBig').textContent = '฿'+w.balance.toLocaleString();
  document.getElementById('walletTokenBig').textContent = w.token.toLocaleString();
  document.getElementById('txBody').innerHTML = w.tx.map(t=>`
    <tr><td>${t.date}</td><td>${t.desc}</td>
    <td class="tx-amt ${t.amount>0?'plus':'minus'}">${t.amount>0?'+':''}${t.amount.toLocaleString()} ฿</td>
    <td><span class="tx-status">${t.status}</span></td></tr>`).join('');
}
function updateWalletChips(){
  document.getElementById('walletChip').textContent = '฿'+State.wallet.balance.toLocaleString();
  document.getElementById('wsBalance').textContent = '฿'+State.wallet.balance.toLocaleString();
  document.getElementById('wsToken').textContent = State.wallet.token.toLocaleString();
}
