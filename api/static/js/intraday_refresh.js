async function executeScripts(container){
  const scripts = Array.from(container.querySelectorAll('script'));
  for(const oldScript of scripts){
    const script = document.createElement('script');
    for(const attr of oldScript.attributes) script.setAttribute(attr.name, attr.value);
    if(oldScript.src){
      if(window.Plotly && oldScript.src.includes('plotly')){
        oldScript.remove();
        continue;
      }
      await new Promise((resolve, reject)=>{
        const timer = window.setTimeout(resolve, 5000);
        script.onload = () => { window.clearTimeout(timer); resolve(); };
        script.onerror = () => { window.clearTimeout(timer); reject(); };
        oldScript.replaceWith(script);
      }).catch(()=>{});
    } else {
      script.text = oldScript.textContent;
      oldScript.replaceWith(script);
    }
  }
}
const LIVE_PRICE_SNAPSHOT_STORAGE_PREFIX = 'tw_dashboard_live_snapshot:';
function taipeiDateKey(){
  const twNow = new Date(new Date().toLocaleString('en-CA', { timeZone: 'Asia/Taipei' }));
  const year = twNow.getFullYear();
  const month = String(twNow.getMonth() + 1).padStart(2, '0');
  const day = String(twNow.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}
function latestPriceSnapshotKey(){
  const url = new URL(window.location.href);
  url.searchParams.delete('_live_refresh');
  url.searchParams.delete('_intraday_refresh');
  url.searchParams.sort();
  return `${LIVE_PRICE_SNAPSHOT_STORAGE_PREFIX}${url.pathname}?${url.searchParams.toString()}`;
}
function latestPriceRefreshUrl(){
  const url = new URL(window.location.href);
  url.searchParams.set('_live_refresh', String(Date.now()));
  if(isIntradayMode) url.searchParams.set('_intraday_refresh', String(Date.now()));
  return url.toString();
}
function intradayRefreshUrl(){
  return latestPriceRefreshUrl();
}
function shouldRefreshLatestPricesNow(){
  const twNow = new Date(new Date().toLocaleString('en-US', { timeZone: 'Asia/Taipei' }));
  const day = twNow.getDay();
  if(day === 0 || day === 6) return false;
  const minutes = twNow.getHours() * 60 + twNow.getMinutes();
  return minutes >= 9 * 60;
}
function collectLatestPriceSnapshot(){
  const fragments = {};
  ['summaryInfo', 'pageNav', 'tableWrap', 'cardsGrid'].forEach((id)=>{
    const element = document.getElementById(id);
    if(element) fragments[id] = element.outerHTML;
  });
  return {dateKey: taipeiDateKey(), savedAt: Date.now(), fragments};
}
function saveLatestPriceSnapshot(){
  try {
    const snapshot = collectLatestPriceSnapshot();
    const serialized = JSON.stringify(snapshot);
    // Plotly card HTML can be large; skip local persistence if it would likely
    // exceed common browser localStorage quotas. The live in-place refresh still
    // works even when this best-effort cache is not saved.
    if(serialized.length > 4_500_000) return;
    localStorage.setItem(latestPriceSnapshotKey(), serialized);
  } catch(e) {
    console.warn('最新行情本機快取儲存失敗，仍會保留目前頁面顯示', e);
  }
}
async function restoreLatestPriceSnapshot(){
  try {
    const raw = localStorage.getItem(latestPriceSnapshotKey());
    if(!raw) return false;
    const snapshot = JSON.parse(raw);
    if(!snapshot || snapshot.dateKey !== taipeiDateKey() || !snapshot.fragments) return false;
    const template = document.createElement('template');
    for(const id of ['summaryInfo', 'pageNav', 'tableWrap']){
      const html = snapshot.fragments[id];
      const current = document.getElementById(id);
      if(!html || !current) continue;
      template.innerHTML = html;
      const fresh = template.content.firstElementChild;
      if(fresh) current.replaceWith(fresh);
    }
    const gridHtml = snapshot.fragments.cardsGrid;
    const currentGrid = document.getElementById('cardsGrid');
    if(gridHtml && currentGrid){
      template.innerHTML = gridHtml;
      const freshGrid = template.content.firstElementChild;
      if(freshGrid){
        currentGrid.replaceWith(freshGrid);
        await executeScripts(freshGrid);
      }
    }
    populateStockMetaControls();
    applyNotesToTableAndCards();
    updateResponsiveGrid();
    applyThemeMetaVisibility();
    showWatchlistStatus('已先套用本機暫存的今日最新行情，並在背景確認更新。');
    return true;
  } catch(e) {
    console.warn('最新行情本機快取還原失敗，改用伺服器初始內容', e);
    return false;
  }
}
async function refreshLatestPricesInPlace({force=false, reason='背景自動更新', requireMarketDate=true}={}){
  if(refreshLatestPricesInPlace.busy || document.hidden || (!force && requireMarketDate && !shouldRefreshLatestPricesNow())) return;
  refreshLatestPricesInPlace.busy = true;
  const dataText = isIntradayMode ? '最新即時K線' : '最新行情';
  if(reason !== '背景自動更新') showWatchlistStatus(`${reason}${dataText}中；完成後會自動載入新資料。`);
  try {
    const response = await fetch(latestPriceRefreshUrl(), { cache: 'no-store' });
    if(!response.ok) throw new Error(`HTTP ${response.status}`);
    const html = await response.text();
    const doc = new DOMParser().parseFromString(html, 'text/html');
    const scrollX = window.scrollX;
    const scrollY = window.scrollY;
    ['summaryInfo', 'pageNav', 'tableWrap'].forEach((id)=>{
      const current = document.getElementById(id);
      const fresh = doc.getElementById(id);
      if(current && fresh) current.replaceWith(fresh);
    });
    const currentGrid = document.getElementById('cardsGrid');
    const freshGrid = doc.getElementById('cardsGrid');
    if(currentGrid && freshGrid){
      currentGrid.replaceWith(freshGrid);
      await executeScripts(freshGrid);
    }
    populateStockMetaControls();
    applyNotesToTableAndCards();
    updateResponsiveGrid();
    applyThemeMetaVisibility();
    window.scrollTo(scrollX, scrollY);
    requestAnimationFrame(()=>window.scrollTo(scrollX, scrollY));
    refreshLatestPricesInPlace.lastSuccessAt = Date.now();
    saveLatestPriceSnapshot();
    if(reason !== '背景自動更新') showWatchlistStatus(`${reason}完成，已自動載入${dataText}。`);
  } catch(e) {
    console.warn('最新行情背景刷新失敗，改用下次排程重試', e);
  } finally {
    refreshLatestPricesInPlace.busy = false;
  }
}
async function refreshIntradayInPlace({force=false, reason='背景自動更新'}={}){
  return refreshLatestPricesInPlace({force, reason, requireMarketDate:true});
}
function refreshIntradayAfterResume(reason){
  if(!isIntradayMode) return;
  window.setTimeout(()=>refreshIntradayInPlace({force: isTwTradingHours(), reason}), 250);
}
async function refreshLatestPricesAfterInitialRender(){
  const params = new URLSearchParams(window.location.search);
  if(params.has('_live_refresh') || params.has('_intraday_refresh')) return;
  await restoreLatestPriceSnapshot();
  window.setTimeout(()=>refreshLatestPricesInPlace({reason:'背景補抓'}), 250);
}
refreshLatestPricesAfterInitialRender();
if(isIntradayMode){
  setInterval(()=>refreshIntradayInPlace(), autoRefreshMs);
  window.addEventListener('focus', ()=>refreshIntradayAfterResume('視窗重新啟用'));
  window.addEventListener('online', ()=>refreshIntradayAfterResume('網路恢復'));
  window.addEventListener('pageshow', ()=>refreshIntradayAfterResume('頁面恢復'));
  document.addEventListener('visibilitychange', ()=>{
    if(!document.hidden) refreshIntradayAfterResume('頁面回到前景');
  });
}
function resizeDashboardCharts(){
  if(!window.Plotly?.Plots?.resize) return;
  document.querySelectorAll('#cardsGrid .js-plotly-plot').forEach((chart)=>{
    if(!chart.offsetParent) return;
    window.Plotly.Plots.resize(chart);
  });
}
function scheduleDashboardChartAutosize(){
  window.clearTimeout(scheduleDashboardChartAutosize.timer);
  requestAnimationFrame(()=>requestAnimationFrame(resizeDashboardCharts));
  scheduleDashboardChartAutosize.timer = window.setTimeout(resizeDashboardCharts, 250);
}
function updateResponsiveGrid(){
  const grid = document.getElementById('cardsGrid');
  if(!grid) return;
  const columns = Math.min(Math.max(Number(dashboardCardsPerRow) || 3, 1), 15);
  grid.style.gridTemplateColumns = `repeat(${columns}, minmax(0,1fr))`;
  scheduleDashboardChartAutosize();
}
window.addEventListener('resize', updateResponsiveGrid);
updateResponsiveGrid();
