/* modules/iot.js — จัดการอุปกรณ์ IoT: ลงทะเบียน ESP32 (ได้ device key), ดูค่าล่าสุด, กราฟ, ส่งคำสั่ง
   API: GET/POST /iot/my/devices · GET /iot/my/devices/{id}/readings · POST /iot/my/devices/{id}/commands
   ESP32: POST /iot/device/data + GET /iot/device/commands (header X-Device-Key) */
registerModule('iot', {
  sub: 'เชื่อม ESP32 ของคุณ ดูค่าเซนเซอร์แบบเรียลไทม์ และสั่งงานอุปกรณ์',
  async render(el){
    if(!State.me) return loginGate(el, 'ระบบ IoT');
    this.el = el;
    const d = await api('/iot/my/devices'); if(!d) return;
    el.innerHTML = `<div class="m-row"><span class="m-muted">ค่าล่าสุดจากอุปกรณ์</span><button class="btn-ghost m-sm" id="ioRefresh">🔄 รีเฟรช</button></div>
      <div class="m-split"><div>${d.devices.map(v=>`<div class="m-card"><div class="m-row"><b>📡 ${esc(v.name)}</b><small class="m-muted">${esc(v.device_id)}</small></div>
        <div class="m-stats">${Object.entries(v.latest).map(([k,x])=>`<div class="m-stat" data-chart="${esc(v.device_id)}" data-sensor="${esc(k)}" style="cursor:pointer" title="ดูกราฟ">
          <div class="m-stat-v">${x.value}${esc(x.unit)}</div><div class="m-muted">${esc(k)} · ${esc(x.at)}</div></div>`).join('') || '<p class="m-muted">ยังไม่มีข้อมูลจากอุปกรณ์</p>'}</div>
        <div id="chart-${esc(v.device_id)}"></div>
        <div class="m-row"><input id="cmd-${esc(v.device_id)}" class="m-input" placeholder="คำสั่ง เช่น LED_ON"><button class="btn-ghost m-sm" data-cmd="${esc(v.device_id)}">ส่งคำสั่ง</button></div></div>`).join('') || '<p class="m-muted">ยังไม่มีอุปกรณ์</p>'}</div>
      <div><div class="m-card m-form"><h3>➕ เพิ่มอุปกรณ์</h3><input id="ioId" class="m-input" placeholder="device_id เช่น esp32-bedroom"><input id="ioName" class="m-input" placeholder="ชื่อเรียก">
        <button class="btn-primary" id="ioAdd">ลงทะเบียน</button><div id="ioKey"></div></div>
        <div class="m-card"><h3>📘 โค้ดฝั่ง ESP32</h3><div class="m-pre">POST ${esc(location.origin)}/iot/device/data
Header: X-Device-Key: &lt;key&gt;
{"device_id":"esp32-bedroom","temperature":25.4,"humidity":61}

GET ${esc(location.origin)}/iot/device/commands
Header: X-Device-Key: &lt;key&gt;</div></div></div></div>`;
    el.onclick = e=>this.click(e);
  },
  async click(e){
    const t = e.target.closest('[data-chart],[data-cmd],#ioAdd,#ioRefresh'); if(!t) return;
    if(t.id==='ioRefresh') return this.render(this.el);
    if(t.dataset.chart){
      const d = await api(`/iot/my/devices/${encodeURIComponent(t.dataset.chart)}/readings?sensor=${encodeURIComponent(t.dataset.sensor)}`); if(!d) return;
      document.getElementById('chart-'+t.dataset.chart).innerHTML = `<h4 class="m-muted">${esc(d.sensor)} — ${d.points.length} ค่าล่าสุด</h4>` + bars(d.points.map(p=>({v:p.v, t:p.t.slice(11)})), 'v', 't');
    }
    if(t.dataset.cmd){
      const command = document.getElementById('cmd-'+t.dataset.cmd).value.trim();
      if(command && await api(`/iot/my/devices/${encodeURIComponent(t.dataset.cmd)}/commands`, {json:{command}})) toast('ส่งคำสั่งแล้ว อุปกรณ์จะได้รับตอนดึงคำสั่งครั้งถัดไป');
    }
    if(t.id==='ioAdd'){
      const r = await api('/iot/my/devices', {json:{device_id:document.getElementById('ioId').value.trim(), name:document.getElementById('ioName').value.trim()}});
      if(r){ await this.render(this.el); document.getElementById('ioKey').innerHTML = `<p class="m-warn-box">🔑 Device key (แสดงครั้งเดียว — คัดลอกเก็บไว้ใส่ใน ESP32):<br><code>${esc(r.key)}</code></p>`; }
    }
  },
});
