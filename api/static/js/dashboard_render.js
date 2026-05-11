function filteredDashboardItems(){
  const filter = document.querySelector('[name="status_filter"]')?.value || 'all';
  return dashboardRenderItems.filter((item)=>filter === 'all' || item.bucket === filter);
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
  url.searchParams.set('page', String(dashboardCurrentPage));
  url.searchParams.set('cards_per_row', String(dashboardCardsPerRow));
  url.searchParams.set('show_volume', dashboardShowVolume ? '1' : '0');
  url.searchParams.set('show_price', dashboardShowPrice ? '1' : '0');
  window.history.replaceState(null, '', url.toString());
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
    const emptyColspan = dashboardShowTableThemeMeta ? 16 : 14;
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
  if(nav){
    nav.innerHTML = `<button type='button' onclick='goToPage(${Math.max(1, dashboardCurrentPage - 1)})' ${dashboardCurrentPage <= 1 ? 'disabled' : ''}>上一頁</button>`
      + `<button type='button' onclick='goToPage(${Math.min(totalPages, dashboardCurrentPage + 1)})' ${dashboardCurrentPage >= totalPages ? 'disabled' : ''}>下一頁</button>`;
  }
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
