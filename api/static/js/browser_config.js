function saveLocal(){
  localStorage.setItem('tw_dashboard_config', JSON.stringify(serializeForm()));
  alert('設定已存到瀏覽器');
}
function loadLocal(){
  const raw = localStorage.getItem('tw_dashboard_config');
  if(!raw) return alert('找不到瀏覽器設定');
  try { applyConfig(JSON.parse(raw)); } catch(e) { alert('設定格式錯誤'); }
}
function initServerConfigPicker(){
  const el = document.getElementById('serverConfigSelect');
  el.innerHTML = "<option value=''>請選擇</option>" + serverConfigPresets.map((p, idx)=>`<option value="${idx}">${p.label} (${p.id})</option>`).join('');
}
function loadServerConfig(){
  const idx = document.getElementById('serverConfigSelect').value;
  if(idx === '') return alert('請先選擇推薦設定檔');
  const preset = serverConfigPresets[Number(idx)];
  if(!preset || typeof preset.config !== 'object') return alert('推薦設定檔格式錯誤');
  applyConfig(preset.config);
}
function exportBrowserMemory(){
  const configRaw = localStorage.getItem('tw_dashboard_config');
  const watchlistRaw = localStorage.getItem(WATCHLIST_STORAGE_KEY);
  const notesRaw = localStorage.getItem(NOTE_STORAGE_KEY);
  if(!configRaw && !watchlistRaw && !notesRaw) return alert('找不到可匯出的資料');
  const payload = {
    exported_at: new Date().toISOString(),
    config: configRaw ? JSON.parse(configRaw) : null,
    watchlist: watchlistRaw ? JSON.parse(watchlistRaw) : [],
    notes: notesRaw ? JSON.parse(notesRaw) : {},
  };
  const blob = new Blob([JSON.stringify(payload, null, 2)], {type: 'application/json'});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'tw-dashboard-backup.json';
  a.click();
  URL.revokeObjectURL(a.href);
}
function importBrowserMemory(evt){
  const file = evt.target.files[0];
  if(!file) return;
  const reader = new FileReader();
  reader.onload = () => {
    try {
      const payload = JSON.parse(reader.result);
      const cfg = payload?.config ?? payload?.data ?? payload;
      if(typeof cfg !== 'object' || cfg === null) throw new Error('invalid');
      localStorage.setItem('tw_dashboard_config', JSON.stringify(cfg));
      if(Array.isArray(payload?.watchlist)) localStorage.setItem(WATCHLIST_STORAGE_KEY, JSON.stringify(payload.watchlist.map(String)));
      if(payload?.notes && typeof payload.notes === 'object') localStorage.setItem(NOTE_STORAGE_KEY, JSON.stringify(payload.notes));
      applyConfig(cfg);
    } catch(e) {
      alert('匯入失敗：備份格式錯誤');
    }
  };
  reader.readAsText(file);
  evt.target.value = '';
}

