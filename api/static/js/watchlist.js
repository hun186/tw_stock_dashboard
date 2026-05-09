function getWatchlistSymbols(){
  const raw = document.getElementById('customWatchlist').value.trim();
  return raw ? raw.split(',').map(x=>x.trim()).filter(Boolean) : [];
}
function setWatchlistSymbols(symbols){
  const unique = [];
  const seen = new Set();
  symbols.map(String).map(s => s.trim()).filter(Boolean).forEach((symbol)=>{
    const key = normalizeWatchlistSymbol(symbol);
    if(seen.has(key)) return;
    seen.add(key);
    unique.push(symbol);
  });
  document.getElementById('customWatchlist').value = unique.join(',');
}
function syncWatchlistUrlParam(){
  const url = new URL(window.location.href);
  const symbols = getWatchlistSymbols();
  if(symbols.length) url.searchParams.set('custom_watchlist', symbols.join(','));
  else url.searchParams.delete('custom_watchlist');
  window.history.replaceState(null, '', url.toString());
}
function saveWatchlistToBrowser(silent=false){
  const symbols = getWatchlistSymbols();
  localStorage.setItem(WATCHLIST_STORAGE_KEY, JSON.stringify(symbols));
  if(!silent) alert(`已儲存 ${symbols.length} 檔自選到瀏覽器`);
}
function loadWatchlistFromBrowser(autoSubmit=true){
  const raw = localStorage.getItem(WATCHLIST_STORAGE_KEY);
  if(!raw) return alert('找不到瀏覽器自選清單');
  try {
    const symbols = JSON.parse(raw);
    if(!Array.isArray(symbols)) throw new Error('invalid');
    setWatchlistSymbols(symbols.map(String));
    if(autoSubmit) submitConfig();
  } catch(e) {
    alert('瀏覽器自選清單格式錯誤');
  }
}
function normalizeWatchlistSymbol(symbol){
  return String(symbol || '').trim().toUpperCase().replace(/\\.(TW|TWO)$/i, '');
}
function markWatchlistButtonAdded(symbol){
  const key = normalizeWatchlistSymbol(symbol);
  document.querySelectorAll('.watchlist-action[data-symbol]').forEach((btn)=>{
    if(normalizeWatchlistSymbol(btn.dataset.symbol) !== key) return;
    btn.textContent = btn.classList.contains('is-icon') ? '✓' : '已在自選';
    btn.classList.remove('is-add');
    btn.classList.add('is-added');
    btn.disabled = true;
    btn.title = `${symbol} 已在自選`;
    btn.setAttribute('aria-label', `${symbol} 已在自選`);
    btn.removeAttribute('onclick');
  });
}
function markWatchlistStockRemoved(symbol){
  const key = normalizeWatchlistSymbol(symbol);
  document.querySelectorAll('tr[data-symbol], .card[data-symbol]').forEach((el)=>{
    if(normalizeWatchlistSymbol(el.dataset.symbol) !== key) return;
    el.dataset.removed = '1';
    el.style.display = 'none';
  });
  document.querySelectorAll('.watchlist-action[data-symbol]').forEach((btn)=>{
    if(normalizeWatchlistSymbol(btn.dataset.symbol) !== key) return;
    btn.textContent = btn.classList.contains('is-icon') ? '✓' : '已移出';
    btn.disabled = true;
    btn.title = `${symbol} 已移出自選`;
    btn.setAttribute('aria-label', `${symbol} 已移出自選`);
  });
}
function showWatchlistStatus(message){
  const el = document.getElementById('watchlistStatus');
  if(!el) return;
  el.textContent = message;
  window.clearTimeout(showWatchlistStatus.timer);
  showWatchlistStatus.timer = window.setTimeout(()=>{ el.textContent = ''; }, 2500);
}
function addWatchlistStock(symbol, options={}){
  const symbols = getWatchlistSymbols();
  const key = normalizeWatchlistSymbol(symbol);
  const exists = symbols.some(s => normalizeWatchlistSymbol(s) === key);
  if(!exists) symbols.push(symbol);
  setWatchlistSymbols(symbols);
  saveWatchlistToBrowser(true);
  syncWatchlistUrlParam();
  markWatchlistButtonAdded(symbol);
  if(options.stayOnPage){
    showWatchlistStatus(exists ? `${symbol} 已在自選股` : `已加入 ${symbol} 到自選股`);
    return;
  }
  if(options.openWatchlist){
    submitConfig({tab: 'watchlist', page: '1'});
    return;
  }
  submitConfig();
}
function removeWatchlistStock(symbol, options={}){
  const key = normalizeWatchlistSymbol(symbol);
  const symbols = getWatchlistSymbols().filter(s => normalizeWatchlistSymbol(s) !== key);
  setWatchlistSymbols(symbols);
  saveWatchlistToBrowser(true);
  syncWatchlistUrlParam();
  if(options.stayOnPage){
    markWatchlistStockRemoved(symbol);
    showWatchlistStatus(`已將 ${symbol} 移出自選股，剩餘 ${symbols.length} 檔`);
    applyStockMetaFilters();
    return;
  }
  submitConfig();
}
