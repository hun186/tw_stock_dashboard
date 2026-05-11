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
