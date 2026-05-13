document.getElementById('watchKeyword')?.addEventListener('input', (e)=>renderBatchStockResults(e.target.value));
document.getElementById('batchStockSymbols')?.addEventListener('input', updateBatchWatchlistPreview);
document.getElementById('stockFilterKeyword')?.addEventListener('input', (e)=>renderStockFilterResults(e.target.value));
document.getElementById('watchlistBatchModal')?.addEventListener('click', (e)=>{
  if(e.target.id === 'watchlistBatchModal') closeBatchWatchlistDialog();
});
document.getElementById('stockFilterModal')?.addEventListener('click', (e)=>{
  if(e.target.id === 'stockFilterModal') closeStockFilterDialog();
});
document.addEventListener('keydown', (e)=>{
  if(e.key === 'Escape'){
    closeBatchWatchlistDialog();
    closeStockFilterDialog();
    closeThemeReportManager();
  }
});
document.getElementById('themeReportModal')?.addEventListener('click', (e)=>{
  if(e.target.id === 'themeReportModal') closeThemeReportManager();
});
initServerConfigPicker();
initCollapsibleSections();
checkThemeReportStatus({silent:true});
window.addEventListener('pageshow', hideLoadingProgress);
if(document.readyState !== 'loading') hideLoadingProgress();
renderBatchStockResults();
seedStockFilterSelectionsFromInput();
updateStockFilterSummary();
refreshThemeSelectorOptions();
populateStockMetaControls();
refreshStockMetaFilterOptions();
applyNotesToTableAndCards();
STOCK_META_GROUPS.forEach((group)=>{
  document.getElementById(`stockMetaFilter-${group.id}`)?.addEventListener('change', (event)=>{
    applyStockMetaFilters();
    submitConfig({ page: '1', [event.target.name]: event.target.value });
  });
});

const themeSelectorFields = [
  document.querySelector('[name="theme_signal_bucket"]'),
  document.querySelector('[name="theme_signal_code"]'),
  document.querySelector('[name="theme_volume_ratio"]'),
].filter(Boolean);
themeSelectorFields.forEach((filter)=>{
  filter.addEventListener('change', ()=>{
    applyThemeSelectorInPlace();
    window.clearTimeout(filter._themeSubmitTimer);
    filter._themeSubmitTimer = window.setTimeout(submitThemeSelectorFilters, 120);
  });
});
const themeSummaryInput = document.querySelector('[name="theme_summary"]');
if(themeSummaryInput){
  themeSummaryInput.addEventListener('change', ()=>submitConfig({page: '1', theme_summary: themeSummaryInput.value || ''}));
}
const stockMetaTextFilters = [
  document.getElementById('stockMetaFilter-note'),
  document.getElementById('stockMetaFilter-stock'),
].filter(Boolean);
stockMetaTextFilters.forEach((filter)=>{
  filter.addEventListener('input', applyStockMetaFilters);
  filter.addEventListener('change', (event)=>{
    applyStockMetaFilters();
    submitConfig({ page: '1', [event.target.name]: event.target.value });
  });
});
function watchlistSignature(symbols){
  return symbols.map(normalizeWatchlistSymbol).join(',');
}
function restoreBrowserWatchlistIfAvailable(options={}){
  const raw = localStorage.getItem(WATCHLIST_STORAGE_KEY);
  if(!raw) return false;
  try {
    const symbols = JSON.parse(raw);
    if(!Array.isArray(symbols) || symbols.length === 0) return false;
    const before = watchlistSignature(getWatchlistSymbols());
    setWatchlistSymbols(symbols.map(String));
    const after = watchlistSignature(getWatchlistSymbols());
    if(options.submit && after !== before) submitConfig({tab: 'watchlist', page: '1'});
    return true;
  } catch(e) {
    return false;
  }
}
const hasSavedWatchlist = Boolean(localStorage.getItem(WATCHLIST_STORAGE_KEY));
if(hasSavedWatchlist && !window.location.search.includes('custom_watchlist=')){
  restoreBrowserWatchlistIfAvailable({submit: true});
}
function autoSubmitConfig(event){
  const overrides = {};
  if(event?.target?.name === 'tab'){
    overrides.page = '1';
    if(event.target.value === 'watchlist') restoreBrowserWatchlistIfAvailable();
  }
  submitConfig(overrides);
}
document.getElementById('cfgForm')?.addEventListener('submit', (event)=>{
  syncStockMetaPayload();
  showLoadingProgress('更新儀表板');
});
const AUTO_SUBMIT_FIELDS = new Set(['tab','industry','period','interval','limit','group_filter','subgroup_filter','show_target_price','compact_progress','card_sort']);
document.getElementById('cfgForm')?.addEventListener('change', (event)=>{
  const fieldName = event.target?.name;
  if(fieldName === 'cards_per_row'){
    dashboardCardsPerRow = Math.min(Math.max(Number(event.target.value) || 3, 1), 15);
    updateResponsiveGrid();
    syncRenderOnlyUrlParams();
    showWatchlistStatus(`已改成每列 ${dashboardCardsPerRow} 檔，未重新下載行情或重算篩選。`);
    return;
  }
  if(fieldName === 'show_volume'){
    dashboardShowVolume = String(event.target.value) === '1';
    renderDashboardPage(dashboardCurrentPage);
    showWatchlistStatus(`已${dashboardShowVolume ? '開啟' : '關閉'}量K線，保留目前頁碼且未重新下載行情。`);
    return;
  }
  if(fieldName === 'show_price'){
    dashboardShowPrice = String(event.target.value) === '1';
    renderDashboardPage(dashboardCurrentPage);
    showWatchlistStatus(`已${dashboardShowPrice ? '開啟' : '關閉'}價K線，保留目前頁碼且未重新下載行情。`);
    return;
  }
  if(fieldName === 'table_theme_meta'){
    setTableThemeMetaVisibility(event.target.value);
    return;
  }
  if(fieldName === 'card_theme_meta'){
    setCardThemeMetaVisibility(event.target.value);
    return;
  }
  if(AUTO_SUBMIT_FIELDS.has(event.target?.name)) autoSubmitConfig(event);
});
document.querySelector('[name="status_filter"]')?.addEventListener('change', applyStatusFilterInPlace);
