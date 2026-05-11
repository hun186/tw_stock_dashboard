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
function intradayRefreshUrl(){
  const url = new URL(window.location.href);
  url.searchParams.set('_intraday_refresh', String(Date.now()));
  return url.toString();
}
async function refreshIntradayInPlace({force=false, reason='背景自動更新'}={}){
  if(refreshIntradayInPlace.busy || document.hidden || (!force && !isTwTradingHours())) return;
  refreshIntradayInPlace.busy = true;
  try {
    const response = await fetch(intradayRefreshUrl(), { cache: 'no-store' });
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
    refreshIntradayInPlace.lastSuccessAt = Date.now();
    if(reason !== '背景自動更新') showWatchlistStatus(`${reason}完成，已補抓最新即時K線。`);
  } catch(e) {
    console.warn('即時K線背景刷新失敗，改用下次排程重試', e);
  } finally {
    refreshIntradayInPlace.busy = false;
  }
}
function refreshIntradayAfterResume(reason){
  if(!isIntradayMode) return;
  window.setTimeout(()=>refreshIntradayInPlace({force: isTwTradingHours(), reason}), 250);
}
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
