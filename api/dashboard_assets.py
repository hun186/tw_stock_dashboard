"""Static dashboard CSS and JavaScript assets."""

DASHBOARD_CSS = r"""  :root{--bg:#f4f7fb;--panel:#fff;--ink:#172033;--muted:#64748b;--line:#dbe4f0;--brand:#2563eb;--brand-dark:#1d4ed8;--brand-soft:#eaf1ff;--shadow:0 14px 36px rgba(15,23,42,.09);--radius:18px}
  *{box-sizing:border-box}
  body{font-family:Arial,'Noto Sans TC',sans-serif;margin:0;line-height:1.45;color:var(--ink);background:linear-gradient(180deg,#eef4ff 0,#f7f9fc 240px,var(--bg) 100%);padding:20px}
  .page-shell{max-width:1680px;margin:0 auto}
  .hero{display:flex;justify-content:space-between;gap:18px;align-items:flex-end;margin:0 0 16px;padding:22px 24px;border:1px solid rgba(255,255,255,.7);border-radius:24px;background:linear-gradient(135deg,#12213f,#2563eb 58%,#43b5ff);box-shadow:var(--shadow);color:#fff}
  .hero h1{font-size:1.65rem;margin:0 0 6px;letter-spacing:.02em}
  .hero p{margin:0;color:rgba(255,255,255,.82);font-size:.95rem}
  .hero-badge{white-space:nowrap;background:rgba(255,255,255,.16);border:1px solid rgba(255,255,255,.28);border-radius:999px;padding:8px 12px;font-size:.88rem}
  h2{font-size:1.12rem;margin:0;color:#1e293b}
  .section-card,.control-panel{background:rgba(255,255,255,.94);border:1px solid var(--line);border-radius:var(--radius);box-shadow:var(--shadow)}
  .control-panel{padding:16px;margin-bottom:16px}
  .filter-grid{display:grid;grid-template-columns:repeat(9,minmax(0,1fr));gap:10px;align-items:stretch}
  .filter-grid > fieldset{grid-column:span 3}
  .filter-grid > .pool-settings{grid-column:span 3}
  .filter-grid > .primary-actions{grid-column:span 2}
  .filter-grid > .kline-settings{grid-column:span 4}
  fieldset{border:1px solid var(--line);border-radius:14px;padding:12px;margin:0;background:#fbfdff;min-width:0}
  legend{padding:0 7px;color:#334155;font-size:.86rem;font-weight:700}
  .field-stack{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}
  .form-field{display:grid;gap:4px;color:var(--muted);font-size:.78rem;font-weight:700;letter-spacing:.02em}
  input,select,button,textarea{font:inherit}
  input,select,textarea{width:100%;font-size:.9rem;padding:8px 10px;border:1px solid #cbd5e1;border-radius:10px;background:#fff;color:#0f172a;min-height:38px}
  input:focus,select:focus,textarea:focus{outline:2px solid rgba(37,99,235,.22);border-color:var(--brand)}
  button{font-size:.9rem;padding:8px 12px;border:1px solid #cbd5e1;border-radius:999px;background:#fff;color:#1e293b;cursor:pointer;transition:transform .16s ease,box-shadow .16s ease,border-color .16s ease,background .16s ease}
  button:hover:not(:disabled){transform:translateY(-1px);box-shadow:0 8px 18px rgba(15,23,42,.12);border-color:#94a3b8}
  button:disabled{cursor:not-allowed;opacity:.48}
  .btn-primary{background:var(--brand);border-color:var(--brand);color:#fff;font-weight:700}
  .btn-primary:hover:not(:disabled){background:var(--brand-dark);border-color:var(--brand-dark)}
  .btn-soft{background:var(--brand-soft);border-color:#bfdbfe;color:#1d4ed8;font-weight:700}
  .form-actions{display:grid;grid-template-columns:1fr;gap:12px;margin-top:14px;padding-top:14px;border-top:1px solid var(--line);align-items:stretch}
  .primary-actions,.utility-actions{position:relative;display:grid;gap:8px;align-content:start;border:1px solid #dbeafe;border-radius:16px;background:linear-gradient(180deg,#fff,#f8fbff);padding:34px 12px 12px;min-width:0}
  .primary-actions::before,.utility-actions::before{content:attr(data-title);position:absolute;top:10px;left:12px;color:#1e3a8a;font-size:.78rem;font-weight:900;letter-spacing:.06em}
  .primary-actions{grid-template-columns:1fr}
  .kline-settings .field-stack{grid-template-columns:repeat(3,minmax(0,1fr))}
  .utility-actions{grid-template-columns:repeat(4,minmax(120px,1fr))}
  .primary-actions button,.utility-actions button{width:100%;min-height:40px;display:inline-flex;align-items:center;justify-content:center;text-align:center;line-height:1.2}
  .watchlist-actions{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
  #watchlistStatus{grid-column:1 / -1;min-height:1.2em;color:#2e7d32;font-size:.86rem}
  .preset-picker{grid-column:span 2;display:grid;grid-template-columns:auto minmax(0,1fr);align-items:center;gap:8px;min-width:0;padding:6px 8px;border:1px solid #dbeafe;border-radius:999px;background:#fff}
  .preset-picker label{color:var(--muted);font-size:.78rem;font-weight:800;white-space:nowrap}
  .preset-picker select{min-width:0;min-height:34px;padding:6px 8px;border-radius:999px}
  .form-help{grid-column:1 / -1;color:var(--muted);font-size:.82rem;margin:0;padding:0 4px}
  .pipeline-progress{margin:14px 0 0;padding:14px;border:1px solid #bfdbfe;border-radius:16px;background:#f8fbff;color:#172033}
  .pipeline-progress.is-updating{border-color:#60a5fa;background:#eff6ff}
  .pipeline-progress-header{display:flex;justify-content:space-between;gap:12px;align-items:flex-start;margin-bottom:10px}
  .pipeline-progress-title{font-weight:900;color:#1e3a8a}
  .pipeline-progress-current{color:#1d4ed8;font-weight:900;white-space:nowrap}
  .pipeline-progress-message{margin:0 0 10px;color:var(--muted);font-size:.86rem}
  .pipeline-progress-list{display:grid;grid-template-columns:repeat(5,minmax(120px,1fr));gap:8px;list-style:none;padding:0;margin:0}
  .pipeline-progress-list li{border:1px solid #dbeafe;border-radius:12px;background:#fff;padding:9px;min-width:0}
  .progress-stage-name,.progress-stage-ratio{display:block;font-size:.82rem;font-weight:800}
  .progress-stage-name{color:#334155}
  .progress-stage-ratio{color:#1d4ed8;margin-top:2px}
  .progress-bar{height:7px;border-radius:999px;background:#e2e8f0;overflow:hidden;margin:7px 0}
  .progress-bar span{display:block;height:100%;border-radius:999px;background:linear-gradient(90deg,#60a5fa,#2563eb)}
  .pipeline-progress-list small{display:block;color:#64748b;font-size:.74rem;line-height:1.3}
  .pipeline-progress.is-compact{padding:8px 10px;border-radius:14px}
  .pipeline-progress.is-compact .pipeline-progress-header{align-items:center;margin-bottom:6px}
  .pipeline-progress.is-compact .pipeline-progress-title{display:inline;font-size:.88rem}
  .pipeline-progress.is-compact .pipeline-progress-message{display:none}
  .pipeline-progress.is-compact .pipeline-progress-current{font-size:.84rem}
  .pipeline-progress.is-compact .pipeline-progress-list{display:flex;gap:6px;overflow-x:auto;padding-bottom:1px}
  .pipeline-progress.is-compact .pipeline-progress-list li{display:flex;align-items:center;gap:5px;flex:0 0 auto;border-radius:999px;padding:4px 8px}
  .pipeline-progress.is-compact .progress-stage-name,.pipeline-progress.is-compact .progress-stage-ratio{display:inline;font-size:.76rem;line-height:1.1}
  .pipeline-progress.is-compact .progress-stage-ratio{margin-top:0}
  .pipeline-progress.is-compact .progress-bar,.pipeline-progress.is-compact small{display:none}
  table{border-collapse:separate;border-spacing:0;width:100%;font-size:.88rem}
  th{position:sticky;top:0;z-index:2;background:#f1f5f9;color:#334155;font-weight:800}
  td,th{border-bottom:1px solid #e2e8f0;padding:8px 9px;white-space:nowrap}
  td:first-child,th:first-child{border-left:1px solid #e2e8f0}
  td:last-child,th:last-child{border-right:1px solid #e2e8f0}
  tr:hover td{background:#f8fbff}
  table th:nth-child(6), table td:nth-child(6), table th:nth-child(7), table td:nth-child(7), table th:nth-child(8), table td:nth-child(8){text-align:right}
  .row-action-cell{text-align:center;width:42px;min-width:42px}
  .table-wrap th:nth-child(1),.table-wrap td:nth-child(1){width:42px;min-width:42px}
  .status-icon-cell{text-align:center;width:54px;min-width:54px}
  .table-wrap th:nth-child(2),.table-wrap td:nth-child(2){width:54px;min-width:54px;text-align:center}
  .symbol-cell{width:88px;min-width:88px}
  .table-wrap th:nth-child(3),.table-wrap td:nth-child(3){width:88px;min-width:88px}
  .name-cell{width:128px;min-width:128px;max-width:150px}
  .name-cell .stock-jump{display:block;max-width:128px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
  .signal-cell{min-width:180px;max-width:220px;white-space:normal;line-height:1.35;font-weight:800;color:#334155}
  .theme-cell{min-width:150px;max-width:190px}
  .theme-compact{display:flex;flex-direction:column;gap:3px;max-width:176px}
  .theme-chip{display:block;max-width:100%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;border-radius:999px;padding:2px 8px;font-size:.78rem;font-weight:800;line-height:1.35}
  .theme-chip-main{color:#1e3a8a;background:#dbeafe}
  .theme-chip-sub{color:#475569;background:#f1f5f9}
  .table-wrap th:nth-child(-n+5),.table-wrap td:nth-child(-n+5){position:sticky;background:#fff;z-index:3;box-shadow:1px 0 0 #e2e8f0}
  .table-wrap th:nth-child(-n+5){z-index:4;background:#f1f5f9}
  .table-wrap th:nth-child(1),.table-wrap td:nth-child(1){left:0}
  .table-wrap th:nth-child(2),.table-wrap td:nth-child(2){left:42px}
  .table-wrap th:nth-child(3),.table-wrap td:nth-child(3){left:96px}
  .table-wrap th:nth-child(4),.table-wrap td:nth-child(4){left:184px}
  .table-wrap th:nth-child(5),.table-wrap td:nth-child(5){left:312px}
  tr:hover td:nth-child(-n+5){background:#f8fbff}
  .theme-summary-cell{display:none;white-space:normal;min-width:260px;max-width:380px;color:#334155;line-height:1.35;padding-left:22px;border-left:1px solid #e2e8f0;overflow-wrap:anywhere}
  .source-cell{display:none;max-width:140px;overflow:hidden;text-overflow:ellipsis}
  .show-table-theme-meta .theme-summary-cell,.show-table-theme-meta .source-cell{display:table-cell}
  .source-link{color:#1565c0;font-weight:700;text-decoration:none}
  .source-link:hover,.source-link:focus{text-decoration:underline}
  .table-wrap{overflow:auto;border-radius:14px;border:1px solid #e2e8f0;background:#fff}
  .section-card{padding:16px;margin:16px 0}
  .section-header{display:flex;justify-content:space-between;gap:10px;align-items:center;margin-bottom:12px}
  .notice{border:1px solid #fde68a;background:#fffbeb;color:#92400e;border-radius:14px;padding:10px 12px;margin:0 0 12px;font-weight:700}
  .summary-strip{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;margin:0 0 12px}
  .summary-item{border:1px solid var(--line);border-radius:14px;padding:12px;background:linear-gradient(180deg,#fff,#f8fbff)}
  .summary-label{display:block;color:var(--muted);font-size:.78rem;font-weight:700}
  .summary-value{display:block;font-size:1.12rem;font-weight:800;margin-top:2px}
  .page-nav{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
  .cards-grid{display:grid;grid-template-columns:repeat(3, minmax(0,1fr));gap:14px}
  .card{margin:0;padding:12px;border:1px solid var(--line);border-radius:16px;background:#fff;box-shadow:0 8px 22px rgba(15,23,42,.06);transition:border-color .2s ease,box-shadow .2s ease,background .2s ease,transform .2s ease;overflow:visible}
  .card:hover{transform:translateY(-2px);box-shadow:0 16px 32px rgba(15,23,42,.12)}
  .card h3{font-size:.96rem;margin:0 0 8px}
  .card-title{display:flex;justify-content:space-between;align-items:flex-start;gap:8px}
  .card-title-main{display:flex;align-items:center;gap:6px;flex-wrap:wrap;min-width:0}
  .card-target-ratio{font-size:.82rem;font-weight:700;white-space:nowrap}
  .theme-title-popover{position:relative;display:inline-flex;align-items:center;outline:none;border-radius:4px}
  .theme-title-popover:hover,.theme-title-popover:focus{color:#0d47a1;text-decoration:underline;text-decoration-thickness:2px}
  .theme-title-panel{position:absolute;left:0;top:calc(100% + 6px);z-index:8;display:none;width:min(300px,70vw);padding:9px 10px;border:1px solid #bfdbfe;border-radius:12px;background:#fff;box-shadow:0 14px 30px rgba(15,23,42,.18);color:#334155;font-size:.8rem;line-height:1.4;font-weight:400;text-decoration:none}
  .theme-title-panel span{display:block;white-space:normal}
  .theme-title-panel span + span{margin-top:5px}
  .theme-title-popover:hover .theme-title-panel,.theme-title-popover:focus-within .theme-title-panel{display:block}
  .theme-card-meta{display:none;border:1px solid #dbeafe;background:#f8fbff;border-radius:12px;padding:8px 10px;margin:0 0 8px;color:#334155;font-size:.84rem}
  .show-card-theme-meta .theme-card-meta{display:block}
  .theme-card-meta p{margin:0 0 4px}
  .theme-card-meta p:last-child{margin-bottom:0}
  .card.is-jump-target{border-color:#1976d2;box-shadow:0 0 0 3px rgba(25,118,210,.16),var(--shadow);background:#f5fbff}
  .stock-jump{border:0;background:none;color:#1565c0;text-decoration:underline;cursor:pointer;padding:0;font:inherit;border-radius:4px}
  .stock-jump:hover,.stock-jump:focus{color:#0d47a1;text-decoration-thickness:2px;outline:none;box-shadow:none;transform:none}
  .note-editor{display:flex;gap:2px;align-items:center;white-space:nowrap}
  .watchlist-action{min-width:72px;cursor:pointer;padding:6px 10px}
  .watchlist-action.is-icon{display:inline-flex;align-items:center;justify-content:center;width:28px;height:28px;min-width:28px;padding:0;border-radius:999px;font-size:1.12rem;font-weight:900;line-height:1;border:1px solid #cbd5e1;background:#fff;box-shadow:0 2px 6px rgba(15,23,42,.08);transition:background .16s ease,border-color .16s ease,color .16s ease,transform .16s ease,box-shadow .16s ease}
  .watchlist-action.is-icon:hover,.watchlist-action.is-icon:focus{transform:translateY(-1px);box-shadow:0 6px 14px rgba(15,23,42,.14);outline:none}
  .watchlist-action.is-remove{color:#dc2626;border-color:#fecaca;background:#fff5f5}
  .watchlist-action.is-remove:hover,.watchlist-action.is-remove:focus{background:#fee2e2;border-color:#f87171;color:#b91c1c}
  .watchlist-action.is-add{color:#2563eb;border-color:#bfdbfe;background:#eff6ff}
  .watchlist-action.is-add:hover,.watchlist-action.is-add:focus{background:#dbeafe;border-color:#60a5fa;color:#1d4ed8}
  .watchlist-action.is-added{color:#2e7d32;background:#eef8ee;border:1px solid #9ccc9c;cursor:default}
  .watchlist-batch-modal{position:fixed;inset:0;background:rgba(0,0,0,.38);display:none;align-items:center;justify-content:center;z-index:9999;padding:16px}
  .watchlist-batch-modal.is-open{display:flex}
  .watchlist-batch-dialog{background:#fff;border-radius:18px;box-shadow:0 18px 42px rgba(0,0,0,.24);max-width:760px;width:min(760px, 100%);max-height:90vh;display:flex;flex-direction:column;overflow:hidden}
  .watchlist-batch-header,.watchlist-batch-footer{display:flex;align-items:center;justify-content:space-between;gap:8px;padding:12px 14px;border-bottom:1px solid #e5e5e5}
  .watchlist-batch-footer{border-top:1px solid #e5e5e5;border-bottom:0;justify-content:flex-end;flex-wrap:wrap}
  .watchlist-batch-body{padding:12px 14px;overflow:auto;display:grid;gap:10px}
  .watchlist-batch-row{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
  .watchlist-batch-list{border:1px solid #ddd;border-radius:12px;max-height:260px;overflow:auto;background:#fafafa}
  .watchlist-batch-item{display:flex;gap:8px;align-items:center;padding:8px 10px;border-bottom:1px solid #eee;cursor:pointer;min-height:38px}
  .watchlist-batch-item:last-child{border-bottom:0}
  .watchlist-batch-item:hover{background:#f2f7ff}
  .watchlist-batch-item.is-added{color:#777;background:#f5f5f5}
  .watchlist-batch-item .batch-stock-check{flex:0 0 16px;width:16px;min-width:16px;height:16px;min-height:16px;margin:0;padding:0;border-radius:3px}
  .watchlist-batch-item .batch-stock-label{display:block;flex:1 1 auto;min-width:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;line-height:1.35}
  .watchlist-batch-item small{color:#666;margin-left:6px}
  .watchlist-batch-paste{width:100%;min-height:70px}
  .watchlist-batch-help{color:#666;font-size:.84rem}
  .stock-filter-picker{display:block}
  .stock-filter-picker input[type='hidden']{display:none}
  .stock-filter-picker button{width:100%;min-height:38px}
  .stock-meta-cell{width:132px;min-width:132px;max-width:132px}
  .note-cell{width:calc(190px + 3em);min-width:calc(190px + 3em);max-width:calc(190px + 3em)}
  .note-editor .stock-meta-select{width:120px;min-width:0;padding:4px 6px;text-align:left;text-align-last:left;min-height:30px}
  .note-editor .stock-note-input{width:calc(170px + 3em);min-width:calc(120px + 3em);padding:4px 6px;min-height:30px}
  table th:nth-child(14), table td:nth-child(14){width:calc(190px + 3em);min-width:calc(190px + 3em);max-width:calc(190px + 3em)}
  @media (max-width: 920px){.filter-grid{grid-template-columns:repeat(2,minmax(180px,1fr))}.filter-grid > fieldset,.filter-grid > .pool-settings,.filter-grid > .primary-actions,.filter-grid > .kline-settings{grid-column:auto}.form-actions{grid-template-columns:1fr}.utility-actions{grid-template-columns:repeat(4,minmax(120px,1fr))}.pipeline-progress-list{grid-template-columns:repeat(2,minmax(160px,1fr))}.cards-grid{grid-template-columns:repeat(auto-fit,minmax(360px,1fr))}}
  @media (max-width: 760px){body{padding:10px}.hero{display:block;padding:18px}.hero-badge{display:inline-block;margin-top:12px}.filter-grid,.field-stack,.kline-settings .field-stack,.summary-strip,.pipeline-progress-list{grid-template-columns:1fr}.form-actions{gap:10px}.primary-actions{grid-template-columns:1fr;padding:32px 10px 10px;border-radius:14px}.utility-actions{grid-template-columns:repeat(2,minmax(0,1fr));padding:32px 10px 10px;border-radius:14px}.preset-picker{grid-column:1 / -1;grid-template-columns:1fr;border-radius:14px;gap:4px}.cards-grid{grid-template-columns:1fr}input,select,button{font-size:.84rem}table{font-size:.8rem}.table-wrap th:nth-child(5),.table-wrap td:nth-child(5){position:static;box-shadow:none}.signal-cell{min-width:150px;max-width:170px}}
  @media (max-width: 390px){.utility-actions{grid-template-columns:1fr}.preset-picker{grid-column:1}}
"""

