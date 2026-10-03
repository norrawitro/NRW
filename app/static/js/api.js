/* api.js — fetchWallet(), fetchCloud(), fmtSize() — โหลดข้อมูลจาก server */
// ── API: โหลด wallet จริงจาก server ─────────────────────────
async function fetchWallet(){
  try{
    const r = await fetch('/wallet');
    if(r.status===401){ return State.wallet; }
    const d = await r.json();
    State.wallet = {balance:d.balance, token:d.token, tx:d.tx};
  } catch(e){}
  return State.wallet;
}

// ── API: โหลด cloud จริงจาก server ──────────────────────────
async function fetchCloud(){
  try{
    const cur = State.cloudPath[State.cloudPath.length-1].id;
    const r = await fetch('/cloud' + (cur===null ? '' : '?folder_id='+cur));
    if(r.status===401){ return; }
    const d = await r.json();
    State.storage = d.storage;
    State.cloudItems = d.items;
  } catch(e){}
}
function fmtSize(bytes){
  if(bytes==null) return '—';
  if(bytes < 1024) return bytes+' B';
  if(bytes < 1024*1024) return (bytes/1024).toFixed(0)+' KB';
  return (bytes/1024/1024).toFixed(1)+' MB';
}
