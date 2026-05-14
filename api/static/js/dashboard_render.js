const THEME_SIGNAL_BUCKET_LABELS = {
  all: '全部訊號分類',
  bull: '偏多',
  observe: '觀察',
  warn: '警示',
  bear: '轉弱',
  neutral: '中性',
  watch: '資料不足 / 觀察',
};
const THEME_VOLUME_RATIO_LABELS = {
  all: '不限量能',
  '1.5': '成交量 ≥ 20日均量 1.5x',
  '2': '成交量 ≥ 20日均量 2x',
  '4': '成交量 ≥ 20日均量 4x',
};
function themeVolumeThreshold(value){
  return value === 'all' ? null : Number(value);
}
function themeSignalItemMatches(item, { bucket='all', code='all', volume='all' }={}){
  if(bucket !== 'all' && item.bucket !== bucket) return false;
  if(code !== 'all' && item.signal_code !== code) return false;
  const threshold = themeVolumeThreshold(volume);
  return threshold === null || Number(item.volume_ratio || 0) >= threshold;
}
function selectedThemeFilters(){
  return {
    bucket: document.querySelector('[name="theme_signal_bucket"]')?.value || 'all',
    code: document.querySelector('[name="theme_signal_code"]')?.value || 'all',
    volume: document.querySelector('[name="theme_volume_ratio"]')?.value || 'all',
  };
}
function normalizedSortMetricValue(item, metric){
  const raw = item?.sort_metrics?.[metric];
  if(metric === 'symbol') return String(raw || item?.symbol || '');
  const value = Number(raw);
  return Number.isFinite(value) ? value : -999999999;
}
function compareDashboardItems(a, b, metric=dashboardCardSort){
  const direction = dashboardCardSortDirection === 'asc' ? 1 : -1;
  if(metric === 'symbol'){
    return normalizedSortMetricValue(a, metric).localeCompare(normalizedSortMetricValue(b, metric), 'zh-Hant', {numeric:true}) * direction;
  }
  return (normalizedSortMetricValue(a, metric) - normalizedSortMetricValue(b, metric)) * direction;
}
function sortedDashboardItems(items){
  return [...items].sort((a, b)=>compareDashboardItems(a, b));
}
function filteredDashboardItems(){
  const filter = document.querySelector('[name="status_filter"]')?.value || 'all';
  const theme = selectedThemeFilters();
  return sortedDashboardItems(dashboardRenderItems.filter((item)=>
    (filter === 'all' || item.bucket === filter) && themeSignalItemMatches(item, theme)
  ));
}
function replaceSelectOptions(select, options, currentValue){
  if(!select) return currentValue;
  select.replaceChildren(...options.map(({ value, label })=>{
    const option = document.createElement('option');
    option.value = value;
    option.textContent = label;
    return option;
  }));
  const values = new Set(options.map((option)=>option.value));
  select.value = values.has(currentValue) ? currentValue : 'all';
  return select.value;
}
function refreshThemeSelectorOptions(){
  if(!Array.isArray(themeSignalItems) || !themeSignalItems.length) return;
  const bucketSelect = document.querySelector('[name="theme_signal_bucket"]');
  const codeSelect = document.querySelector('[name="theme_signal_code"]');
  const volumeSelect = document.querySelector('[name="theme_volume_ratio"]');
  const current = selectedThemeFilters();
  const bucketValues = new Set(themeSignalItems
    .filter((item)=>themeSignalItemMatches(item, { code: current.code, volume: current.volume }))
    .map((item)=>item.bucket)
    .filter(Boolean));
  const bucketOptions = Object.entries(THEME_SIGNAL_BUCKET_LABELS)
    .filter(([value])=>value === 'all' || bucketValues.has(value))
    .map(([value, label])=>({ value, label }));
  current.bucket = replaceSelectOptions(bucketSelect, bucketOptions, current.bucket);

  const codeLabels = new Map();
  themeSignalItems
    .filter((item)=>themeSignalItemMatches(item, { bucket: current.bucket, volume: current.volume }))
    .forEach((item)=>{
      if(item.signal_code) codeLabels.set(item.signal_code, item.signal_label || item.signal_code);
    });
  const codeOptions = [{ value: 'all', label: '全部技術訊號' }].concat(
    Array.from(codeLabels.entries())
      .sort((a, b)=>a[1].localeCompare(b[1], 'zh-Hant'))
      .map(([value, label])=>({ value, label }))
  );
  current.code = replaceSelectOptions(codeSelect, codeOptions, current.code);

  const volumeOptions = Object.entries(THEME_VOLUME_RATIO_LABELS)
    .filter(([value])=>value === 'all' || themeSignalItems.some((item)=>themeSignalItemMatches(item, { bucket: current.bucket, code: current.code, volume: value })))
    .map(([value, label])=>({ value, label }));
  replaceSelectOptions(volumeSelect, volumeOptions, current.volume);
}
function applyThemeSelectorInPlace(){
  refreshThemeSelectorOptions();
  renderDashboardPage(1);
}
function submitThemeSelectorFilters(){
  const form = document.getElementById('cfgForm');
  submitConfig({
    page: '1',
    theme_signal_bucket: form?.elements?.theme_signal_bucket?.value || 'all',
    theme_signal_code: form?.elements?.theme_signal_code?.value || 'all',
    theme_volume_ratio: form?.elements?.theme_volume_ratio?.value || 'all',
    theme_summary: form?.elements?.theme_summary?.value || '',
  });
}
function escapeHtmlAttr(value){
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll("'", '&#39;')
    .replaceAll('"', '&quot;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;');
}
function selectedCardHtml(item){
  if(dashboardShowVolume && dashboardShowPrice && item.card_html_with_volume_price) return item.card_html_with_volume_price;
  if(dashboardShowVolume && !dashboardShowPrice && item.card_html_with_volume_no_price) return item.card_html_with_volume_no_price;
  if(!dashboardShowVolume && dashboardShowPrice && item.card_html_without_volume_price) return item.card_html_without_volume_price;
  if(!dashboardShowVolume && !dashboardShowPrice && item.card_html_without_volume_no_price) return item.card_html_without_volume_no_price;
  if(dashboardShowVolume && item.card_html_with_volume) return item.card_html_with_volume;
  if(!dashboardShowVolume && item.card_html_without_volume) return item.card_html_without_volume;
  return item.card_html || '';
}
function applyTableThemeMetaVisibility(){
  document.documentElement.classList.toggle('show-table-theme-meta', dashboardShowTableThemeMeta);
  const control = document.getElementById('tableThemeMetaToggle');
  if(control) control.value = dashboardShowTableThemeMeta ? '1' : '0';
}
function applyCardThemeMetaVisibility(){
  document.documentElement.classList.toggle('show-card-theme-meta', dashboardShowCardThemeMeta);
  const control = document.getElementById('cardThemeMetaToggle');
  if(control) control.value = dashboardShowCardThemeMeta ? '1' : '0';
}
function applyThemeMetaVisibility(){
  applyTableThemeMetaVisibility();
  applyCardThemeMetaVisibility();
}
function toggleTableThemeMeta(){
  dashboardShowTableThemeMeta = !dashboardShowTableThemeMeta;
  applyTableThemeMetaVisibility();
  renderDashboardPage(dashboardCurrentPage);
  showWatchlistStatus(`已${dashboardShowTableThemeMeta ? '顯示' : '隱藏'}總表摘要/來源，未更新儀表板或變更個股排序。`);
}
function toggleCardThemeMeta(){
  dashboardShowCardThemeMeta = !dashboardShowCardThemeMeta;
  applyCardThemeMetaVisibility();
  showWatchlistStatus(`已${dashboardShowCardThemeMeta ? '顯示' : '隱藏'}K線摘要/來源，未更新儀表板或變更個股排序。`);
}
function setTableThemeMetaVisibility(value){
  dashboardShowTableThemeMeta = String(value) === '1';
  applyTableThemeMetaVisibility();
  renderDashboardPage(dashboardCurrentPage);
  showWatchlistStatus(`已${dashboardShowTableThemeMeta ? '顯示' : '隱藏'}總表摘要/來源，未更新儀表板或變更個股排序。`);
}
function setCardThemeMetaVisibility(value){
  dashboardShowCardThemeMeta = String(value) === '1';
  applyCardThemeMetaVisibility();
  showWatchlistStatus(`已${dashboardShowCardThemeMeta ? '顯示' : '隱藏'}K線摘要/來源，未更新儀表板或變更個股排序。`);
}
function syncRenderOnlyUrlParams(){
  const form = document.getElementById('cfgForm');
  const url = new URL(window.location.href);
  if(form?.elements?.page) form.elements.page.value = String(dashboardCurrentPage);
  if(form?.elements?.cards_per_row) form.elements.cards_per_row.value = String(dashboardCardsPerRow);
  if(form?.elements?.show_volume) form.elements.show_volume.value = dashboardShowVolume ? '1' : '0';
  if(form?.elements?.show_price) form.elements.show_price.value = dashboardShowPrice ? '1' : '0';
  if(form?.elements?.card_sort) form.elements.card_sort.value = dashboardCardSort;
  if(form?.elements?.card_sort_direction) form.elements.card_sort_direction.value = dashboardCardSortDirection;
  url.searchParams.set('page', String(dashboardCurrentPage));
  url.searchParams.set('cards_per_row', String(dashboardCardsPerRow));
  url.searchParams.set('show_volume', dashboardShowVolume ? '1' : '0');
  url.searchParams.set('show_price', dashboardShowPrice ? '1' : '0');
  url.searchParams.set('card_sort', dashboardCardSort);
  url.searchParams.set('card_sort_direction', dashboardCardSortDirection);
  window.history.replaceState(null, '', url.toString());
}

