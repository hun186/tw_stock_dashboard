function syncVisibleBatchSelections(){
  syncVisibleStockPickerSelections(batchSelectedSymbols, '.batch-watchlist-check');
}
function getBatchCheckedSymbols(){
  return getStockPickerCheckedSymbols(batchSelectedSymbols, syncVisibleBatchSelections);
}
function parseBatchSymbolsText(){
  return splitStockTokens(document.getElementById('batchStockSymbols')?.value || '');
}
function updateBatchWatchlistPreview(){
  const preview = document.getElementById('batchWatchlistPreview');
  if(!preview) return;
  const currentKeys = new Set(getWatchlistSymbols().map(normalizeWatchlistSymbol));
  const candidates = [...getBatchCheckedSymbols(), ...parseBatchSymbolsText()];
  const newKeys = [];
  const duplicateKeys = [];
  const seen = new Set();
  candidates.forEach((symbol)=>{
    const key = normalizeWatchlistSymbol(symbol);
    if(!key || seen.has(key)) return;
    seen.add(key);
    if(currentKeys.has(key)) duplicateKeys.push(key);
    else newKeys.push(key);
  });
  preview.textContent = `準備新增 ${newKeys.length} 檔；已在自選或重複 ${duplicateKeys.length} 檔。`;
}
function renderBatchStockResults(keyword=''){
  syncVisibleBatchSelections();
  const currentKeys = new Set(getWatchlistSymbols().map(normalizeWatchlistSymbol));
  renderStockPickerResults({
    keyword,
    containerId: 'batchStockResults',
    stocks: allStocks,
    selectedSymbols: batchSelectedSymbols,
    checkboxClass: 'batch-watchlist-check batch-stock-check',
    onChange: 'syncVisibleBatchSelections(); updateBatchWatchlistPreview()',
    updatePreview: updateBatchWatchlistPreview,
    emptyText: (kw)=>`找不到符合「${kw}」的股票`,
    rowState: (stock)=>{
      const added = currentKeys.has(normalizeWatchlistSymbol(stock.symbol));
      return { disabled: added, itemClass: added ? ' is-added' : '', suffix: added ? '<small>已在自選</small>' : '' };
    },
  });
}
function openBatchWatchlistDialog(){
  const modal = document.getElementById('watchlistBatchModal');
  if(!modal) return;
  modal.classList.add('is-open');
  renderBatchStockResults(document.getElementById('watchKeyword')?.value || '');
  setTimeout(()=>document.getElementById('watchKeyword')?.focus(), 0);
}
function closeBatchWatchlistDialog(){
  syncVisibleBatchSelections();
  document.getElementById('watchlistBatchModal')?.classList.remove('is-open');
}
function selectVisibleBatchStocks(checked){
  document.querySelectorAll('.batch-watchlist-check:not(:disabled)').forEach((el)=>{ el.checked = checked; });
  syncVisibleBatchSelections();
  updateBatchWatchlistPreview();
}
function addBatchWatchlistStocks(){
  const before = getWatchlistSymbols();
  const beforeCount = before.length;
  setWatchlistSymbols([...before, ...getBatchCheckedSymbols(), ...parseBatchSymbolsText()]);
  const after = getWatchlistSymbols();
  const addedCount = after.length - beforeCount;
  if(addedCount <= 0){
    setWatchlistSymbols(before);
    updateBatchWatchlistPreview();
    return alert('沒有新的股票可加入');
  }
  saveWatchlistToBrowser(true);
  syncWatchlistUrlParam();
  batchSelectedSymbols.clear();
  closeBatchWatchlistDialog();
  showWatchlistStatus(`已批次加入 ${addedCount} 檔自選股，正在更新頁面`);
  submitConfig({tab: 'watchlist', page: '1'});
}
