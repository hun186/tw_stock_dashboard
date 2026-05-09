const STOCK_META_PRESET_LOOKUP = STOCK_META_GROUPS.reduce((lookup, group)=>{
  group.options.forEach((option)=>{ lookup[option] = group.id; });
  return lookup;
}, {});
function isTwTradingHours(){
  const twNow = new Date(new Date().toLocaleString('en-US', { timeZone: 'Asia/Taipei' }));
  const day = twNow.getDay();
  if(day === 0 || day === 6) return false;
  const minutes = twNow.getHours() * 60 + twNow.getMinutes();
  return minutes >= 9 * 60 && minutes <= 13 * 60 + 30;
}
function syncStockMetaPayload(){
  const payload = document.getElementById('stockMetaPayload');
  if(payload) payload.value = localStorage.getItem(NOTE_STORAGE_KEY) || '{}';
}
function serializeForm(){
  syncStockMetaPayload();
  const fd = new FormData(document.getElementById('cfgForm'));
  return Object.fromEntries(fd.entries());
}
function selectedOptionText(form, name){
  const el = form?.elements?.[name];
  if(!el || el.selectedIndex < 0) return '';
  return el.options[el.selectedIndex]?.text?.trim() || '';
}
function buildLoadingMessage(form, reason='更新儀表板'){
  const tabText = selectedOptionText(form, 'tab') || '目前股池';
  const industryText = selectedOptionText(form, 'industry');
  const periodText = selectedOptionText(form, 'period');
  const intervalText = selectedOptionText(form, 'interval');
  const countText = document.querySelector('#summaryInfo .summary-value')?.textContent?.trim() || '';
  const scope = industryText && !industryText.includes('不限') ? `${tabText}／${industryText}` : tabText;
  const cadence = [periodText, intervalText].filter(Boolean).join('・');
  const stockHint = countText ? `目前頁面 ${countText}；新篩選會由後端重新計算` : '新篩選會由後端重新計算';
  return `${reason}：已送出 ${scope}（${stockHint}）。等待伺服器回傳前，瀏覽器無法取得後端內部逐檔百分比；回傳後此區塊會更新成實際完成比例${cadence ? `（${cadence}）` : ''}。`;
}
function renderProgressRows(steps){
  return steps.map((step)=>`
    <li><span class='progress-stage-name'>${escapeHtmlAttr(step.label)}</span>
    <span class='progress-stage-ratio'>${Number(step.done || 0)} / ${Number(step.total || 0)}（${Number(step.percent || 0)}%）</span>
    <div class='progress-bar' aria-hidden='true'><span style='width:${Number(step.percent || 0)}%'></span></div>
    <small>${escapeHtmlAttr(step.detail || '')}</small></li>
  `).join('');
}
function setInlineProgress({message, current, steps, updating=false}={}){
  const panel = document.getElementById('pipelineProgress');
  if(!panel) return;
  panel.classList.toggle('is-updating', Boolean(updating));
  const msg = document.getElementById('pipelineProgressMessage');
  const currentEl = document.getElementById('pipelineProgressCurrent');
  const list = document.getElementById('pipelineProgressList');
  if(message && msg) msg.textContent = message;
  if(current && currentEl) currentEl.textContent = current;
  if(Array.isArray(steps) && list) list.innerHTML = renderProgressRows(steps);
}
function hideLoadingProgress(){
  setInlineProgress({updating:false});
}
function showLoadingProgress(reason='更新儀表板'){
  const form = document.getElementById('cfgForm');
  const waitingSteps = [
    {label:'瀏覽器送出', done:1, total:1, percent:100, detail:'已同步自選、備註與篩選參數'},
    {label:'等待後端', done:0, total:1, percent:0, detail:'後端正在讀取股池、行情與計算；此階段不再顯示假百分比'},
    ...pipelineProgressSteps.slice(2).map((step)=>({...step, done:0, percent:0})),
  ];
  setInlineProgress({
    updating:true,
    current:'等待後端回應：0%',
    message:buildLoadingMessage(form, reason),
    steps:waitingSteps,
  });
}
function submitFormWithLoading(form, reason='更新儀表板'){
  showLoadingProgress(reason);
  window.setTimeout(()=>{
    if(typeof form.requestSubmit === 'function') form.requestSubmit();
    else form.submit();
  }, 30);
}
function applyConfig(cfg){
  const form = document.getElementById('cfgForm');
  Object.entries(cfg).forEach(([k,v])=>{ if(form.elements[k]) form.elements[k].value = v; });
  syncStockMetaPayload();
  submitFormWithLoading(form, '讀取設定');
}
function submitConfig(overrides={}){
  const form = document.getElementById('cfgForm');
  Object.entries(overrides).forEach(([k,v])=>{ if(form.elements[k]) form.elements[k].value = v; });
  syncStockMetaPayload();
  submitFormWithLoading(form, '更新儀表板');
}