function pageNavHtml(totalPages){
  const page = dashboardCurrentPage;
  const prevPage = Math.max(1, page - 1);
  const nextPage = Math.min(totalPages, page + 1);
  const atFirst = page <= 1;
  const atLast = page >= totalPages;
  return `<button type='button' class='page-nav-button' onclick='goToPage(1)' ${atFirst ? 'disabled' : ''} aria-label='第一頁'>首頁</button>`
    + `<button type='button' class='page-nav-button' onclick='goToPage(${prevPage})' ${atFirst ? 'disabled' : ''} aria-label='上一頁'>上一頁</button>`
    + `<label class='page-jump' aria-label='跳到指定頁碼'><span class='page-jump-prefix'>第</span>`
    + `<input id='pageJumpInput' class='page-jump-input' type='number' min='1' max='${totalPages}' value='${page}' inputmode='numeric' onkeydown='handlePageJumpKey(event)' onchange='submitPageJump(this.value)' aria-label='頁碼'>`
    + `<span class='page-jump-total'>/ ${totalPages} 頁</span></label>`
    + `<button type='button' class='page-nav-button' onclick='goToPage(${nextPage})' ${atLast ? 'disabled' : ''} aria-label='下一頁'>下一頁</button>`
    + `<button type='button' class='page-nav-button' onclick='goToPage(${totalPages})' ${atLast ? 'disabled' : ''} aria-label='最後一頁'>最後一頁</button>`;
}
function submitPageJump(value){
  const items = filteredDashboardItems();
  const totalPages = Math.max(1, Math.ceil(items.length / dashboardPageSize));
  const targetPage = Math.min(Math.max(Number(value) || dashboardCurrentPage, 1), totalPages);
  goToPage(targetPage);
}
function handlePageJumpKey(event){
  if(event.key === 'Enter'){
    event.preventDefault();
    submitPageJump(event.currentTarget.value);
  }
}

