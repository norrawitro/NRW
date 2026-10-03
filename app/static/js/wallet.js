/* wallet.js — กระเป๋าเงิน: ยอดเงิน, ตารางธุรกรรม, ป้ายยอดเงินมุมขวาบน */
/* ============================================================
   RENDER: WALLET
   ============================================================ */
function renderWallet(){
  const w = State.wallet;
  document.getElementById('walletBalanceBig').textContent = '฿'+w.balance.toLocaleString();
  document.getElementById('walletTokenBig').textContent = w.token.toLocaleString();
  document.getElementById('txBody').innerHTML = w.tx.map(t=>`
    <tr><td>${esc(t.date)}</td><td>${esc(t.desc)}</td>
    <td class="tx-amt ${t.amount>0?'plus':'minus'}">${t.amount>0?'+':''}${t.amount.toLocaleString()} ฿</td>
    <td><span class="tx-status">${esc(t.status)}</span></td></tr>`).join('')
    || '<tr><td colspan="4" style="text-align:center;color:var(--ink-soft);padding:20px">ยังไม่มีธุรกรรม</td></tr>';
  const reqs = w.requests || [];
  document.getElementById('reqList').innerHTML = reqs.length ? reqs.map(q=>`
    <div class="m-row"><span>${q.type==='topup'?'➕ เติม':'➖ ถอน'} ${baht(q.amount)}<br><small class="m-muted">#${q.id} · ${esc(q.date)} · ${esc(q.desc)}</small></span>
      <span class="badge st-${q.status}">${esc(q.status_label)}</span></div>`).join('')
    : '<p class="m-muted">ยังไม่มีคำขอ</p>';
}
function updateWalletChips(){
  document.getElementById('walletChip').textContent = '฿'+State.wallet.balance.toLocaleString();
  document.getElementById('wsBalance').textContent = '฿'+State.wallet.balance.toLocaleString();
  document.getElementById('wsToken').textContent = State.wallet.token.toLocaleString();
}
