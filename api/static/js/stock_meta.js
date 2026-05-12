function normalizeStockMetaEntry(entry){
  const meta = { action: '', trait: '', stage: '', risk: '', note: '' };
  if(typeof entry === 'string'){
    const legacyValue = entry.trim();
    const legacyField = STOCK_META_PRESET_LOOKUP[legacyValue];
    if(legacyField) meta[legacyField] = legacyValue;
    else meta.note = legacyValue;
    return meta;
  }
  if(entry && typeof entry === 'object'){
    STOCK_META_FIELDS.forEach((field)=>{
      meta[field] = String(entry[field] || '').trim();
    });
    meta.note = String(entry.note || entry.memo || '').trim();
  }
  return meta;
}
function isEmptyStockMeta(meta){
  return !meta.note && STOCK_META_FIELDS.every((field)=>!meta[field]);
}
function getStockNotes(){
  try {
    const raw = localStorage.getItem(NOTE_STORAGE_KEY) || '{}';
    const obj = JSON.parse(raw);
    if(!obj || typeof obj !== 'object') return {};
    return Object.fromEntries(Object.entries(obj).map(([symbol, entry])=>[symbol, normalizeStockMetaEntry(entry)]));
  } catch(e) {
    return {};
  }
}
function setStockNotes(notes){
  const compact = {};
  Object.entries(notes || {}).forEach(([symbol, entry])=>{
    const meta = normalizeStockMetaEntry(entry);
    if(!isEmptyStockMeta(meta)) compact[symbol] = meta;
  });
  localStorage.setItem(NOTE_STORAGE_KEY, JSON.stringify(compact));
}
function appendOption(parent, value, label){
  const option = document.createElement('option');
  option.value = value;
  option.textContent = label;
  parent.appendChild(option);
  return option;
}
function populateStockMetaControls(){
  document.querySelectorAll('.stock-meta-select').forEach((select)=>{
    const currentValue = select.value;
    const group = STOCK_META_GROUPS.find((item)=>item.id === select.dataset.field);
    select.replaceChildren();
    appendOption(select, '', group ? `設定${group.label}` : '未設定');
    if(group) group.options.forEach((value)=>appendOption(select, value, value));
    select.value = group?.options.includes(currentValue) ? currentValue : '';
  });
}
function stockMetaAvailabilitySymbols(){
  if(typeof filteredDashboardItems === 'function' && Array.isArray(dashboardRenderItems) && dashboardRenderItems.length){
    return filteredDashboardItems().map((item)=>String(item.symbol || '')).filter(Boolean);
  }
  return Array.from(document.querySelectorAll('tr[data-symbol]')).map((tr)=>tr.dataset.symbol).filter(Boolean);
}
function currentStockMetaFilterAvailability(){
  const options = Object.fromEntries(STOCK_META_FIELDS.map((field)=>[field, new Set()]));
  const hasEmpty = Object.fromEntries(STOCK_META_FIELDS.map((field)=>[field, false]));
  const notes = getStockNotes();
  const symbols = stockMetaAvailabilitySymbols();
  symbols.forEach((symbol)=>{
    const meta = normalizeStockMetaEntry(notes[symbol]);
    STOCK_META_FIELDS.forEach((field)=>{
      const value = String(meta[field] || '').trim();
      if(value) options[field].add(value);
      else hasEmpty[field] = true;
    });
  });
  return { options, hasEmpty };
}
function refreshStockMetaFilterOptions(){
  const availability = currentStockMetaFilterAvailability();
  STOCK_META_GROUPS.forEach((group)=>{
    const filter = document.getElementById(`stockMetaFilter-${group.id}`);
    if(!filter) return;
    const currentValue = filter.value || 'all';
    const availableOptions = availability.options[group.id] || new Set();
    const hasEmpty = Boolean(availability.hasEmpty[group.id]);
    filter.replaceChildren();
    appendOption(filter, 'all', group.allLabel);
    if(hasEmpty) appendOption(filter, 'none', group.noneLabel);
    group.options
      .filter((value)=>availableOptions.has(value))
      .forEach((value)=>appendOption(filter, value, value));
    filter.value = (currentValue === 'none' && hasEmpty) || availableOptions.has(currentValue) ? currentValue : 'all';
  });
}
function applyNotesToTableAndCards(){
  const notes = getStockNotes();
  document.querySelectorAll('tr[data-symbol]').forEach((tr)=>{
    const symbol = tr.dataset.symbol;
    const meta = normalizeStockMetaEntry(notes[symbol]);
    STOCK_META_FIELDS.forEach((field)=>{
      tr.dataset[field] = meta[field] || 'none';
      const select = tr.querySelector(`.stock-meta-select[data-field="${field}"]`);
      if(select) select.value = meta[field] || '';
    });
    tr.dataset.note = meta.note || '';
    const noteInput = tr.querySelector('.stock-note-input');
    if(noteInput && document.activeElement !== noteInput) noteInput.value = meta.note || '';
  });
  refreshStockMetaFilterOptions();
  applyStockMetaFilters();
}
function selectedStockMetaFilters(){
  const filters = Object.fromEntries(STOCK_META_GROUPS.map((group)=>[
    group.id,
    document.getElementById(`stockMetaFilter-${group.id}`)?.value || 'all'
  ]));
  filters.note = (document.getElementById('stockMetaFilter-note')?.value || '').trim().toLowerCase();
  filters.stockTokens = (document.getElementById('stockMetaFilter-stock')?.value || '')
    .split(/[\\s,，、;；]+/)
    .map((token)=>token.trim().toLowerCase())
    .filter(Boolean);
  return filters;
}
function applyStockMetaFilters(){
  const filters = selectedStockMetaFilters();
  const visibleSymbols = new Set();
  document.querySelectorAll('tr[data-symbol]').forEach((tr)=>{
    const removed = tr.dataset.removed === '1';
    const tagMatched = STOCK_META_FIELDS.every((field)=>{
      const selected = filters[field] || 'all';
      const value = tr.dataset[field] || 'none';
      return selected === 'all' || value === selected || (selected === 'none' && value === 'none');
    });
    const noteMatched = !filters.note || String(tr.dataset.note || '').toLowerCase().includes(filters.note);
    const stockMatched = !filters.stockTokens.length || filters.stockTokens.some((token)=>{
      const symbol = String(tr.dataset.symbol || '').toLowerCase();
      const symbolKey = symbol.split('.')[0];
      const name = String(tr.dataset.name || '').toLowerCase();
      const summary = String(tr.dataset.summary || '').toLowerCase();
      return symbol.includes(token) || symbolKey.includes(token) || name.includes(token) || summary.includes(token);
    });
    const visible = !removed && tagMatched && noteMatched && stockMatched;
    tr.style.display = visible ? '' : 'none';
    if(visible) visibleSymbols.add(tr.dataset.symbol);
  });
  document.querySelectorAll('.card[data-symbol]').forEach((card)=>{
    const removed = card.dataset.removed === '1';
    card.style.display = !removed && visibleSymbols.has(card.dataset.symbol) ? '' : 'none';
  });
}
function saveStockMetaBySymbol(symbol, patch){
  const notes = getStockNotes();
  const meta = normalizeStockMetaEntry(notes[symbol]);
  Object.assign(meta, patch);
  if(isEmptyStockMeta(meta)) delete notes[symbol];
  else notes[symbol] = meta;
  setStockNotes(notes);
  applyNotesToTableAndCards();
}
function saveInlineStockMeta(selectEl){
  const editor = selectEl.closest('.note-editor');
  if(!editor) return;
  const field = selectEl.dataset.field;
  if(!STOCK_META_FIELDS.includes(field)) return;
  saveStockMetaBySymbol(editor.dataset.symbol, { [field]: (selectEl.value || '').trim() });
}
function saveInlineStockNote(inputEl){
  const editor = inputEl.closest('.note-editor');
  if(!editor) return;
  window.clearTimeout(inputEl._saveTimer);
  saveStockMetaBySymbol(editor.dataset.symbol, { note: (inputEl.value || '').trim() });
}
function queueInlineStockNoteSave(inputEl){
  window.clearTimeout(inputEl._saveTimer);
  inputEl._saveTimer = window.setTimeout(()=>saveInlineStockNote(inputEl), 450);
}
