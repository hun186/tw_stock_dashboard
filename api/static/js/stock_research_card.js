function researchCardValue(value){
  const text = String(value ?? '').trim();
  return text || '-';
}
function stockResearchBySymbol(symbol){
  const item = Array.isArray(dashboardRenderItems)
    ? dashboardRenderItems.find((entry)=>String(entry.symbol || '') === String(symbol || ''))
    : null;
  return item?.research || null;
}
function currentStockResearchMeta(symbol){
  return normalizeStockMetaEntry(getStockNotes()[symbol]);
}
function researchMetaRows(meta){
  return STOCK_META_GROUPS.map((group)=>({
    label: group.label,
    value: researchCardValue(meta[group.id]),
  })).concat([{ label: '備註', value: researchCardValue(meta.note) }]);
}
function researchMarkdownLines(research, meta){
  const title = `${researchCardValue(research.name)} (${researchCardValue(research.symbol)})`;
  const rows = [
    ['主題', research.group],
    ['次題材', research.subgroup],
    ['形勢判斷', research.status],
    ['收盤價', research.close_text],
    ['目標價', research.target_price_text],
    ['目標價/現價', research.target_ratio_text],
    ['summary', research.summary],
    ['reference_url', research.reference_url],
  ].concat(researchMetaRows(meta).map((row)=>[row.label, row.value]));
  return [`# ${title}`, '']
    .concat(rows.map(([label, value])=>`- **${label}**：${researchCardValue(value)}`))
    .join('\n');
}
function renderResearchField(label, value, { isUrl=false }={}){
  const safeValue = researchCardValue(value);
  const dd = document.createElement('dd');
  if(isUrl && safeValue !== '-' && /^https?:\/\//i.test(safeValue)){
    const link = document.createElement('a');
    link.href = safeValue;
    link.target = '_blank';
    link.rel = 'noopener noreferrer';
    link.textContent = safeValue;
    dd.appendChild(link);
  } else {
    dd.textContent = safeValue;
  }
  const dt = document.createElement('dt');
  dt.textContent = label;
  return [dt, dd];
}
function fillStockResearchCard(symbol){
  const research = stockResearchBySymbol(symbol);
  const modal = document.getElementById('stockResearchModal');
  const title = document.getElementById('stockResearchTitle');
  const subtitle = document.getElementById('stockResearchSubtitle');
  const body = document.getElementById('stockResearchBody');
  const markdown = document.getElementById('stockResearchMarkdown');
  if(!modal || !title || !subtitle || !body || !markdown || !research) return false;
  const meta = currentStockResearchMeta(research.symbol);
  title.textContent = `${researchCardValue(research.name)} (${researchCardValue(research.symbol)})`;
  subtitle.textContent = `${researchCardValue(research.group)} / ${researchCardValue(research.subgroup)}`;
  const fields = [
    ['公司名稱', research.name],
    ['代號', research.symbol],
    ['主題', research.group],
    ['次題材', research.subgroup],
    ['summary', research.summary],
    ['reference_url', research.reference_url, { isUrl: true }],
    ['形勢判斷', research.status],
    ['收盤價', research.close_text],
    ['目標價', research.target_price_text],
    ['目標價/現價', research.target_ratio_text],
  ];
  body.replaceChildren();
  const info = document.createElement('dl');
  info.className = 'research-card-fields';
  fields.forEach(([label, value, options])=>info.append(...renderResearchField(label, value, options || {})));
  const personal = document.createElement('section');
  personal.className = 'research-card-personal';
  const personalTitle = document.createElement('h4');
  personalTitle.textContent = '個人標籤欄位';
  const personalList = document.createElement('dl');
  personalList.className = 'research-card-fields';
  researchMetaRows(meta).forEach((row)=>personalList.append(...renderResearchField(row.label, row.value)));
  personal.append(personalTitle, personalList);
  body.append(info, personal);
  markdown.value = researchMarkdownLines(research, meta);
  modal.dataset.symbol = research.symbol;
  return true;
}
function openStockResearchCard(symbol){
  if(!fillStockResearchCard(symbol)){
    showWatchlistStatus('找不到可顯示的研究卡資料。');
    return;
  }
  const modal = document.getElementById('stockResearchModal');
  if(modal){
    modal.classList.add('is-open');
    modal.setAttribute('aria-hidden', 'false');
    document.getElementById('stockResearchClose')?.focus();
  }
}
function closeStockResearchCard(){
  const modal = document.getElementById('stockResearchModal');
  if(modal){
    modal.classList.remove('is-open');
    modal.setAttribute('aria-hidden', 'true');
  }
}
async function copyStockResearchMarkdown(){
  const textarea = document.getElementById('stockResearchMarkdown');
  const text = textarea?.value || '';
  if(!text) return;
  try {
    await navigator.clipboard.writeText(text);
    showWatchlistStatus('已複製研究卡 Markdown。');
  } catch(e) {
    textarea.focus();
    textarea.select();
    document.execCommand('copy');
    showWatchlistStatus('已選取並複製研究卡 Markdown。');
  }
}
document.addEventListener('keydown', (event)=>{
  if(event.key === 'Escape') closeStockResearchCard();
});
