from __future__ import annotations

import html
import json
import math
from urllib.parse import parse_qs

import pandas as pd

from api.charts import make_chart_html
from api.constants import (
    LLM_GROUP_FILE,
    LLM_GROUP_SHEET,
    STATUS_FILTERS,
    UP_COLOR,
    DOWN_COLOR,
    WATCHLIST_FILE,
)
from api.data_loader import load_llm_group_map, load_twse_industry_map, load_watchlist
from api.market_data import (
    _symbol_key,
    fetch_target_price,
    prefetch_price_data,
    resolve_price_params,
    trim_display_df,
)
from api.server_configs import load_server_config_presets
from api.stock_analysis import add_indicators, analyze_stock_signal


def app(environ, start_response):
    params = parse_qs(environ.get("QUERY_STRING", ""))
    tab = params.get("tab", ["watchlist"])[0]
    period = params.get("period", ["3mo"])[0]
    interval = params.get("interval", ["1d"])[0]
    limit = int(params.get("limit", ["30"])[0])
    limit = limit if limit > 0 else 30
    page = int(params.get("page", ["1"])[0])
    status_filter = params.get("status_filter", ["all"])[0]
    group_filter = params.get("group_filter", ["all"])[0]
    subgroup_filter = params.get("subgroup_filter", ["all"])[0]
    cards_per_row = int(params.get("cards_per_row", ["3"])[0])
    cards_per_row = cards_per_row if cards_per_row in list(range(1, 16)) else 3
    custom_watchlist_raw = params.get("custom_watchlist", [""])[0]
    show_volume = params.get("show_volume", ["1"])[0] == "1"
    show_target_price = params.get("show_target_price", ["0"])[0] == "1"
    card_sort = params.get("card_sort", ["symbol"])[0]
    fetch_period, fetch_interval, display_period = resolve_price_params(period, interval)

    base_watchlist = load_watchlist(WATCHLIST_FILE)
    llm_watchlist = load_llm_group_map(LLM_GROUP_FILE, LLM_GROUP_SHEET)
    base_watchlist = (
        pd.concat([llm_watchlist, base_watchlist], ignore_index=True)
        .drop_duplicates(subset=["symbol"], keep="last")
        .reset_index(drop=True)
    )
    industry_df = load_twse_industry_map()
    industries = industry_df[["industry", "industry_label"]].drop_duplicates().sort_values("industry")
    valid_industries = set(industries["industry"].astype(str)) if not industries.empty else set()
    industry = params.get("industry", ["all"])[0]
    if industry != "all" and industry not in valid_industries:
        industry = "all"

    watchlist_overrides = (
        base_watchlist[["symbol", "name", "group", "subgroup"]]
        .assign(symbol_key=lambda d: d["symbol"].map(_symbol_key))
        .drop_duplicates(subset=["symbol"], keep="last")
        .rename(columns={
            "name": "watch_name",
            "group": "watch_group",
            "subgroup": "watch_subgroup",
        })
    )

    all_stocks = pd.concat([
        base_watchlist[["symbol", "name", "group", "subgroup"]],
        industry_df[["symbol", "name", "group", "subgroup"]]
    ], ignore_index=True).drop_duplicates(subset=["symbol"])

    custom_symbols = [x.strip() for x in custom_watchlist_raw.split(",") if x.strip()]
    custom_df = all_stocks[all_stocks["symbol"].isin(custom_symbols)][["symbol", "name", "group", "subgroup"]]
    missing_symbols = [x for x in custom_symbols if x not in set(custom_df["symbol"]) ]
    if missing_symbols:
        custom_df = pd.concat([
            custom_df,
            pd.DataFrame([{"symbol": s, "name": s, "group": "自訂", "subgroup": ""} for s in missing_symbols])
        ], ignore_index=True)
    watchlist = custom_df if not custom_df.empty else base_watchlist

    if tab == "category":
        source_stocks = industry_df.copy()
        if industry != "all":
            source_stocks = source_stocks[source_stocks["industry"] == industry]
        source_stocks = source_stocks[["symbol", "name", "group", "subgroup"]]
    else:
        source_stocks = watchlist[["symbol", "name", "group", "subgroup"]].copy()
        if industry != "all":
            industry_symbol_keys = set(
                industry_df.loc[industry_df["industry"] == industry, "symbol"].map(_symbol_key)
            )
            source_stocks = source_stocks[source_stocks["symbol"].map(_symbol_key).isin(industry_symbol_keys)]

    source_stocks["symbol_key"] = source_stocks["symbol"].map(_symbol_key)
    source_stocks = source_stocks.merge(
        watchlist_overrides[["symbol_key", "watch_name", "watch_group", "watch_subgroup"]],
        on="symbol_key",
        how="left",
    )
    source_stocks["name"] = source_stocks["watch_name"].fillna(source_stocks["name"])
    source_stocks["group"] = source_stocks["watch_group"].fillna(source_stocks["group"])
    source_stocks["subgroup"] = source_stocks["watch_subgroup"].fillna(source_stocks["subgroup"])
    source_stocks = source_stocks[["symbol", "name", "group", "subgroup"]]

    picker_stocks = pd.concat(
        [all_stocks, watchlist[["symbol", "name", "group", "subgroup"]], source_stocks],
        ignore_index=True,
    ).drop_duplicates(subset=["symbol"], keep="first")

    valid_groups = sorted([g for g in source_stocks["group"].dropna().astype(str).str.strip().unique() if g])
    if group_filter != "all" and group_filter not in valid_groups:
        group_filter = "all"
    subgroup_source = source_stocks if group_filter == "all" else source_stocks[source_stocks["group"] == group_filter]
    valid_subgroups = sorted([g for g in subgroup_source["subgroup"].dropna().astype(str).str.strip().unique() if g])
    if subgroup_filter != "all" and subgroup_filter not in valid_subgroups:
        subgroup_filter = "all"

    stocks = source_stocks.copy()
    if group_filter != "all":
        stocks = stocks[stocks["group"] == group_filter]
    if subgroup_filter != "all":
        stocks = stocks[stocks["subgroup"] == subgroup_filter]
    total_stocks = len(stocks)
    total_pages = max(1, math.ceil(total_stocks / limit)) if total_stocks else 1
    page = min(max(page, 1), total_pages)
    start_idx = (page - 1) * limit
    end_idx = start_idx + limit
    stocks = stocks.iloc[start_idx:end_idx].copy()

    rows_data = []
    cards_data = []
    watchlist_symbol_keys = set(watchlist["symbol"].map(_symbol_key))
    price_data_map = prefetch_price_data(stocks, fetch_period, fetch_interval)
    signal_data_map = prefetch_price_data(stocks, "6mo", "1d") if period == "intraday" else {}

    for row in stocks.itertuples(index=False):
        df = price_data_map.get(row.symbol, pd.DataFrame()).copy()
        signal_df = signal_data_map.get(row.symbol, pd.DataFrame()).copy() if period == "intraday" else df.copy()
        if df.empty:
            bucket, status = "watch", "⚪ 抓不到資料"
            close_text = "-"
            signal = {"score": -999}
        else:
            df = add_indicators(df)
            df = trim_display_df(df, display_period)
            if signal_df.empty:
                signal = {"bucket": "watch", "message": "⚪ 抓不到判斷資料", "score": -999}
            else:
                signal_df = add_indicators(signal_df)
                signal = analyze_stock_signal(signal_df)
            bucket, status = signal["bucket"], signal["message"]
            close_text = f"{float(df.iloc[-1]['Close']):.2f}"

        if status_filter != "all" and bucket != status_filter:
            continue

        symbol_key = _symbol_key(row.symbol)
        symbol_js = json.dumps(row.symbol, ensure_ascii=False)
        if tab == "watchlist":
            action_btn = (
                "<button type='button' class='watchlist-action' "
                f"data-symbol='{html.escape(row.symbol, quote=True)}' "
                f"onclick='removeWatchlistStock({symbol_js}, {{ stayOnPage: true }})'>移出自選</button>"
            )
        elif symbol_key in watchlist_symbol_keys:
            action_btn = "<button type='button' class='watchlist-action is-added' disabled>已在自選</button>"
        else:
            action_btn = (
                "<button type='button' class='watchlist-action' "
                f"data-symbol='{html.escape(row.symbol, quote=True)}' "
                f"onclick='addWatchlistStock({symbol_js}, {{ stayOnPage: true }})'>加入自選</button>"
            )
        subgroup_text = row.subgroup if isinstance(row.subgroup, str) and row.subgroup else "-"
        note_editor = (
            f"<div class='note-editor' data-symbol='{html.escape(row.symbol)}'>"
            "<select class='note-preset-select' onchange=\"saveInlineNote(this)\"></select>"
            "</div>"
        )
        target_price_text = fetch_target_price(row.symbol) if show_target_price else "-"
        target_ratio_text = "-"
        if target_price_text != "-" and close_text != "-":
            try:
                target_price_value = float(target_price_text)
                close_value = float(close_text)
                if close_value != 0:
                    target_ratio_text = f"{(target_price_value / close_value) * 100:.1f}%"
            except (TypeError, ValueError):
                target_ratio_text = "-"
        name_jump_button = (
            "<button type='button' class='stock-jump' "
            f"onclick='scrollToStockCard({symbol_js})' "
            f"title='跳到 {html.escape(row.name, quote=True)} 的曲線圖'>"
            f"{html.escape(row.name)}"
            "</button>"
        )
        rows_data.append({"score": signal["score"] if not df.empty else -999, "row_html": f"<tr data-symbol='{html.escape(row.symbol)}'><td>{html.escape(status.split()[0])}</td><td>{html.escape(row.symbol)}</td><td>{name_jump_button}</td><td>{html.escape(row.group)}</td><td>{html.escape(subgroup_text)}</td><td>{html.escape(status)}</td><td>{close_text}</td><td>{target_price_text}</td><td>{target_ratio_text}</td><td class='note-cell'>{note_editor}</td><td>{action_btn}</td></tr>"})
        if not df.empty:
            show_ma = period != "intraday"
            intraday_ref_close = float(df.iloc[-1]["RefClose"]) if show_ma is False and "RefClose" in df.columns else None
            prev_close = float(df.iloc[-2]["Close"]) if len(df) >= 2 else float(df.iloc[-1]["Close"])
            now_close = float(df.iloc[-1]["Close"])
            reference_close = intraday_ref_close if period == "intraday" and intraday_ref_close else prev_close
            close_color = UP_COLOR if now_close >= reference_close else DOWN_COLOR
            if reference_close != 0:
                change_pct = ((now_close - reference_close) / reference_close) * 100
                change_text = f" ({change_pct:+.2f}%)"
            else:
                change_text = ""
            last_volume = float(df.iloc[-1]["Volume"]) if "Volume" in df.columns else 0.0
            signal_label = str(signal.get("label") or "").strip()
            signal_brief_text = signal_label[:8] + "…" if len(signal_label) > 8 else signal_label
            signal_brief = f"・{signal_brief_text}" if signal_brief_text else ""
            change_pct_value = ((now_close - reference_close) / reference_close) * 100 if reference_close else 0.0
            target_ratio_value = -1.0
            target_ratio_color = "#666"
            if target_ratio_text.endswith("%"):
                try:
                    target_ratio_value = float(target_ratio_text[:-1])
                    if target_ratio_value >= 110:
                        target_ratio_color = "#c62828"
                    elif target_ratio_value >= 100:
                        target_ratio_color = "#d84315"
                    elif target_ratio_value >= 90:
                        target_ratio_color = "#2e7d32"
                    else:
                        target_ratio_color = "#0b8f3a"
                except ValueError:
                    target_ratio_value = -1.0
                    target_ratio_color = "#666"
            cards_data.append({
                "symbol": row.symbol,
                "close": now_close,
                "volume": last_volume,
                "change_pct": change_pct_value,
                "target_ratio": target_ratio_value,
                "card_html": (
                    "<h3 style='display:flex;justify-content:space-between;align-items:center;gap:8px'>"
                    f"<span>{html.escape(row.name)} ({html.escape(row.symbol)}) 收盤 "
                    f"<span style='color:{close_color};font-weight:700'>{close_text}{change_text}</span>{html.escape(signal_brief)}</span>"
                    f"<span style='font-size:.82rem;color:{target_ratio_color};font-weight:700'>目標價/現價：{target_ratio_text}</span>"
                    "</h3>"
                    f"{make_chart_html(df, row.name, show_volume, show_ma, intraday_ref_close=intraday_ref_close)}"
                ),
            })

    rows_data.sort(key=lambda x: x["score"], reverse=True)
    rows = [x["row_html"] for x in rows_data]

    sort_options = {"symbol", "close", "volume", "change_pct", "target_ratio"}
    if card_sort not in sort_options:
        card_sort = "symbol"
    if card_sort == "symbol":
        cards_data.sort(key=lambda x: x["symbol"])
    else:
        cards_data.sort(key=lambda x: x[card_sort], reverse=True)
    cards = [x["card_html"] for x in cards_data]

    industry_options = (
        "<option value='all' {}>不限產業</option>".format("selected" if industry == "all" else "")
        + "".join([
            f"<option value='{html.escape(r.industry)}' {'selected' if r.industry == industry else ''}>{html.escape(r.industry_label)}</option>"
            for r in industries.itertuples(index=False)
        ])
    )
    status_options = "".join([
        f"<option value='{k}' {'selected' if k == status_filter else ''}>{v}</option>" for k, v in STATUS_FILTERS.items()
    ])
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
        "cards_per_row": cards_per_row,
        "custom_watchlist": ",".join(watchlist["symbol"].tolist()),
        "show_volume": "1" if show_volume else "0",
        "show_target_price": "1" if show_target_price else "0",
        "card_sort": card_sort,
        "page": page,
    }
    server_config_presets = load_server_config_presets()

    body = f"""<!doctype html><html lang='zh-Hant'><head><meta charset='utf-8'><title>TW Dashboard</title>
    <style>
      body{{font-family:Arial;margin:16px;line-height:1.35}}
      h1{{font-size:1.35rem;margin:0 0 10px}}
      h2{{font-size:1.1rem;margin:12px 0 8px}}
      form{{display:flex;flex-wrap:wrap;gap:6px 8px;align-items:center}}
      label{{font-size:.9rem;color:#333}}
      input,select,button{{font-size:.9rem;padding:4px 6px}}
      table{{border-collapse:collapse;width:100%;font-size:.88rem}}
      td,th{{border:1px solid #ddd;padding:5px;white-space:nowrap}}
      table th:nth-child(7), table td:nth-child(7), table th:nth-child(8), table td:nth-child(8), table th:nth-child(9), table td:nth-child(9){{text-align:right}}
      .table-wrap{{overflow-x:auto}}
      .card{{margin:8px 0;padding:8px;border:1px solid #ddd;border-radius:8px;transition:border-color .2s ease,box-shadow .2s ease,background .2s ease}}
      .card h3{{font-size:.95rem;margin:4px 0 6px}}
      .card.is-jump-target{{border-color:#1976d2;box-shadow:0 0 0 3px rgba(25,118,210,.16);background:#f5fbff}}
      .stock-jump{{border:0;background:none;color:#1565c0;text-decoration:underline;cursor:pointer;padding:0;font:inherit}}
      .stock-jump:hover,.stock-jump:focus{{color:#0d47a1;text-decoration-thickness:2px;outline:none}}
      .note-editor{{display:flex;gap:2px;align-items:center;white-space:nowrap}}
      .note-editor .note-preset-select{{width:150px;min-width:0;padding:2px 3px;text-align:left;text-align-last:left}}
      .watchlist-action{{min-width:72px;cursor:pointer}}
      .watchlist-action.is-added{{color:#2e7d32;background:#eef8ee;border:1px solid #9ccc9c;cursor:default}}
      #watchlistStatus{{min-height:1.2em;color:#2e7d32;font-size:.86rem}}
      .watchlist-batch-modal{{position:fixed;inset:0;background:rgba(0,0,0,.38);display:none;align-items:center;justify-content:center;z-index:9999;padding:16px}}
      .watchlist-batch-modal.is-open{{display:flex}}
      .watchlist-batch-dialog{{background:#fff;border-radius:10px;box-shadow:0 12px 32px rgba(0,0,0,.22);max-width:760px;width:min(760px, 100%);max-height:90vh;display:flex;flex-direction:column;overflow:hidden}}
      .watchlist-batch-header,.watchlist-batch-footer{{display:flex;align-items:center;justify-content:space-between;gap:8px;padding:12px 14px;border-bottom:1px solid #e5e5e5}}
      .watchlist-batch-footer{{border-top:1px solid #e5e5e5;border-bottom:0;justify-content:flex-end;flex-wrap:wrap}}
      .watchlist-batch-body{{padding:12px 14px;overflow:auto;display:grid;gap:10px}}
      .watchlist-batch-row{{display:flex;gap:8px;align-items:center;flex-wrap:wrap}}
      .watchlist-batch-list{{border:1px solid #ddd;border-radius:8px;max-height:260px;overflow:auto;background:#fafafa}}
      .watchlist-batch-item{{display:flex;gap:8px;align-items:center;padding:6px 8px;border-bottom:1px solid #eee;cursor:pointer}}
      .watchlist-batch-item:last-child{{border-bottom:0}}
      .watchlist-batch-item:hover{{background:#f2f7ff}}
      .watchlist-batch-item.is-added{{color:#777;background:#f5f5f5}}
      .watchlist-batch-item small{{color:#666}}
      .watchlist-batch-paste{{width:100%;min-height:70px;box-sizing:border-box}}
      .watchlist-batch-help{{color:#666;font-size:.84rem}}
      table th:nth-child(10), table td:nth-child(10){{width:160px;min-width:160px;max-width:160px}}
      table th:nth-child(11), table td:nth-child(11){{width:96px;min-width:96px;max-width:96px}}
      @media (max-width: 900px){{ body{{margin:10px}} }}
      @media (max-width: 720px){{
        form{{gap:4px 6px}}
        input,select,button{{font-size:.82rem;padding:3px 5px}}
        label{{font-size:.8rem}}
        table{{font-size:.8rem}}
      }}
    </style></head><body>
    <h1>多台股監控 Dashboard（Vercel 版）</h1>
    <form id='cfgForm'>
    <label>頁籤</label><select name='tab'><option value='watchlist' {'selected' if tab=='watchlist' else ''}>自選股監控</option><option value='category' {'selected' if tab=='category' else ''}>分類股池</option></select>
    <label>產業</label><select name='industry'>{industry_options}</select>
    <label>期間</label><select name='period'><option value='intraday' {'selected' if period=='intraday' else ''}>當日即時K</option><option value='1mo' {'selected' if period=='1mo' else ''}>1個月</option><option value='2mo' {'selected' if period=='2mo' else ''}>2個月</option><option value='3mo' {'selected' if period=='3mo' else ''}>3個月</option><option value='6mo' {'selected' if period=='6mo' else ''}>6個月</option><option value='1y' {'selected' if period=='1y' else ''}>1年</option><option value='5y' {'selected' if period=='5y' else ''}>5年</option></select>
    <label>週期</label><select name='interval'><option value='1m' {'selected' if interval=='1m' else ''}>1 分鐘</option><option value='5m' {'selected' if interval=='5m' else ''}>5 分鐘</option><option value='15m' {'selected' if interval=='15m' else ''}>15 分鐘</option><option value='1d' {'selected' if interval=='1d' else ''}>日線</option><option value='1wk' {'selected' if interval=='1wk' else ''}>週線</option></select>
    <label>檔數</label><input name='limit' value='{limit}' size='3'/>
    <label>頁碼</label><input name='page' value='{page}' size='3'/>
    <label>主題</label><select name='group_filter'>{group_options}</select>
    <label>次題材</label><select name='subgroup_filter'>{subgroup_options}</select>
    <label>判斷篩選</label><select name='status_filter'>{status_options}</select>
    <label>每列檔數</label><select name='cards_per_row'>{''.join([f"<option value='{n}' {'selected' if cards_per_row==n else ''}>{n}</option>" for n in range(1, 16)])}</select>
    <label>顯示量K線</label><select name='show_volume'><option value='1' {'selected' if show_volume else ''}>開啟</option><option value='0' {'selected' if not show_volume else ''}>關閉</option></select>
    <label>目標價</label><select name='show_target_price'><option value='0' {'selected' if not show_target_price else ''}>關閉（較快）</option><option value='1' {'selected' if show_target_price else ''}>開啟</option></select>
    <label>圖塊排序</label><select name='card_sort'><option value='symbol' {'selected' if card_sort=='symbol' else ''}>個股代號</option><option value='close' {'selected' if card_sort=='close' else ''}>成交價</option><option value='volume' {'selected' if card_sort=='volume' else ''}>成交量</option><option value='change_pct' {'selected' if card_sort=='change_pct' else ''}>漲跌幅度</option><option value='target_ratio' {'selected' if card_sort=='target_ratio' else ''}>目標價/現價</option></select>
    <label>註記篩選</label><select id='noteFilter'><option value='all'>全部註記</option></select>
    <button type='submit'>更新</button>
    <button type='button' onclick='saveLocal()'>儲存目前設定</button>
    <button type='button' onclick='loadLocal()'>讀取本機設定</button>
    <label>推薦設定檔</label><select id='serverConfigSelect'><option value=''>請選擇</option></select>
    <button type='button' onclick='loadServerConfig()'>讀取推薦設定</button>
    <button type='button' onclick='exportBrowserMemory()'>匯出完整備份檔</button>
    <input type='file' id='memoryFile' accept='application/json' style='display:none' onchange='importBrowserMemory(event)'>
    <button type='button' onclick="document.getElementById('memoryFile').click()">匯入備份檔</button>
    <small style='color:#666'>讀取推薦設定：由伺服器設定目錄提供；讀取本機設定：讀瀏覽器目前裝置已存內容；匯入備份檔：從 JSON 檔還原（可跨裝置）。</small>
    <hr>
    <button type='button' onclick='openBatchWatchlistDialog()'>批次加入自選</button>
    <span id='watchlistStatus' role='status' aria-live='polite'></span>
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
            <input id='watchKeyword' placeholder='輸入名稱、代號、主題或次題材' style='flex:1;min-width:220px'>
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
    </form>
    <h2>總覽</h2>
    <div id='summaryInfo' style='margin:4px 0 8px;color:#444;font-size:.9rem'>共 {total_stocks} 檔，現在第 {page}/{total_pages} 頁，每頁 {limit} 檔。</div>
    <div id='pageNav' style='display:flex;gap:6px;margin:0 0 8px'>
      <button type='button' onclick='goToPage({max(1, page-1)})' {'disabled' if page <= 1 else ''}>上一頁</button>
      <button type='button' onclick='goToPage({min(total_pages, page+1)})' {'disabled' if page >= total_pages else ''}>下一頁</button>
    </div>
    <div id='tableWrap' class='table-wrap'><table><tr><th>狀態</th><th>代號</th><th>名稱</th><th>主題分類</th><th>次題材</th><th>判斷</th><th>收盤</th><th>目標價</th><th>目標價/現價</th><th>註記</th><th>互動</th></tr>{''.join(rows) if rows else '<tr><td colspan="11">無符合條件資料</td></tr>'}</table></div>
    <h2>多股趨勢圖</h2><div id='cardsGrid' style='display:grid;grid-template-columns:repeat({cards_per_row}, minmax(0,1fr));gap:8px'>{''.join([f"<div class='card' data-symbol='{html.escape(cd['symbol'])}'>{cd['card_html']}</div>" for cd in cards_data])}</div>
    <script>
    const defaultConfig = {json.dumps(save_payload, ensure_ascii=False)};
    const serverConfigPresets = {json.dumps(server_config_presets, ensure_ascii=False)};
    const autoRefreshMs = 15000;
    const isIntradayMode = defaultConfig.period === 'intraday';
    const WATCHLIST_STORAGE_KEY = 'tw_dashboard_watchlist';
    const NOTE_STORAGE_KEY = 'tw_dashboard_stock_notes';
    const NOTE_PRESET_GROUPS = [
      {{ label: '操作方法', options: ['波段', '短線', '當沖', '長期', '定期定額', '分批布局', '分批加碼', '減碼鎖利', '續抱', '汰弱留強', '停利觀察', '停損觀察', '空手等待'] }},
      {{ label: '個股特性', options: ['強勢股', '題材股', '轉機股', '成長股', '價值股', '景氣循環股', '防禦股', '高股息股', '權值股', '低基期股', '落後補漲股', '籌碼股', '法人認養股'] }},
      {{ label: '行情階段', options: ['極早股', '初升段', '主升段前段', '主升段中段', '主升段後段', '高檔震盪', '魚尾', '拉回整理', '築底期', '整理末端', '突破觀察', '跌深反彈'] }},
      {{ label: '風險與觀察', options: ['量縮觀察', '爆量觀察', '籌碼鬆動', '技術轉弱', '財報觀察', '法說觀察', '除權息觀察', '利多出盡疑慮', '追高風險', '流動性不足'] }},
    ];
    const NOTE_PRESETS = NOTE_PRESET_GROUPS.flatMap((group)=>group.options);
    const CUSTOM_NOTE_PREFIX = '自訂：';
    function isTwTradingHours(){{
      const twNow = new Date(new Date().toLocaleString('en-US', {{ timeZone: 'Asia/Taipei' }}));
      const day = twNow.getDay();
      if(day === 0 || day === 6) return false;
      const minutes = twNow.getHours() * 60 + twNow.getMinutes();
      return minutes >= 9 * 60 && minutes <= 13 * 60 + 30;
    }}
    function serializeForm(){{
      const fd = new FormData(document.getElementById('cfgForm'));
      return Object.fromEntries(fd.entries());
    }}
    function applyConfig(cfg){{
      const form = document.getElementById('cfgForm');
      Object.entries(cfg).forEach(([k,v])=>{{ if(form.elements[k]) form.elements[k].value = v; }});
      form.submit();
    }}
    function submitConfig(overrides={{}}){{
      const form = document.getElementById('cfgForm');
      Object.entries(overrides).forEach(([k,v])=>{{ if(form.elements[k]) form.elements[k].value = v; }});
      form.submit();
    }}
    function goToPage(page){{
      submitConfig({{page: String(page)}});
    }}
    function scrollToStockCard(symbol){{
      const key = normalizeWatchlistSymbol(symbol);
      const card = Array.from(document.querySelectorAll('.card[data-symbol]')).find((el)=>normalizeWatchlistSymbol(el.dataset.symbol) === key);
      if(!card){{
        showWatchlistStatus(`找不到 ${{symbol}} 的曲線圖`);
        return;
      }}
      document.querySelectorAll('.card.is-jump-target').forEach((el)=>el.classList.remove('is-jump-target'));
      card.scrollIntoView({{behavior: 'smooth', block: 'start'}});
      card.classList.add('is-jump-target');
      window.clearTimeout(scrollToStockCard.timer);
      scrollToStockCard.timer = window.setTimeout(()=>card.classList.remove('is-jump-target'), 2200);
    }}
    function saveLocal(){{
      localStorage.setItem('tw_dashboard_config', JSON.stringify(serializeForm()));
      alert('設定已存到瀏覽器');
    }}
    function loadLocal(){{
      const raw = localStorage.getItem('tw_dashboard_config');
      if(!raw) return alert('找不到瀏覽器設定');
      try {{ applyConfig(JSON.parse(raw)); }} catch(e) {{ alert('設定格式錯誤'); }}
    }}
    function initServerConfigPicker(){{
      const el = document.getElementById('serverConfigSelect');
      el.innerHTML = "<option value=''>請選擇</option>" + serverConfigPresets.map((p, idx)=>`<option value="${{idx}}">${{p.label}} (${{p.id}})</option>`).join('');
    }}
    function loadServerConfig(){{
      const idx = document.getElementById('serverConfigSelect').value;
      if(idx === '') return alert('請先選擇推薦設定檔');
      const preset = serverConfigPresets[Number(idx)];
      if(!preset || typeof preset.config !== 'object') return alert('推薦設定檔格式錯誤');
      applyConfig(preset.config);
    }}
    function exportBrowserMemory(){{
      const configRaw = localStorage.getItem('tw_dashboard_config');
      const watchlistRaw = localStorage.getItem(WATCHLIST_STORAGE_KEY);
      const notesRaw = localStorage.getItem(NOTE_STORAGE_KEY);
      if(!configRaw && !watchlistRaw && !notesRaw) return alert('找不到可匯出的資料');
      const payload = {{
        exported_at: new Date().toISOString(),
        config: configRaw ? JSON.parse(configRaw) : null,
        watchlist: watchlistRaw ? JSON.parse(watchlistRaw) : [],
        notes: notesRaw ? JSON.parse(notesRaw) : {{}},
      }};
      const blob = new Blob([JSON.stringify(payload, null, 2)], {{type: 'application/json'}});
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = 'tw-dashboard-backup.json';
      a.click();
      URL.revokeObjectURL(a.href);
    }}
    function importBrowserMemory(evt){{
      const file = evt.target.files[0];
      if(!file) return;
      const reader = new FileReader();
      reader.onload = () => {{
        try {{
          const payload = JSON.parse(reader.result);
          const cfg = payload?.config ?? payload?.data ?? payload;
          if(typeof cfg !== 'object' || cfg === null) throw new Error('invalid');
          localStorage.setItem('tw_dashboard_config', JSON.stringify(cfg));
          if(Array.isArray(payload?.watchlist)) localStorage.setItem(WATCHLIST_STORAGE_KEY, JSON.stringify(payload.watchlist.map(String)));
          if(payload?.notes && typeof payload.notes === 'object') localStorage.setItem(NOTE_STORAGE_KEY, JSON.stringify(payload.notes));
          applyConfig(cfg);
        }} catch(e) {{
          alert('匯入失敗：備份格式錯誤');
        }}
      }};
      reader.readAsText(file);
      evt.target.value = '';
    }}

    const allStocks = {json.dumps(picker_stocks[['symbol', 'name', 'group', 'subgroup']].to_dict(orient='records'), ensure_ascii=False)};
    function getWatchlistSymbols(){{
      const raw = document.getElementById('customWatchlist').value.trim();
      return raw ? raw.split(',').map(x=>x.trim()).filter(Boolean) : [];
    }}
    function setWatchlistSymbols(symbols){{
      const unique = [];
      const seen = new Set();
      symbols.map(String).map(s => s.trim()).filter(Boolean).forEach((symbol)=>{{
        const key = normalizeWatchlistSymbol(symbol);
        if(seen.has(key)) return;
        seen.add(key);
        unique.push(symbol);
      }});
      document.getElementById('customWatchlist').value = unique.join(',');
    }}
    function syncWatchlistUrlParam(){{
      const url = new URL(window.location.href);
      const symbols = getWatchlistSymbols();
      if(symbols.length) url.searchParams.set('custom_watchlist', symbols.join(','));
      else url.searchParams.delete('custom_watchlist');
      window.history.replaceState(null, '', url.toString());
    }}
    function saveWatchlistToBrowser(silent=false){{
      const symbols = getWatchlistSymbols();
      localStorage.setItem(WATCHLIST_STORAGE_KEY, JSON.stringify(symbols));
      if(!silent) alert(`已儲存 ${{symbols.length}} 檔自選到瀏覽器`);
    }}
    function loadWatchlistFromBrowser(autoSubmit=true){{
      const raw = localStorage.getItem(WATCHLIST_STORAGE_KEY);
      if(!raw) return alert('找不到瀏覽器自選清單');
      try {{
        const symbols = JSON.parse(raw);
        if(!Array.isArray(symbols)) throw new Error('invalid');
        setWatchlistSymbols(symbols.map(String));
        if(autoSubmit) document.getElementById('cfgForm').submit();
      }} catch(e) {{
        alert('瀏覽器自選清單格式錯誤');
      }}
    }}
    function normalizeWatchlistSymbol(symbol){{
      return String(symbol || '').trim().toUpperCase().replace(/\.(TW|TWO)$/i, '');
    }}
    function markWatchlistButtonAdded(symbol){{
      const key = normalizeWatchlistSymbol(symbol);
      document.querySelectorAll('.watchlist-action[data-symbol]').forEach((btn)=>{{
        if(normalizeWatchlistSymbol(btn.dataset.symbol) !== key) return;
        btn.textContent = '已在自選';
        btn.classList.add('is-added');
        btn.disabled = true;
        btn.removeAttribute('onclick');
      }});
    }}
    function markWatchlistStockRemoved(symbol){{
      const key = normalizeWatchlistSymbol(symbol);
      document.querySelectorAll('tr[data-symbol], .card[data-symbol]').forEach((el)=>{{
        if(normalizeWatchlistSymbol(el.dataset.symbol) !== key) return;
        el.dataset.removed = '1';
        el.style.display = 'none';
      }});
      document.querySelectorAll('.watchlist-action[data-symbol]').forEach((btn)=>{{
        if(normalizeWatchlistSymbol(btn.dataset.symbol) !== key) return;
        btn.textContent = '已移出';
        btn.disabled = true;
      }});
    }}
    function showWatchlistStatus(message){{
      const el = document.getElementById('watchlistStatus');
      if(!el) return;
      el.textContent = message;
      window.clearTimeout(showWatchlistStatus.timer);
      showWatchlistStatus.timer = window.setTimeout(()=>{{ el.textContent = ''; }}, 2500);
    }}
    function addWatchlistStock(symbol, options={{}}){{
      const symbols = getWatchlistSymbols();
      const key = normalizeWatchlistSymbol(symbol);
      const exists = symbols.some(s => normalizeWatchlistSymbol(s) === key);
      if(!exists) symbols.push(symbol);
      setWatchlistSymbols(symbols);
      saveWatchlistToBrowser(true);
      syncWatchlistUrlParam();
      markWatchlistButtonAdded(symbol);
      if(options.stayOnPage){{
        showWatchlistStatus(exists ? `${{symbol}} 已在自選股` : `已加入 ${{symbol}} 到自選股`);
        return;
      }}
      if(options.openWatchlist){{
        submitConfig({{tab: 'watchlist', page: '1'}});
        return;
      }}
      submitConfig();
    }}
    function removeWatchlistStock(symbol, options={{}}){{
      const key = normalizeWatchlistSymbol(symbol);
      const symbols = getWatchlistSymbols().filter(s => normalizeWatchlistSymbol(s) !== key);
      setWatchlistSymbols(symbols);
      saveWatchlistToBrowser(true);
      syncWatchlistUrlParam();
      if(options.stayOnPage){{
        markWatchlistStockRemoved(symbol);
        showWatchlistStatus(`已將 ${{symbol}} 移出自選股，剩餘 ${{symbols.length}} 檔`);
        applyNoteFilter();
        return;
      }}
      submitConfig();
    }}
    const batchSelectedSymbols = new Map();
    function getStockLabel(stock){{
      return `${{stock.symbol}} - ${{stock.name || ''}} (${{stock.group || '未分類'}}${{stock.subgroup ? ' / ' + stock.subgroup : ''}})`;
    }}
    function syncVisibleBatchSelections(){{
      document.querySelectorAll('.batch-stock-check').forEach((el)=>{{
        const key = normalizeWatchlistSymbol(el.value);
        if(el.checked && !el.disabled) batchSelectedSymbols.set(key, el.value);
        else batchSelectedSymbols.delete(key);
      }});
    }}
    function getBatchCheckedSymbols(){{
      syncVisibleBatchSelections();
      return Array.from(batchSelectedSymbols.values());
    }}
    function parseBatchSymbolsText(){{
      const el = document.getElementById('batchStockSymbols');
      if(!el) return [];
      return el.value.split(/[\s,，、;；]+/).map(x => x.trim()).filter(Boolean);
    }}
    function updateBatchWatchlistPreview(){{
      const preview = document.getElementById('batchWatchlistPreview');
      if(!preview) return;
      const currentKeys = new Set(getWatchlistSymbols().map(normalizeWatchlistSymbol));
      const candidates = [...getBatchCheckedSymbols(), ...parseBatchSymbolsText()];
      const newKeys = [];
      const duplicateKeys = [];
      const seen = new Set();
      candidates.forEach((symbol)=>{{
        const key = normalizeWatchlistSymbol(symbol);
        if(!key || seen.has(key)) return;
        seen.add(key);
        if(currentKeys.has(key)) duplicateKeys.push(key);
        else newKeys.push(key);
      }});
      preview.textContent = `準備新增 ${{newKeys.length}} 檔；已在自選或重複 ${{duplicateKeys.length}} 檔。`;
    }}
    function renderBatchStockResults(keyword=''){{
      const container = document.getElementById('batchStockResults');
      if(!container) return;
      const kw = keyword.trim().toLowerCase();
      const currentKeys = new Set(getWatchlistSymbols().map(normalizeWatchlistSymbol));
      syncVisibleBatchSelections();
      const checkedKeys = new Set(batchSelectedSymbols.keys());
      const rows = allStocks.filter(r => !kw || [r.symbol, r.name, r.group, r.subgroup].filter(Boolean).some(v => String(v).toLowerCase().includes(kw))).slice(0, 200);
      if(!rows.length){{
        container.innerHTML = `<div class='watchlist-batch-item'>找不到符合「${{keyword}}」的股票</div>`;
        updateBatchWatchlistPreview();
        return;
      }}
      container.innerHTML = rows.map((r)=>{{
        const key = normalizeWatchlistSymbol(r.symbol);
        const added = currentKeys.has(key);
        const checked = checkedKeys.has(key) && !added;
        return `<label class='watchlist-batch-item${{added ? ' is-added' : ''}}'>
          <input class='batch-stock-check' type='checkbox' value="${{r.symbol}}" ${{checked ? 'checked' : ''}} ${{added ? 'disabled' : ''}} onchange='syncVisibleBatchSelections(); updateBatchWatchlistPreview()'>
          <span>${{getStockLabel(r)}} ${{added ? '<small>已在自選</small>' : ''}}</span>
        </label>`;
      }}).join('');
      updateBatchWatchlistPreview();
    }}
    function openBatchWatchlistDialog(){{
      const modal = document.getElementById('watchlistBatchModal');
      if(!modal) return;
      modal.classList.add('is-open');
      renderBatchStockResults(document.getElementById('watchKeyword')?.value || '');
      setTimeout(()=>document.getElementById('watchKeyword')?.focus(), 0);
    }}
    function closeBatchWatchlistDialog(){{
      syncVisibleBatchSelections();
      document.getElementById('watchlistBatchModal')?.classList.remove('is-open');
    }}
    function selectVisibleBatchStocks(checked){{
      document.querySelectorAll('.batch-stock-check:not(:disabled)').forEach((el)=>{{ el.checked = checked; }});
      syncVisibleBatchSelections();
      updateBatchWatchlistPreview();
    }}
    function addBatchWatchlistStocks(){{
      const before = getWatchlistSymbols();
      const beforeCount = before.length;
      setWatchlistSymbols([...before, ...getBatchCheckedSymbols(), ...parseBatchSymbolsText()]);
      const after = getWatchlistSymbols();
      const addedCount = after.length - beforeCount;
      if(addedCount <= 0){{
        setWatchlistSymbols(before);
        updateBatchWatchlistPreview();
        return alert('沒有新的股票可加入');
      }}
      saveWatchlistToBrowser(true);
      syncWatchlistUrlParam();
      batchSelectedSymbols.clear();
      closeBatchWatchlistDialog();
      showWatchlistStatus(`已批次加入 ${{addedCount}} 檔自選股，正在更新頁面`);
      submitConfig({{tab: 'watchlist', page: '1'}});
    }}
    function getStockNotes(){{
      try {{
        const raw = localStorage.getItem(NOTE_STORAGE_KEY) || '{{}}';
        const obj = JSON.parse(raw);
        return (obj && typeof obj === 'object') ? obj : {{}};
      }} catch(e) {{
        return {{}};
      }}
    }}
    function setStockNotes(notes){{
      localStorage.setItem(NOTE_STORAGE_KEY, JSON.stringify(notes));
    }}
    function appendOption(parent, value, label){{
      const option = document.createElement('option');
      option.value = value;
      option.textContent = label;
      parent.appendChild(option);
      return option;
    }}
    function populateNotePresetSelects(){{
      document.querySelectorAll('.note-preset-select').forEach((select)=>{{
        const currentValue = select.value;
        select.replaceChildren();
        appendOption(select, '', '清除註記');
        NOTE_PRESET_GROUPS.forEach((group)=>{{
          const optgroup = document.createElement('optgroup');
          optgroup.label = group.label;
          group.options.forEach((note)=>appendOption(optgroup, note, note));
          select.appendChild(optgroup);
        }});
        select.value = NOTE_PRESETS.includes(currentValue) ? currentValue : '';
      }});
    }}
    function refreshNoteFilterOptions(){{
      const filter = document.getElementById('noteFilter');
      const notes = getStockNotes();
      const uniq = [...new Set(Object.values(notes).map(v => String(v).trim()).filter(Boolean))].sort((a, b)=>a.localeCompare(b, 'zh-Hant'));
      filter.replaceChildren();
      appendOption(filter, 'all', '全部註記');
      appendOption(filter, 'none', '未註記');
      uniq.forEach((note)=>appendOption(filter, note, note));
    }}
    function applyNotesToTableAndCards(){{
      const notes = getStockNotes();
      document.querySelectorAll('tr[data-symbol]').forEach((tr)=>{{
        const symbol = tr.dataset.symbol;
        const note = (notes[symbol] || '').trim();
        tr.dataset.note = note || 'none';
        const presetSelect = tr.querySelector('.note-preset-select');
        if(presetSelect) presetSelect.value = NOTE_PRESETS.includes(note) ? note : '';
      }});
      applyNoteFilter();
    }}
    function applyNoteFilter(){{
      const selected = document.getElementById('noteFilter').value || 'all';
      const visibleSymbols = new Set();
      document.querySelectorAll('tr[data-symbol]').forEach((tr)=>{{
        const note = tr.dataset.note || 'none';
        const removed = tr.dataset.removed === '1';
        const visible = !removed && (selected === 'all' || note === selected || (selected === 'none' && note === 'none'));
        tr.style.display = visible ? '' : 'none';
        if(visible) visibleSymbols.add(tr.dataset.symbol);
      }});
      document.querySelectorAll('.card[data-symbol]').forEach((card)=>{{
        const removed = card.dataset.removed === '1';
        card.style.display = !removed && visibleSymbols.has(card.dataset.symbol) ? '' : 'none';
      }});
    }}
    function saveNoteBySymbol(symbol, note){{
      const notes = getStockNotes();
      if(note) notes[symbol] = note;
      else delete notes[symbol];
      setStockNotes(notes);
      refreshNoteFilterOptions();
      applyNotesToTableAndCards();
    }}
    function saveInlineNote(selectEl){{
      const editor = selectEl.closest('.note-editor');
      if(!editor) return;
      const symbol = editor.dataset.symbol;
      const preset = (selectEl.value || '').trim();
      saveNoteBySymbol(symbol, preset);
    }}
    document.getElementById('watchKeyword')?.addEventListener('input', (e)=>renderBatchStockResults(e.target.value));
    document.getElementById('batchStockSymbols')?.addEventListener('input', updateBatchWatchlistPreview);
    document.getElementById('watchlistBatchModal')?.addEventListener('click', (e)=>{{
      if(e.target.id === 'watchlistBatchModal') closeBatchWatchlistDialog();
    }});
    document.addEventListener('keydown', (e)=>{{
      if(e.key === 'Escape') closeBatchWatchlistDialog();
    }});
    initServerConfigPicker();
    renderBatchStockResults();
    populateNotePresetSelects();
    refreshNoteFilterOptions();
    applyNotesToTableAndCards();
    document.getElementById('noteFilter').addEventListener('change', applyNoteFilter);
    const hasSavedWatchlist = Boolean(localStorage.getItem(WATCHLIST_STORAGE_KEY));
    if(hasSavedWatchlist && !window.location.search.includes('custom_watchlist=')){{
      try {{
        const symbols = JSON.parse(localStorage.getItem(WATCHLIST_STORAGE_KEY) || '[]');
        if(Array.isArray(symbols) && symbols.length > 0) setWatchlistSymbols(symbols.map(String));
      }} catch(e) {{}}
    }}
    function autoSubmitConfig(event){{
      const overrides = {{}};
      if(event?.target?.name === 'tab') overrides.page = '1';
      submitConfig(overrides);
    }}
    ['tab','industry','period','interval','limit','status_filter','group_filter','subgroup_filter','cards_per_row','show_volume','show_target_price','card_sort'].forEach((name)=>{{
      const el = document.querySelector(`[name="${{name}}"]`);
      if(el) el.addEventListener('change', autoSubmitConfig);
    }});
    async function executeScripts(container){{
      const scripts = Array.from(container.querySelectorAll('script'));
      for(const oldScript of scripts){{
        const script = document.createElement('script');
        for(const attr of oldScript.attributes) script.setAttribute(attr.name, attr.value);
        if(oldScript.src){{
          if(window.Plotly && oldScript.src.includes('plotly')){{
            oldScript.remove();
            continue;
          }}
          await new Promise((resolve, reject)=>{{
            script.onload = resolve;
            script.onerror = reject;
            oldScript.replaceWith(script);
          }}).catch(()=>{{}});
        }} else {{
          script.text = oldScript.textContent;
          oldScript.replaceWith(script);
        }}
      }}
    }}
    async function refreshIntradayInPlace(){{
      if(refreshIntradayInPlace.busy || document.hidden || !isTwTradingHours()) return;
      refreshIntradayInPlace.busy = true;
      try {{
        const response = await fetch(window.location.href, {{ cache: 'no-store' }});
        if(!response.ok) throw new Error(`HTTP ${{response.status}}`);
        const html = await response.text();
        const doc = new DOMParser().parseFromString(html, 'text/html');
        const scrollX = window.scrollX;
        const scrollY = window.scrollY;
        ['summaryInfo', 'pageNav', 'tableWrap'].forEach((id)=>{{
          const current = document.getElementById(id);
          const fresh = doc.getElementById(id);
          if(current && fresh) current.replaceWith(fresh);
        }});
        const currentGrid = document.getElementById('cardsGrid');
        const freshGrid = doc.getElementById('cardsGrid');
        if(currentGrid && freshGrid){{
          currentGrid.replaceWith(freshGrid);
          await executeScripts(freshGrid);
        }}
        populateNotePresetSelects();
        applyNotesToTableAndCards();
        updateResponsiveGrid();
        window.scrollTo(scrollX, scrollY);
        requestAnimationFrame(()=>window.scrollTo(scrollX, scrollY));
      }} catch(e) {{
        console.warn('即時K線背景刷新失敗，改用下次排程重試', e);
      }} finally {{
        refreshIntradayInPlace.busy = false;
      }}
    }}
    if(isIntradayMode){{
      setInterval(refreshIntradayInPlace, autoRefreshMs);
    }}
    function updateResponsiveGrid(){{
      const grid = document.getElementById('cardsGrid');
      const w = window.innerWidth;
      if (w <= 640) grid.style.gridTemplateColumns = '1fr';
      else if (w <= 1024) grid.style.gridTemplateColumns = 'repeat(2, minmax(0,1fr))';
      else grid.style.gridTemplateColumns = `repeat(${{defaultConfig.cards_per_row || 3}}, minmax(0,1fr))`;
    }}
    window.addEventListener('resize', updateResponsiveGrid);
    updateResponsiveGrid();
    </script>
    </body></html>"""

    data = body.encode("utf-8")
    start_response("200 OK", [("Content-Type", "text/html; charset=utf-8"), ("Content-Length", str(len(data)))])
    return [data]

if __name__ == "__main__":
    import os

    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8000"))

    try:
        from waitress import serve

        print(f"Serving with waitress on http://{host}:{port}")
        serve(app, host=host, port=port)
    except ImportError:
        from wsgiref.simple_server import make_server

        print("waitress not installed, fallback to wsgiref (development only).")
        print(f"Serving on http://{host}:{port}")
        with make_server(host, port, app) as httpd:
            httpd.serve_forever()
