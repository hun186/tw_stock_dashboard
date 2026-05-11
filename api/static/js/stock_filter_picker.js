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
