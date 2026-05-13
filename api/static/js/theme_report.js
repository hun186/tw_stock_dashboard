function formatThemeReportStatus(payload){
  if(!payload || !payload.exists) return payload?.message || '尚未找到可下載的預建報告。';
  const parts = [];
  if(payload.as_of) parts.push(`報告日 ${payload.as_of}`);
  if(payload.generated_at){
    const dt = new Date(payload.generated_at);
    parts.push(`更新 ${Number.isNaN(dt.getTime()) ? payload.generated_at : dt.toLocaleString()}`);
  }
  if(payload.size_bytes) parts.push(`${Math.max(1, Math.round(payload.size_bytes / 1024))} KB`);
  return parts.length ? `已可下載：${parts.join('｜')}` : (payload.message || '已可下載預建報告。');
}
async function checkThemeReportStatus({silent=false}={}){
  const statusEl = document.getElementById('themeReportStatus');
  const button = document.getElementById('themeReportCheckButton');
  const link = document.getElementById('themeReportDownloadLink');
  if(!statusEl || !button || !link) return;
  if(!silent) statusEl.textContent = '檢測預建報告中…';
  button.disabled = true;
  try{
    const response = await fetch('/api/theme-report/status', {headers:{'Accept':'application/json'}});
    const payload = await response.json();
    statusEl.textContent = formatThemeReportStatus(payload);
    link.classList.toggle('is-disabled', !payload.exists);
    link.setAttribute('aria-disabled', payload.exists ? 'false' : 'true');
    link.href = payload.download_url || '/api/theme-report/download';
  } catch(error){
    statusEl.textContent = '檢測失敗：請稍後重試，或確認部署是否包含 reports/daily_theme_report.md。';
    link.classList.add('is-disabled');
    link.setAttribute('aria-disabled', 'true');
  } finally {
    button.disabled = false;
  }
}
