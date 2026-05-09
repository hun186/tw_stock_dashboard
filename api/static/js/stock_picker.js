const batchSelectedSymbols = new Map();
function getStockLabel(stock){
  return `${stock.symbol} - ${stock.name || ''} (${stock.group || '未分類'}${stock.subgroup ? ' / ' + stock.subgroup : ''})`;
}
function splitStockTokens(value){
  return String(value || '').split(/[\\s,，、;；]+/).map(x => x.trim()).filter(Boolean);
}
function stockMatchesKeyword(stock, keyword=''){
  const kw = keyword.trim().toLowerCase();
  return !kw || [stock.symbol, stock.name, stock.group, stock.subgroup, stock.summary]
    .filter(Boolean)
    .some(v => String(v).toLowerCase().includes(kw));
}
function syncVisibleStockPickerSelections(selectedSymbols, checkboxSelector, options={}){
  const skipDisabled = options.skipDisabled !== false;
  document.querySelectorAll(checkboxSelector).forEach((el)=>{
    const key = normalizeWatchlistSymbol(el.value);
    if(el.checked && (!skipDisabled || !el.disabled)) selectedSymbols.set(key, el.value);
    else selectedSymbols.delete(key);
  });
}
function getStockPickerCheckedSymbols(selectedSymbols, syncFn){
  syncFn();
  return Array.from(selectedSymbols.values());
}
function renderStockPickerResults({ keyword='', containerId, stocks, selectedSymbols, checkboxClass, onChange, updatePreview, emptyText, rowState }){
  const container = document.getElementById(containerId);
  if(!container) return;
  const rows = stocks.filter(r => stockMatchesKeyword(r, keyword)).slice(0, 200);
  const checkedKeys = new Set(selectedSymbols.keys());
  if(!rows.length){
    container.innerHTML = `<div class='watchlist-batch-item'>${emptyText(keyword)}</div>`;
    updatePreview();
    return;
  }
  container.innerHTML = rows.map((r)=>{
    const state = rowState ? rowState(r) : { disabled: false, itemClass: '', suffix: '' };
    const key = normalizeWatchlistSymbol(r.symbol);
    const disabled = Boolean(state.disabled);
    const checked = checkedKeys.has(key) && !disabled;
    return `<label class='watchlist-batch-item${state.itemClass || ''}'>
      <input class='${checkboxClass}' type='checkbox' value="${r.symbol}" ${checked ? 'checked' : ''} ${disabled ? 'disabled' : ''} onchange='${onChange}'>
      <span class="batch-stock-label">${getStockLabel(r)}${state.suffix || ''}</span>
    </label>`;
  }).join('');
  updatePreview();
}
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
const stockFilterSelectedSymbols = new Map();
function parseStockFilterValue(){
  return splitStockTokens(document.getElementById('stockMetaFilter-stock')?.value || '');
}
function seedStockFilterSelectionsFromInput(){
  stockFilterSelectedSymbols.clear();
  const tokens = parseStockFilterValue();
  if(!tokens.length) return;
  const tokenSet = new Set(tokens.map(normalizeWatchlistSymbol));
  const lowerTokens = tokens.map((token)=>token.toLowerCase());
  stockFilterStocks.forEach((stock)=>{
    const key = normalizeWatchlistSymbol(stock.symbol);
    const symbol = String(stock.symbol || '').toLowerCase();
    const name = String(stock.name || '').toLowerCase();
    const summary = String(stock.summary || '').toLowerCase();
    if(tokenSet.has(key) || lowerTokens.some((token)=>symbol.includes(token) || name.includes(token) || summary.includes(token))){
      stockFilterSelectedSymbols.set(key, stock.symbol);
    }
  });
}
function syncVisibleStockFilterSelections(){
  syncVisibleStockPickerSelections(stockFilterSelectedSymbols, '.stock-filter-check');
}
function getStockFilterCheckedSymbols(){
  return getStockPickerCheckedSymbols(stockFilterSelectedSymbols, syncVisibleStockFilterSelections);
}
function updateStockFilterSummary(){
  const button = document.getElementById('stockFilterButton');
  if(!button) return;
  const symbols = parseStockFilterValue();
  if(!symbols.length){
    button.textContent = '選擇自選股';
    button.title = '未套用股名／代號篩選';
    return;
  }
  button.textContent = `已選 ${symbols.length} 筆條件`;
  button.title = symbols.join('、');
}
function updateStockFilterPreview(){
  const preview = document.getElementById('stockFilterPreview');
  if(!preview) return;
  const selected = getStockFilterCheckedSymbols();
  preview.textContent = selected.length ? `準備以 ${selected.length} 檔自選股篩選。` : '未勾選時會清除股名篩選。';
}
function renderStockFilterResults(keyword=''){
  syncVisibleStockFilterSelections();
  renderStockPickerResults({
    keyword,
    containerId: 'stockFilterResults',
    stocks: stockFilterStocks,
    selectedSymbols: stockFilterSelectedSymbols,
    checkboxClass: 'stock-filter-check batch-stock-check',
    onChange: 'syncVisibleStockFilterSelections(); updateStockFilterPreview()',
    updatePreview: updateStockFilterPreview,
    emptyText: (kw)=>stockFilterStocks.length ? `找不到符合「${kw}」的自選股` : '目前沒有自選股可供股名篩選',
  });
}
function openStockFilterDialog(){
  const modal = document.getElementById('stockFilterModal');
  if(!modal) return;
  seedStockFilterSelectionsFromInput();
  modal.classList.add('is-open');
  renderStockFilterResults(document.getElementById('stockFilterKeyword')?.value || '');
  setTimeout(()=>document.getElementById('stockFilterKeyword')?.focus(), 0);
}
function closeStockFilterDialog(){
  syncVisibleStockFilterSelections();
  document.getElementById('stockFilterModal')?.classList.remove('is-open');
}
function selectVisibleStockFilterStocks(checked){
  document.querySelectorAll('.stock-filter-check:not(:disabled)').forEach((el)=>{ el.checked = checked; });
  syncVisibleStockFilterSelections();
  updateStockFilterPreview();
}
function setStockFilterValue(symbols){
  const input = document.getElementById('stockMetaFilter-stock');
  if(input) input.value = symbols.join(',');
  updateStockFilterSummary();
}
function applyStockFilterSelection(){
  const selected = getStockFilterCheckedSymbols();
  setStockFilterValue(selected);
  closeStockFilterDialog();
  applyStockMetaFilters();
  submitConfig({ page: '1', stock_meta_stock: selected.join(',') });
}
function clearStockFilterSelection(){
  stockFilterSelectedSymbols.clear();
  setStockFilterValue([]);
  renderStockFilterResults(document.getElementById('stockFilterKeyword')?.value || '');
  closeStockFilterDialog();
  applyStockMetaFilters();
  submitConfig({ page: '1', stock_meta_stock: '' });
}