DASHBOARD_JS = r"""const STOCK_META_PRESET_LOOKUP = STOCK_META_GROUPS.reduce((lookup, group)=>{
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
function saveLocal(){
  localStorage.setItem('tw_dashboard_config', JSON.stringify(serializeForm()));
  alert('設定已存到瀏覽器');
}
function loadLocal(){
  const raw = localStorage.getItem('tw_dashboard_config');
  if(!raw) return alert('找不到瀏覽器設定');
  try { applyConfig(JSON.parse(raw)); } catch(e) { alert('設定格式錯誤'); }
}
function initServerConfigPicker(){
  const el = document.getElementById('serverConfigSelect');
  el.innerHTML = "<option value=''>請選擇</option>" + serverConfigPresets.map((p, idx)=>`<option value="${idx}">${p.label} (${p.id})</option>`).join('');
}
function loadServerConfig(){
  const idx = document.getElementById('serverConfigSelect').value;
  if(idx === '') return alert('請先選擇推薦設定檔');
  const preset = serverConfigPresets[Number(idx)];
  if(!preset || typeof preset.config !== 'object') return alert('推薦設定檔格式錯誤');
  applyConfig(preset.config);
}
function exportBrowserMemory(){
  const configRaw = localStorage.getItem('tw_dashboard_config');
  const watchlistRaw = localStorage.getItem(WATCHLIST_STORAGE_KEY);
  const notesRaw = localStorage.getItem(NOTE_STORAGE_KEY);
  if(!configRaw && !watchlistRaw && !notesRaw) return alert('找不到可匯出的資料');
  const payload = {
    exported_at: new Date().toISOString(),
    config: configRaw ? JSON.parse(configRaw) : null,
    watchlist: watchlistRaw ? JSON.parse(watchlistRaw) : [],
    notes: notesRaw ? JSON.parse(notesRaw) : {},
  };
  const blob = new Blob([JSON.stringify(payload, null, 2)], {type: 'application/json'});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'tw-dashboard-backup.json';
  a.click();
  URL.revokeObjectURL(a.href);
}
function importBrowserMemory(evt){
  const file = evt.target.files[0];
  if(!file) return;
  const reader = new FileReader();
  reader.onload = () => {
    try {
      const payload = JSON.parse(reader.result);
      const cfg = payload?.config ?? payload?.data ?? payload;
      if(typeof cfg !== 'object' || cfg === null) throw new Error('invalid');
      localStorage.setItem('tw_dashboard_config', JSON.stringify(cfg));
      if(Array.isArray(payload?.watchlist)) localStorage.setItem(WATCHLIST_STORAGE_KEY, JSON.stringify(payload.watchlist.map(String)));
      if(payload?.notes && typeof payload.notes === 'object') localStorage.setItem(NOTE_STORAGE_KEY, JSON.stringify(payload.notes));
      applyConfig(cfg);
    } catch(e) {
      alert('匯入失敗：備份格式錯誤');
    }
  };
  reader.readAsText(file);
  evt.target.value = '';
}

function getWatchlistSymbols(){
  const raw = document.getElementById('customWatchlist').value.trim();
  return raw ? raw.split(',').map(x=>x.trim()).filter(Boolean) : [];
}
function setWatchlistSymbols(symbols){
  const unique = [];
  const seen = new Set();
  symbols.map(String).map(s => s.trim()).filter(Boolean).forEach((symbol)=>{
    const key = normalizeWatchlistSymbol(symbol);
    if(seen.has(key)) return;
    seen.add(key);
    unique.push(symbol);
  });
  document.getElementById('customWatchlist').value = unique.join(',');
}
function syncWatchlistUrlParam(){
  const url = new URL(window.location.href);
  const symbols = getWatchlistSymbols();
  if(symbols.length) url.searchParams.set('custom_watchlist', symbols.join(','));
  else url.searchParams.delete('custom_watchlist');
  window.history.replaceState(null, '', url.toString());
}
function saveWatchlistToBrowser(silent=false){
  const symbols = getWatchlistSymbols();
  localStorage.setItem(WATCHLIST_STORAGE_KEY, JSON.stringify(symbols));
  if(!silent) alert(`已儲存 ${symbols.length} 檔自選到瀏覽器`);
}
function loadWatchlistFromBrowser(autoSubmit=true){
  const raw = localStorage.getItem(WATCHLIST_STORAGE_KEY);
  if(!raw) return alert('找不到瀏覽器自選清單');
  try {
    const symbols = JSON.parse(raw);
    if(!Array.isArray(symbols)) throw new Error('invalid');
    setWatchlistSymbols(symbols.map(String));
    if(autoSubmit) submitConfig();
  } catch(e) {
    alert('瀏覽器自選清單格式錯誤');
  }
}
function normalizeWatchlistSymbol(symbol){
  return String(symbol || '').trim().toUpperCase().replace(/\\.(TW|TWO)$/i, '');
}
function markWatchlistButtonAdded(symbol){
  const key = normalizeWatchlistSymbol(symbol);
  document.querySelectorAll('.watchlist-action[data-symbol]').forEach((btn)=>{
    if(normalizeWatchlistSymbol(btn.dataset.symbol) !== key) return;
    btn.textContent = btn.classList.contains('is-icon') ? '✓' : '已在自選';
    btn.classList.remove('is-add');
    btn.classList.add('is-added');
    btn.disabled = true;
    btn.title = `${symbol} 已在自選`;
    btn.setAttribute('aria-label', `${symbol} 已在自選`);
    btn.removeAttribute('onclick');
  });
}
function markWatchlistStockRemoved(symbol){
  const key = normalizeWatchlistSymbol(symbol);
  document.querySelectorAll('tr[data-symbol], .card[data-symbol]').forEach((el)=>{
    if(normalizeWatchlistSymbol(el.dataset.symbol) !== key) return;
    el.dataset.removed = '1';
    el.style.display = 'none';
  });
  document.querySelectorAll('.watchlist-action[data-symbol]').forEach((btn)=>{
    if(normalizeWatchlistSymbol(btn.dataset.symbol) !== key) return;
    btn.textContent = btn.classList.contains('is-icon') ? '✓' : '已移出';
    btn.disabled = true;
    btn.title = `${symbol} 已移出自選`;
    btn.setAttribute('aria-label', `${symbol} 已移出自選`);
  });
}
function showWatchlistStatus(message){
  const el = document.getElementById('watchlistStatus');
  if(!el) return;
  el.textContent = message;
  window.clearTimeout(showWatchlistStatus.timer);
  showWatchlistStatus.timer = window.setTimeout(()=>{ el.textContent = ''; }, 2500);
}
function addWatchlistStock(symbol, options={}){
  const symbols = getWatchlistSymbols();
  const key = normalizeWatchlistSymbol(symbol);
  const exists = symbols.some(s => normalizeWatchlistSymbol(s) === key);
  if(!exists) symbols.push(symbol);
  setWatchlistSymbols(symbols);
  saveWatchlistToBrowser(true);
  syncWatchlistUrlParam();
  markWatchlistButtonAdded(symbol);
  if(options.stayOnPage){
    showWatchlistStatus(exists ? `${symbol} 已在自選股` : `已加入 ${symbol} 到自選股`);
    return;
  }
  if(options.openWatchlist){
    submitConfig({tab: 'watchlist', page: '1'});
    return;
  }
  submitConfig();
}
function removeWatchlistStock(symbol, options={}){
  const key = normalizeWatchlistSymbol(symbol);
  const symbols = getWatchlistSymbols().filter(s => normalizeWatchlistSymbol(s) !== key);
  setWatchlistSymbols(symbols);
  saveWatchlistToBrowser(true);
  syncWatchlistUrlParam();
  if(options.stayOnPage){
    markWatchlistStockRemoved(symbol);
    showWatchlistStatus(`已將 ${symbol} 移出自選股，剩餘 ${symbols.length} 檔`);
    applyStockMetaFilters();
    return;
  }
  submitConfig();
}
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
function refreshStockMetaFilterOptions(){
  STOCK_META_GROUPS.forEach((group)=>{
    const filter = document.getElementById(`stockMetaFilter-${group.id}`);
    if(!filter) return;
    const currentValue = filter.value || 'all';
    const availableOptions = new Set(stockMetaFilterOptions[group.id] || []);
    const hasEmpty = Boolean(stockMetaFilterHasEmpty[group.id]);
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
  }
});
initServerConfigPicker();
window.addEventListener('pageshow', hideLoadingProgress);
if(document.readyState !== 'loading') hideLoadingProgress();
renderBatchStockResults();
seedStockFilterSelectionsFromInput();
updateStockFilterSummary();
populateStockMetaControls();
refreshStockMetaFilterOptions();
applyNotesToTableAndCards();
STOCK_META_GROUPS.forEach((group)=>{
  document.getElementById(`stockMetaFilter-${group.id}`)?.addEventListener('change', (event)=>{
    applyStockMetaFilters();
    submitConfig({ page: '1', [event.target.name]: event.target.value });
  });
});
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
"""
