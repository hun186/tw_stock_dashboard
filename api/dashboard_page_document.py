from __future__ import annotations

import html

from api.dashboard_assets import DASHBOARD_CSS, DASHBOARD_JS
from api.dashboard_page_controls import render_dashboard_control_panel
from api.dashboard_page_context import safe_json_script
from api.data_loader import STOCK_GROUP_COLUMNS


def render_dashboard_document(
    card_sort,
    cards_data,
    cards_per_row,
    category_all_coverage_notice,
    client_render_all_cards,
    compact_progress,
    current_progress_stage,
    dashboard_render_items_json,
    group_options,
    industry_options,
    interval,
    limit,
    limited_notice,
    page,
    period,
    picker_stocks,
    pipeline_progress_json,
    progress_panel_class,
    progress_steps_html,
    rows,
    save_payload,
    server_config_presets,
    show_price,
    show_target_price,
    show_volume,
    status_options,
    stock_filter_button_label,
    stock_filter_stocks,
    stock_meta_filter_has_empty,
    stock_meta_filter_options,
    stock_meta_filters,
    stock_meta_note_filter,
    stock_meta_payload_raw,
    stock_meta_stock_filter,
    theme_summary_keyword,
    theme_signal_bucket_options,
    theme_signal_code_options,
    theme_volume_ratio_options,
    subgroup_options,
    tab,
    table_header_html,
    table_header_html_json,
    theme_rotation_html,
    total_pages,
    total_stocks,
    watchlist,
) -> str:
    control_panel_html = render_dashboard_control_panel(
        card_sort=card_sort,
        cards_per_row=cards_per_row,
        compact_progress=compact_progress,
        current_progress_stage=current_progress_stage,
        group_options=group_options,
        industry_options=industry_options,
        interval=interval,
        limit=limit,
        page=page,
        period=period,
        progress_panel_class=progress_panel_class,
        progress_steps_html=progress_steps_html,
        show_price=show_price,
        show_target_price=show_target_price,
        show_volume=show_volume,
        status_options=status_options,
        stock_filter_button_label=stock_filter_button_label,
        stock_meta_filters=stock_meta_filters,
        stock_meta_note_filter=stock_meta_note_filter,
        stock_meta_payload_raw=stock_meta_payload_raw,
        stock_meta_stock_filter=stock_meta_stock_filter,
        theme_summary_keyword=theme_summary_keyword,
        theme_signal_bucket_options=theme_signal_bucket_options,
        theme_signal_code_options=theme_signal_code_options,
        theme_volume_ratio_options=theme_volume_ratio_options,
        subgroup_options=subgroup_options,
        tab=tab,
        watchlist=watchlist,
    )

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
    {control_panel_html}
    {theme_rotation_html}
    <section class='section-card collapsible-section' data-collapsible-section='overview' aria-labelledby='overviewTitle'>
      <div class='section-header'>
        <button type='button' class='section-toggle' data-collapse-target='overviewBody' aria-expanded='true' aria-controls='overviewBody'>
          <span class='section-toggle-icon' aria-hidden='true'>▾</span><span id='overviewTitle' class='section-toggle-title'>總覽</span>
        </button>
        <div id='pageNav' class='page-nav'>
          <button type='button' onclick='goToPage({max(1, page-1)})' {'disabled' if page <= 1 else ''}>上一頁</button>
          <button type='button' onclick='goToPage({min(total_pages, page+1)})' {'disabled' if page >= total_pages else ''}>下一頁</button>
        </div>
      </div>
      <div id='overviewBody' class='collapsible-content'>
      {limited_notice}
      {category_all_coverage_notice}
      <div id='summaryInfo' class='summary-strip'>
        <div class='summary-item'><span class='summary-label'>符合股數</span><span class='summary-value'>{total_stocks} 檔</span></div>
        <div class='summary-item'><span class='summary-label'>頁面進度</span><span class='summary-value'>{page} / {total_pages}</span></div>
        <div class='summary-item'><span class='summary-label'>每頁顯示</span><span class='summary-value'>{limit} 檔</span></div>
      </div>
      <div id='tableWrap' class='table-wrap'><table>{table_header_html}{''.join(rows) if rows else '<tr><td colspan="14">無符合條件資料</td></tr>'}</table></div>
      </div>
    </section>
    <section class='section-card collapsible-section' data-collapsible-section='charts' aria-labelledby='chartsTitle'>
      <div class='section-header'>
        <button type='button' class='section-toggle' data-collapse-target='chartsBody' aria-expanded='true' aria-controls='chartsBody'>
          <span class='section-toggle-icon' aria-hidden='true'>▾</span><span id='chartsTitle' class='section-toggle-title'>多股趨勢圖</span>
        </button>
      </div>
      <div id='chartsBody' class='collapsible-content'>
      <div id='cardsGrid' class='cards-grid' style='grid-template-columns:repeat({cards_per_row}, minmax(0,1fr))'>{''.join([f"<div class='card' data-symbol='{html.escape(cd['symbol'])}'>{cd['card_html']}</div>" for cd in cards_data])}</div>
      </div>
    </section>
    <script>
    const defaultConfig = {safe_json_script(save_payload)};
    const serverConfigPresets = {safe_json_script(server_config_presets)};
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
    const stockMetaFilterOptions = {safe_json_script(stock_meta_filter_options)};
    const stockMetaFilterHasEmpty = {safe_json_script(stock_meta_filter_has_empty)};
    const allStocks = {safe_json_script(picker_stocks[STOCK_GROUP_COLUMNS].to_dict(orient='records'))};
    const stockFilterStocks = {safe_json_script(stock_filter_stocks[STOCK_GROUP_COLUMNS].to_dict(orient='records'))};
    const pipelineProgressSteps = {pipeline_progress_json};
    // Immutable source of the full server-analyzed pool; status filtering always derives
    // a fresh visible list from this array so switching back to "全部" never needs
    // another yfinance download or analysis pass.
    const dashboardRenderItems = Object.freeze({dashboard_render_items_json});
    const dashboardTableHeaderHtml = {table_header_html_json};
    const dashboardPageSize = Number(defaultConfig.limit || 30);
    const dashboardHasAllClientCards = {safe_json_script(client_render_all_cards)};
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