async function renderDashboardPage(page=dashboardCurrentPage){
  const items = filteredDashboardItems();
  const total = items.length;
  const totalPages = Math.max(1, Math.ceil(total / dashboardPageSize));
  dashboardCurrentPage = Math.min(Math.max(Number(page) || 1, 1), totalPages);
  const start = (dashboardCurrentPage - 1) * dashboardPageSize;
  const pageItems = items.slice(start, start + dashboardPageSize);
  const table = document.querySelector('#tableWrap table');
  if(table){
    const emptyColspan = dashboardShowTableThemeMeta ? 17 : 15;
    table.innerHTML = dashboardTableHeaderHtml + (pageItems.length ? pageItems.map((item)=>item.row_html).join('') : `<tr><td colspan="${emptyColspan}">無符合條件資料</td></tr>`);
  }
  const grid = document.getElementById('cardsGrid');
  if(grid){
    grid.innerHTML = pageItems
      .map((item)=>({...item, selected_card_html: selectedCardHtml(item)}))
      .filter((item)=>item.selected_card_html)
      .map((item)=>`<div class='card' data-symbol='${escapeHtmlAttr(item.symbol)}'>${item.selected_card_html}</div>`)
      .join('');
    await executeScripts(grid);
  }
  const summaryValues = document.querySelectorAll('#summaryInfo .summary-value');
  if(summaryValues[0]) summaryValues[0].textContent = `${total} 檔`;
  if(summaryValues[1]) summaryValues[1].textContent = `${dashboardCurrentPage} / ${totalPages}`;
  if(summaryValues[2]) summaryValues[2].textContent = `${dashboardPageSize} 檔`;
  const nav = document.getElementById('pageNav');
  if(nav) nav.innerHTML = pageNavHtml(totalPages);
  populateStockMetaControls();
  applyNotesToTableAndCards();
  updateResponsiveGrid();
  applyThemeMetaVisibility();
  syncRenderOnlyUrlParams();
  hideLoadingProgress();
}
function applyStatusFilterInPlace(){
  renderDashboardPage(dashboardCurrentPage);
  const selectedText = selectedOptionText(document.getElementById('cfgForm'), 'status_filter') || '全部';
  const isAll = (document.querySelector('[name="status_filter"]')?.value || 'all') === 'all';
  const actionText = isAll ? '已恢復顯示全部形勢判斷' : `已套用「${selectedText}」形勢判斷篩選`;
  const cardNote = dashboardHasAllClientCards ? '' : '（大型股池僅表格即時篩選；若要補齊其他頁圖表再換頁更新。）';
  showWatchlistStatus(`${actionText}，仍使用目前載入的完整股池，未重新下載行情。${cardNote}`);
}
function pageHasClientCards(page){
  const items = filteredDashboardItems();
  const totalPages = Math.max(1, Math.ceil(items.length / dashboardPageSize));
  const targetPage = Math.min(Math.max(Number(page) || 1, 1), totalPages);
  const start = (targetPage - 1) * dashboardPageSize;
  return items.slice(start, start + dashboardPageSize).every((item)=>!item.has_chart_data || Boolean(selectedCardHtml(item)));
}
function goToPage(page){
  if(dashboardRenderItems.length && (dashboardHasAllClientCards || pageHasClientCards(page))){
    renderDashboardPage(page);
    return;
  }
  submitConfig({page: String(page)});
}
function scrollToStockCard(symbol){
  const key = normalizeWatchlistSymbol(symbol);
  const card = Array.from(document.querySelectorAll('.card[data-symbol]')).find((el)=>normalizeWatchlistSymbol(el.dataset.symbol) === key);
  if(!card){
    showWatchlistStatus(`找不到 ${symbol} 的曲線圖`);
    return;
  }
  document.querySelectorAll('.card.is-jump-target').forEach((el)=>el.classList.remove('is-jump-target'));
  card.scrollIntoView({behavior: 'smooth', block: 'start'});
  card.classList.add('is-jump-target');
  window.clearTimeout(scrollToStockCard.timer);
  scrollToStockCard.timer = window.setTimeout(()=>card.classList.remove('is-jump-target'), 2200);
}
function applyThemeRadarFilter(group, subgroup){
  const overrides = {group_filter: group || 'all', subgroup_filter: subgroup || 'all', page: '1'};
  submitConfig(overrides);
}
