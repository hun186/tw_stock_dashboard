from __future__ import annotations

import html
import json

from api.dashboard_assets import DASHBOARD_CSS, DASHBOARD_JS
from api.constants import STATUS_FILTERS
from api.data_loader import STOCK_GROUP_COLUMNS
from api.dashboard_notices import render_category_all_coverage_notice, render_limited_notice
from api.dashboard_progress import build_progress_steps, progress_steps_json, render_progress_steps_html
from api.server_configs import load_server_config_presets


def render_dashboard_page(
    analyzed_stocks,
    candidate_count,
    card_sort,
    cards_data,
    cards_per_row,
    client_render_all_cards,
    compact_progress,
    group_filter,
    industries,
    industry,
    industry_df,
    interval,
    is_limited_analysis,
    limit,
    max_serverless_analysis_stocks,
    page,
    period,
    picker_stocks,
    price_ready_count,
    progress_total_stocks,
    rendered_stock_items,
    rows,
    show_price,
    show_target_price,
    show_volume,
    signal_ready_count,
    sorted_stocks,
    source_stocks,
    status_filter,
    status_filter_values,
    stock_filter_stocks,
    stock_meta_filter_values,
    stock_meta_filters,
    stock_meta_note_filter,
    stock_meta_payload_raw,
    stock_meta_stock_filter,
    stocks,
    subgroup_filter,
    tab,
    total_pages,
    total_stocks,
    valid_groups,
    valid_subgroups,
    watchlist,
) -> str:
    industry_options = (
        "<option value='all' {}>不限產業</option>".format("selected" if industry == "all" else "")
        + "".join([
            f"<option value='{html.escape(r.industry)}' {'selected' if r.industry == industry else ''}>{html.escape(r.industry_label)}</option>"
            for r in industries.itertuples(index=False)
        ])
    )
    status_options = "".join([
        f"<option value='{k}' {'selected' if k == status_filter else ''}>{v}</option>"
        for k, v in STATUS_FILTERS.items()
        if k == "all" or k in status_filter_values
    ])
    stock_meta_filter_options = {
        field: sorted(value for value in values if value != "none")
        for field, values in stock_meta_filter_values.items()
    }
    stock_meta_filter_has_empty = {
        field: "none" in values
        for field, values in stock_meta_filter_values.items()
    }
    group_options = "<option value='all'>全部主題</option>" + "".join([
        f"<option value='{html.escape(v)}' {'selected' if v == group_filter else ''}>{html.escape(v)}</option>" for v in valid_groups
    ])
    subgroup_options = "<option value='all'>全部次題材</option>" + "".join([
        f"<option value='{html.escape(v)}' {'selected' if v == subgroup_filter else ''}>{html.escape(v)}</option>" for v in valid_subgroups
    ])

    save_payload = {
        "tab": tab,
        "industry": industry,
        "period": period,
        "interval": interval,
        "limit": limit,
        "status_filter": status_filter,
        "group_filter": group_filter,
        "subgroup_filter": subgroup_filter,
        **{f"stock_meta_{field}": value for field, value in stock_meta_filters.items()},
        "stock_meta_note": stock_meta_note_filter,
        "stock_meta_stock": stock_meta_stock_filter,
        "stock_meta_payload": stock_meta_payload_raw,
        "cards_per_row": cards_per_row,
        "custom_watchlist": ",".join(watchlist["symbol"].tolist()),
        "show_volume": "1" if show_volume else "0",
        "show_price": "1" if show_price else "0",
        "show_target_price": "1" if show_target_price else "0",
        "card_sort": card_sort,
        "compact_progress": "1" if compact_progress else "0",
        "page": page,
    }
    server_config_presets = load_server_config_presets()
    limited_notice = render_limited_notice(
        candidate_count=candidate_count,
        is_limited_analysis=is_limited_analysis,
        max_serverless_analysis_stocks=max_serverless_analysis_stocks,
    )
    category_all_coverage_notice = render_category_all_coverage_notice(
        tab=tab,
        industry=industry,
        industry_df=industry_df,
        source_stocks=source_stocks,
    )
    progress_steps = build_progress_steps(
        analyzed_count=len(analyzed_stocks),
        candidate_count=candidate_count,
        is_limited_analysis=is_limited_analysis,
        price_ready_count=price_ready_count,
        progress_total_stocks=progress_total_stocks,
        rendered_count=len(rendered_stock_items),
        signal_ready_count=signal_ready_count,
        sorted_count=len(sorted_stocks),
        visible_stock_count=len(stocks),
    )
    current_progress_stage = next((step for step in progress_steps if step["percent"] < 100), progress_steps[-1])
    progress_steps_html = render_progress_steps_html(progress_steps)
    pipeline_progress_json = progress_steps_json(progress_steps)

    progress_panel_class = "pipeline-progress is-compact" if compact_progress else "pipeline-progress"

    action_column_label = "移除" if tab == "watchlist" else "自選"
    table_header_html = f"<tr><th>{action_column_label}</th><th>狀態</th><th>代號</th><th>名稱</th><th>形勢判斷</th><th>收盤</th><th>目標價</th><th>目標價/現價</th><th>題材</th><th>操作方法</th><th>個股特性</th><th>行情階段</th><th>風險與觀察</th><th>備註</th><th class='theme-summary-cell'>題材摘要</th><th class='source-cell'>來源</th></tr>"
    stock_filter_button_text = "選擇自選股" if not stock_meta_stock_filter else f"已選 {len([x for x in stock_meta_stock_filter.replace('，', ',').replace('、', ',').replace(';', ',').replace('；', ',').split(',') for x in x.split() if x.strip()])} 筆條件"
    dashboard_render_items_json = json.dumps(rendered_stock_items, ensure_ascii=False).replace("</", "<\\/")
    table_header_html_json = json.dumps(table_header_html, ensure_ascii=False).replace("</", "<\\/")

    body = f"""<!doctype html><html lang='zh-Hant'><head><meta charset='utf-8'><title>TW Dashboard</title>
    <style>{DASHBOARD_CSS}</style></head><body>
    <div class='page-shell'>
    <header class='hero'>
      <div>
        <h1>多台股監控 Dashboard</h1>
        <p>把股池、技術線圖、篩選條件與自選管理整理到同一個清楚工作台。</p>
      </div>
      <div class='hero-badge'>Vercel 版・即時觀察</div>
    </header>
    <form id='cfgForm' class='control-panel'>
      <div class='filter-grid'>
        <fieldset class='pool-settings'>
          <legend>股池與分類</legend>
          <div class='field-stack'>
            <label class='form-field'>頁籤<select name='tab'><option value='watchlist' {'selected' if tab=='watchlist' else ''}>自選股監控</option><option value='category' {'selected' if tab=='category' else ''}>分類股池</option></select></label>
            <label class='form-field'>產業<select name='industry'>{industry_options}</select></label>
            <label class='form-field'>主題<select name='group_filter'>{group_options}</select></label>
            <label class='form-field'>次題材<select name='subgroup_filter'>{subgroup_options}</select></label>
          </div>
        </fieldset>
        <div class='primary-actions' data-title='主要操作'>
          <button type='submit' class='btn-primary'>更新儀表板</button>
          <button type='button' class='btn-soft' onclick='openBatchWatchlistDialog()'>批次加入自選</button>
          <span id='watchlistStatus' role='status' aria-live='polite'></span>
        </div>
        <fieldset class='kline-settings'>
          <legend>K 線與顯示</legend>
          <div class='field-stack'>
            <label class='form-field'>期間<select name='period'><option value='intraday' {'selected' if period=='intraday' else ''}>當日即時K</option><option value='1mo' {'selected' if period=='1mo' else ''}>1個月</option><option value='2mo' {'selected' if period=='2mo' else ''}>2個月</option><option value='3mo' {'selected' if period=='3mo' else ''}>3個月</option><option value='6mo' {'selected' if period=='6mo' else ''}>6個月</option><option value='1y' {'selected' if period=='1y' else ''}>1年</option><option value='5y' {'selected' if period=='5y' else ''}>5年</option></select></label>
            <label class='form-field'>週期<select name='interval'><option value='1m' {'selected' if interval=='1m' else ''}>1 分鐘</option><option value='5m' {'selected' if interval=='5m' else ''}>5 分鐘</option><option value='15m' {'selected' if interval=='15m' else ''}>15 分鐘</option><option value='1d' {'selected' if interval=='1d' else ''}>日線</option><option value='1wk' {'selected' if interval=='1wk' else ''}>週線</option></select></label>
            <label class='form-field'>每列檔數<select name='cards_per_row'>{''.join([f"<option value='{n}' {'selected' if cards_per_row==n else ''}>{n}</option>" for n in range(1, 16)])}</select></label>
            <label class='form-field'>圖塊排序<select name='card_sort'><option value='symbol' {'selected' if card_sort=='symbol' else ''}>個股代號</option><option value='signal_score' {'selected' if card_sort=='signal_score' else ''}>形勢分數</option><option value='close' {'selected' if card_sort=='close' else ''}>成交價</option><option value='volume' {'selected' if card_sort=='volume' else ''}>成交量</option><option value='change_pct' {'selected' if card_sort=='change_pct' else ''}>漲跌幅度</option><option value='target_ratio' {'selected' if card_sort=='target_ratio' else ''}>目標價/現價</option></select></label>
            <label class='form-field'>顯示量K線<select name='show_volume'><option value='1' {'selected' if show_volume else ''}>開啟</option><option value='0' {'selected' if not show_volume else ''}>關閉</option></select></label>
            <label class='form-field'>顯示價K線<select name='show_price'><option value='1' {'selected' if show_price else ''}>開啟</option><option value='0' {'selected' if not show_price else ''}>關閉</option></select></label>
            <label class='form-field'>總表摘要／來源<select id='tableThemeMetaToggle' name='table_theme_meta' aria-label='總表摘要與來源顯示開關'><option value='0' selected>關閉</option><option value='1'>開啟</option></select></label>
            <label class='form-field'>K線摘要／來源<select id='cardThemeMetaToggle' name='card_theme_meta' aria-label='K線摘要與來源顯示開關'><option value='0' selected>關閉</option><option value='1'>開啟</option></select></label>
          </div>
        </fieldset>
        <fieldset>
          <legend>篩選與分頁</legend>
          <div class='field-stack'>
            <label class='form-field'>形勢判斷篩選<select name='status_filter'>{status_options}</select></label>
            <label class='form-field'>檔數<input name='limit' value='{limit}' size='3'/></label>
            <label class='form-field'>頁碼<input name='page' value='{page}' size='3'/></label>
            <label class='form-field'>目標價<select name='show_target_price'><option value='0' {'selected' if not show_target_price else ''}>關閉（較快）</option><option value='1' {'selected' if show_target_price else ''}>開啟</option></select></label>
            <label class='form-field'>精簡進度<select name='compact_progress'><option value='1' {'selected' if compact_progress else ''}>開啟（省空間）</option><option value='0' {'selected' if not compact_progress else ''}>關閉（詳細）</option></select></label>
          </div>
        </fieldset>
        <fieldset>
          <legend>個人標籤篩選</legend>
          <div class='field-stack'>
            <label class='form-field'>操作方法<select id='stockMetaFilter-action' name='stock_meta_action'><option value='{html.escape(stock_meta_filters['action'])}' selected></option></select></label>
            <label class='form-field'>個股特性<select id='stockMetaFilter-trait' name='stock_meta_trait'><option value='{html.escape(stock_meta_filters['trait'])}' selected></option></select></label>
            <label class='form-field'>行情階段<select id='stockMetaFilter-stage' name='stock_meta_stage'><option value='{html.escape(stock_meta_filters['stage'])}' selected></option></select></label>
            <label class='form-field'>風險觀察<select id='stockMetaFilter-risk' name='stock_meta_risk'><option value='{html.escape(stock_meta_filters['risk'])}' selected></option></select></label>
            <label class='form-field'>備註關鍵字<input id='stockMetaFilter-note' name='stock_meta_note' value='{html.escape(stock_meta_note_filter, quote=True)}' placeholder='輸入備註文字篩選'></label>
            <label class='form-field'>股名／代號篩選
              <span class='stock-filter-picker'>
                <input type='hidden' id='stockMetaFilter-stock' name='stock_meta_stock' value='{html.escape(stock_meta_stock_filter, quote=True)}'>
                <button type='button' id='stockFilterButton' class='btn-soft' onclick='openStockFilterDialog()'>{html.escape(stock_filter_button_text)}</button>
              </span>
            </label>
          </div>
        </fieldset>
      </div>
      <input type='hidden' name='stock_meta_payload' id='stockMetaPayload' value='{html.escape(stock_meta_payload_raw, quote=True)}'>
      <div class='form-actions'>
        <div class='utility-actions' data-title='設定與備份'>
          <button type='button' onclick='saveLocal()'>儲存目前設定</button>
          <button type='button' onclick='loadLocal()'>讀取本機設定</button>
          <button type='button' onclick='exportBrowserMemory()'>匯出完整備份檔</button>
          <input type='file' id='memoryFile' accept='application/json' style='display:none' onchange='importBrowserMemory(event)'>
          <button type='button' onclick="document.getElementById('memoryFile').click()">匯入備份檔</button>
          <span class='preset-picker'><label>推薦設定檔</label><select id='serverConfigSelect'><option value=''>請選擇</option></select></span>
          <button type='button' onclick='loadServerConfig()'>讀取推薦設定</button>
        </div>
        <p class='form-help'>推薦設定由伺服器設定目錄提供；本機設定與完整備份檔會保存在瀏覽器，可跨裝置匯入還原。下方進度區只顯示目前頁面實際完成的階段與比例，不再用跳動提示假裝後端進度；可用「精簡進度」開關縮成單列顯示。</p>
        <div id='pipelineProgress' class='{progress_panel_class}' role='status' aria-live='polite'>
          <div class='pipeline-progress-header'>
            <div>
              <div class='pipeline-progress-title'>目前處理進度</div>
              <p id='pipelineProgressMessage' class='pipeline-progress-message'>已完成本次儀表板資料處理；重新送出後會在同一區塊顯示目前送出與等待狀態。</p>
            </div>
            <div id='pipelineProgressCurrent' class='pipeline-progress-current'>{html.escape(current_progress_stage['label'])}：{current_progress_stage['percent']}%</div>
          </div>
          <ol id='pipelineProgressList' class='pipeline-progress-list'>{progress_steps_html}</ol>
        </div>
      </div>
    <input type='hidden' name='custom_watchlist' id='customWatchlist' value='{html.escape(','.join(watchlist['symbol'].tolist()))}'>
    <div id='watchlistBatchModal' class='watchlist-batch-modal' role='dialog' aria-modal='true' aria-labelledby='watchlistBatchTitle'>
      <div class='watchlist-batch-dialog'>
        <div class='watchlist-batch-header'>
          <strong id='watchlistBatchTitle'>批次加入自選股</strong>
          <button type='button' onclick='closeBatchWatchlistDialog()' aria-label='關閉'>×</button>
        </div>
        <div class='watchlist-batch-body'>
          <div class='watchlist-batch-help'>先搜尋並勾選多檔股票，或在下方貼上多個代號（可用逗號、空白或換行分隔）；未按「批次加入」前，暫時關閉視窗也會保留已勾選內容。</div>
          <label for='watchKeyword'>關鍵字搜尋</label>
          <div class='watchlist-batch-row'>
            <input id='watchKeyword' placeholder='輸入名稱、代號、主題、次題材或摘要' style='flex:1;min-width:220px'>
            <button type='button' onclick='selectVisibleBatchStocks(true)'>全選搜尋結果</button>
            <button type='button' onclick='selectVisibleBatchStocks(false)'>清除搜尋勾選</button>
          </div>
          <div id='batchStockResults' class='watchlist-batch-list'></div>
          <label for='batchStockSymbols'>貼上代號</label>
          <textarea id='batchStockSymbols' class='watchlist-batch-paste' placeholder='例如：2330 2317
    2454, 2603'></textarea>
          <div id='batchWatchlistPreview' class='watchlist-batch-help'></div>
        </div>
        <div class='watchlist-batch-footer'>
          <button type='button' onclick='closeBatchWatchlistDialog()'>取消</button>
          <button type='button' onclick='addBatchWatchlistStocks()'>批次加入並更新</button>
        </div>
      </div>
    </div>
    <div id='stockFilterModal' class='watchlist-batch-modal' role='dialog' aria-modal='true' aria-labelledby='stockFilterTitle'>
      <div class='watchlist-batch-dialog'>
        <div class='watchlist-batch-header'>
          <strong id='stockFilterTitle'>股名／代號篩選</strong>
          <button type='button' onclick='closeStockFilterDialog()' aria-label='關閉'>×</button>
        </div>
        <div class='watchlist-batch-body'>
          <div class='watchlist-batch-help'>用和「批次加入自選」相同的搜尋勾選方式建立股名篩選；可勾選的來源僅限目前自選股清單。</div>
          <label for='stockFilterKeyword'>關鍵字搜尋</label>
          <div class='watchlist-batch-row'>
            <input id='stockFilterKeyword' placeholder='輸入名稱、代號、主題、次題材或摘要' style='flex:1;min-width:220px'>
            <button type='button' onclick='selectVisibleStockFilterStocks(true)'>全選搜尋結果</button>
            <button type='button' onclick='selectVisibleStockFilterStocks(false)'>清除搜尋勾選</button>
          </div>
          <div id='stockFilterResults' class='watchlist-batch-list'></div>
          <div id='stockFilterPreview' class='watchlist-batch-help'></div>
        </div>
        <div class='watchlist-batch-footer'>
          <button type='button' onclick='clearStockFilterSelection()'>清除股名篩選</button>
          <button type='button' onclick='closeStockFilterDialog()'>取消</button>
          <button type='button' onclick='applyStockFilterSelection()'>套用篩選並更新</button>
        </div>
      </div>
    </div>
    </form>
    <section class='section-card' aria-labelledby='overviewTitle'>
      <div class='section-header'>
        <h2 id='overviewTitle'>總覽</h2>
        <div id='pageNav' class='page-nav'>
          <button type='button' onclick='goToPage({max(1, page-1)})' {'disabled' if page <= 1 else ''}>上一頁</button>
          <button type='button' onclick='goToPage({min(total_pages, page+1)})' {'disabled' if page >= total_pages else ''}>下一頁</button>
        </div>
      </div>
      {limited_notice}
      {category_all_coverage_notice}
      <div id='summaryInfo' class='summary-strip'>
        <div class='summary-item'><span class='summary-label'>符合股數</span><span class='summary-value'>{total_stocks} 檔</span></div>
        <div class='summary-item'><span class='summary-label'>頁面進度</span><span class='summary-value'>{page} / {total_pages}</span></div>
        <div class='summary-item'><span class='summary-label'>每頁顯示</span><span class='summary-value'>{limit} 檔</span></div>
      </div>
      <div id='tableWrap' class='table-wrap'><table>{table_header_html}{''.join(rows) if rows else '<tr><td colspan="14">無符合條件資料</td></tr>'}</table></div>
    </section>
    <section class='section-card' aria-labelledby='chartsTitle'>
      <div class='section-header'><h2 id='chartsTitle'>多股趨勢圖</h2></div>
      <div id='cardsGrid' class='cards-grid' style='grid-template-columns:repeat({cards_per_row}, minmax(0,1fr))'>{''.join([f"<div class='card' data-symbol='{html.escape(cd['symbol'])}'>{cd['card_html']}</div>" for cd in cards_data])}</div>
    </section>
    <script>
    const defaultConfig = {json.dumps(save_payload, ensure_ascii=False)};
    const serverConfigPresets = {json.dumps(server_config_presets, ensure_ascii=False)};
    const autoRefreshMs = 60000;
    const isIntradayMode = defaultConfig.period === 'intraday';
    const WATCHLIST_STORAGE_KEY = 'tw_dashboard_watchlist';
    const NOTE_STORAGE_KEY = 'tw_dashboard_stock_notes';
    const STOCK_META_GROUPS = [
      {{ id: 'action', label: '操作方法', allLabel: '全部操作方法', noneLabel: '未設定操作方法', options: ['波段', '短線', '當沖', '長期', '定期定額', '分批布局', '分批加碼', '減碼鎖利', '續抱', '汰弱留強', '停利觀察', '停損觀察', '空手等待'] }},
      {{ id: 'trait', label: '個股特性', allLabel: '全部個股特性', noneLabel: '未設定個股特性', options: ['強勢股', '題材股', '轉機股', '成長股', '價值股', '景氣循環股', '防禦股', '高股息股', '權值股', '低基期股', '落後補漲股', '籌碼股', '法人認養股'] }},
      {{ id: 'stage', label: '行情階段', allLabel: '全部行情階段', noneLabel: '未設定行情階段', options: ['極早股', '初升段', '主升段前段', '主升段中段', '主升段後段', '高檔震盪', '魚尾', '拉回整理', '築底期', '整理末端', '突破觀察', '跌深反彈'] }},
      {{ id: 'risk', label: '風險與觀察', allLabel: '全部風險觀察', noneLabel: '未設定風險觀察', options: ['量縮觀察', '爆量觀察', '籌碼鬆動', '技術轉弱', '財報觀察', '法說觀察', '除權息觀察', '利多出盡疑慮', '追高風險', '流動性不足'] }},
    ];
    const STOCK_META_FIELDS = STOCK_META_GROUPS.map((group)=>group.id);
    const stockMetaFilterOptions = {json.dumps(stock_meta_filter_options, ensure_ascii=False)};
    const stockMetaFilterHasEmpty = {json.dumps(stock_meta_filter_has_empty, ensure_ascii=False)};
    const allStocks = {json.dumps(picker_stocks[STOCK_GROUP_COLUMNS].to_dict(orient='records'), ensure_ascii=False)};
    const stockFilterStocks = {json.dumps(stock_filter_stocks[STOCK_GROUP_COLUMNS].to_dict(orient='records'), ensure_ascii=False)};
    const pipelineProgressSteps = {pipeline_progress_json};
    // Immutable source of the full server-analyzed pool; status filtering always derives
    // a fresh visible list from this array so switching back to "全部" never needs
    // another yfinance download or analysis pass.
    const dashboardRenderItems = Object.freeze({dashboard_render_items_json});
    const dashboardTableHeaderHtml = {table_header_html_json};
    const dashboardPageSize = Number(defaultConfig.limit || 30);
    const dashboardHasAllClientCards = {json.dumps(client_render_all_cards)};
    let dashboardCurrentPage = Number(defaultConfig.page || 1);
    let dashboardCardsPerRow = Number(defaultConfig.cards_per_row || 3);
    let dashboardShowVolume = String(defaultConfig.show_volume ?? '1') === '1';
    let dashboardShowPrice = String(defaultConfig.show_price ?? '1') === '1';
    let dashboardShowTableThemeMeta = false;
    let dashboardShowCardThemeMeta = false;
    {DASHBOARD_JS}
    </script>
    </div>
    </body></html>"""

    return body
