let themeReportListCache = null;
let activeThemeReportName = '';
function formatThemeReportDate(value){
  if(!value) return '';
  const dt = new Date(value);
  return Number.isNaN(dt.getTime()) ? value : dt.toLocaleString();
}
function formatThemeReportSize(bytes){
  const value = Number(bytes || 0);
  return value ? `${Math.max(1, Math.round(value / 1024))} KB` : '';
}
function formatThemeReportStatus(payload){
  if(!payload || !payload.exists) return payload?.message || '尚未找到可下載的預建報告。';
  const parts = [];
  if(payload.as_of) parts.push(`最新報告日 ${payload.as_of}`);
  if(payload.generated_at) parts.push(`更新 ${formatThemeReportDate(payload.generated_at)}`);
  if(payload.size_bytes) parts.push(formatThemeReportSize(payload.size_bytes));
  return parts.length ? `已可線上檢視 / 下載：${parts.join('｜')}` : (payload.message || '已可線上檢視 / 下載預建報告。');
}
async function checkThemeReportStatus({silent=false}={}){
  const statusEl = document.getElementById('themeReportStatus');
  const link = document.getElementById('themeReportDownloadLink');
  if(!statusEl || !link) return;
  if(!silent) statusEl.textContent = '讀取最新報告狀態中…';
  try{
    const response = await fetch('/api/theme-report/status', {headers:{'Accept':'application/json'}});
    const payload = await response.json();
    statusEl.textContent = formatThemeReportStatus(payload);
    link.classList.toggle('is-disabled', !payload.exists);
    link.setAttribute('aria-disabled', payload.exists ? 'false' : 'true');
    link.href = payload.download_url || '/api/theme-report/download';
  } catch(error){
    statusEl.textContent = '讀取失敗：請稍後重試，或確認部署是否包含 reports/*.md。';
    link.classList.add('is-disabled');
    link.setAttribute('aria-disabled', 'true');
  }
}
function renderInlineMarkdown(text){
  return escapeHtmlAttr(text || '')
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/(https?:\/\/[^\s<]+)/g, '<a href="$1" target="_blank" rel="noopener noreferrer">$1</a>');
}
function renderMarkdownReport(markdown){
  const lines = String(markdown || '').split(/\r?\n/);
  const html = [];
  let listOpen = false;
  let paragraph = [];
  function closeParagraph(){
    if(paragraph.length){
      html.push(`<p>${renderInlineMarkdown(paragraph.join(' '))}</p>`);
      paragraph = [];
    }
  }
  function closeList(){
    if(listOpen){
      html.push('</ul>');
      listOpen = false;
    }
  }
  lines.forEach((line)=>{
    const trimmed = line.trim();
    if(!trimmed){ closeParagraph(); closeList(); return; }
    const heading = trimmed.match(/^(#{1,4})\s+(.+)$/);
    if(heading){
      closeParagraph(); closeList();
      const level = heading[1].length;
      html.push(`<h${level}>${renderInlineMarkdown(heading[2])}</h${level}>`);
      return;
    }
    const item = trimmed.match(/^[-*]\s+(.+)$/);
    if(item){
      closeParagraph();
      if(!listOpen){ html.push('<ul>'); listOpen = true; }
      html.push(`<li>${renderInlineMarkdown(item[1])}</li>`);
      return;
    }
    if(trimmed.startsWith('>')){
      closeParagraph(); closeList();
      html.push(`<blockquote>${renderInlineMarkdown(trimmed.replace(/^>\s?/, ''))}</blockquote>`);
      return;
    }
    paragraph.push(trimmed);
  });
  closeParagraph();
  closeList();
  return html.join('') || '<p>這份報告沒有內容。</p>';
}
function reportButtonLabel(report){
  const title = report.title || report.name || '未命名報告';
  const meta = [report.as_of, formatThemeReportSize(report.size_bytes)].filter(Boolean).join('｜');
  return `<span>${escapeHtmlAttr(title)}</span>${meta ? `<small>${escapeHtmlAttr(meta)}</small>` : ''}`;
}
function renderThemeReportList(reports=[]){
  const listEl = document.getElementById('themeReportList');
  const statusEl = document.getElementById('themeReportListStatus');
  if(!listEl || !statusEl) return;
  statusEl.textContent = reports.length ? `共 ${reports.length} 份報告` : '尚未找到任何 reports/*.md。';
  listEl.innerHTML = reports.map((report)=>`
    <button type='button' class='theme-report-item ${report.name === activeThemeReportName ? 'is-active' : ''}' data-report-name='${escapeHtmlAttr(report.name)}'>
      ${reportButtonLabel(report)}
    </button>
  `).join('');
  listEl.querySelectorAll('[data-report-name]').forEach((button)=>{
    button.addEventListener('click', ()=>loadThemeReportContent(button.dataset.reportName));
  });
}
async function loadThemeReportList({force=false}={}){
  const statusEl = document.getElementById('themeReportListStatus');
  if(themeReportListCache && !force){
    renderThemeReportList(themeReportListCache.reports || []);
    return themeReportListCache;
  }
  if(statusEl) statusEl.textContent = '讀取歷史報告中…';
  const response = await fetch('/api/theme-report/list', {headers:{'Accept':'application/json'}});
  const payload = await response.json();
  themeReportListCache = payload;
  renderThemeReportList(payload.reports || []);
  if(payload.latest && !activeThemeReportName) await loadThemeReportContent(payload.latest.name);
  return payload;
}
async function loadThemeReportContent(name){
  if(!name) return;
  activeThemeReportName = name;
  renderThemeReportList(themeReportListCache?.reports || []);
  const article = document.getElementById('themeReportMarkdown');
  const title = document.getElementById('themeReportViewerTitle');
  const meta = document.getElementById('themeReportViewerMeta');
  const download = document.getElementById('themeReportViewerDownload');
  if(article) article.textContent = '載入報告內容中…';
  const response = await fetch(`/api/theme-report/content?name=${encodeURIComponent(name)}`, {headers:{'Accept':'application/json'}});
  const payload = await response.json();
  if(!response.ok || !payload.exists){
    if(article) article.textContent = payload.message || '讀取報告失敗。';
    return;
  }
  const report = payload.report || {};
  if(title) title.textContent = report.title || report.name || '題材報告';
  if(meta) meta.textContent = [report.as_of ? `報告日 ${report.as_of}` : '', formatThemeReportDate(report.generated_at), formatThemeReportSize(report.size_bytes)].filter(Boolean).join('｜');
  if(download){
    download.href = report.download_url || `/api/theme-report/download?name=${encodeURIComponent(name)}`;
    download.classList.remove('is-disabled');
    download.setAttribute('aria-disabled', 'false');
  }
  if(article) article.innerHTML = renderMarkdownReport(payload.content || '');
}
async function openThemeReportManager(){
  const modal = document.getElementById('themeReportModal');
  if(!modal) return;
  modal.classList.add('is-open');
  modal.setAttribute('aria-hidden', 'false');
  await loadThemeReportList();
}
function closeThemeReportManager(){
  const modal = document.getElementById('themeReportModal');
  if(!modal) return;
  modal.classList.remove('is-open');
  modal.setAttribute('aria-hidden', 'true');
}
