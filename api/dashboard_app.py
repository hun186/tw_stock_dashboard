from __future__ import annotations

import html
import json
import math
import os
import time
from urllib.parse import parse_qs

import pandas as pd

from api.charts import make_chart_html
from api.constants import (
    GEMINI_AGENT_GROUP_FILE,
    LLM_GROUP_FILE,
    LLM_GROUP_SHEET,
    STATUS_FILTERS,
    UP_COLOR,
    DOWN_COLOR,
    WATCHLIST_FILE,
)
from api.data_loader import (
    STOCK_GROUP_COLUMNS,
    load_gemini_agent_group_map,
    load_llm_group_map,
    load_twse_industry_map,
    load_watchlist,
)
from api.market_data import (
    _symbol_key,
    fetch_target_price,
    get_price_cache_ttl_seconds,
    prefetch_price_data,
    resolve_price_params,
    trim_display_df,
)
from api.server_configs import load_server_config_presets
from api.stock_analysis import add_indicators, analyze_stock_signal


def _ensure_stock_group_columns(df: pd.DataFrame) -> pd.DataFrame:
    normalized = df.copy()
    for col in STOCK_GROUP_COLUMNS:
        if col not in normalized.columns:
            normalized[col] = ""
        normalized[col] = normalized[col].fillna("").astype(str).str.strip()
    return normalized


def _stock_group_frame(df: pd.DataFrame) -> pd.DataFrame:
    return _ensure_stock_group_columns(df)[STOCK_GROUP_COLUMNS].copy()


def _merge_stock_group_sources(*sources: pd.DataFrame) -> pd.DataFrame:
    frames = [_stock_group_frame(source) for source in sources if source is not None]
    if not frames:
        return pd.DataFrame(columns=STOCK_GROUP_COLUMNS)
    combined = pd.concat(frames, ignore_index=True)
    combined = combined[combined["symbol"] != ""].copy()
    if combined.empty:
        return pd.DataFrame(columns=STOCK_GROUP_COLUMNS)

    # Sources are passed from lowest to highest priority.  For every column, keep
    # the highest-priority non-empty value so a legacy watchlist without
    # summary/reference_url does not erase Gemini metadata for the same symbol.
    merged_rows = []
    for symbol, group in combined.groupby("symbol", sort=False):
        row = {"symbol": symbol}
        for col in [c for c in STOCK_GROUP_COLUMNS if c != "symbol"]:
            values = group[col].tolist()
            row[col] = next((value for value in reversed(values) if value), "")
        merged_rows.append(row)
    return pd.DataFrame(merged_rows, columns=STOCK_GROUP_COLUMNS)


def _theme_summary_text(value: object) -> str:
    text = str(value or "").strip()
    return text if text else "-"


def _theme_reference_html(value: object) -> str:
    url = str(value or "").strip()
    if not url:
        return "-"
    escaped = html.escape(url, quote=True)
    label = "來源連結" if url.lower().startswith(("http://", "https://")) else url
    if url.lower().startswith(("http://", "https://")):
        return f"<a class='source-link' href='{escaped}' target='_blank' rel='noopener noreferrer'>{html.escape(label)}</a>"
    return html.escape(label)


STOCK_ANALYSIS_CACHE: dict[tuple[str, str, str, str, str, bool], tuple[float, dict]] = {}
DEFAULT_LIVE_FETCH_THRESHOLD = 80
SINGLE_CATEGORY_LIVE_FETCH_BUFFER = 20


def _positive_int_param(params, name: str, default: int, *, max_value: int | None = None) -> int:
    try:
        value = int(params.get(name, [str(default)])[0])
    except (TypeError, ValueError):
        value = default
    if value <= 0:
        value = default
    if max_value is not None:
        value = min(value, max_value)
    return value


def _analysis_cache_ttl_seconds(fetch_interval: str) -> int:
    return max(get_price_cache_ttl_seconds(fetch_interval), 300)


def _stock_code_sort_value(symbol: object) -> tuple[str, str]:
    normalized = str(symbol or "").strip().upper()
    code = normalized.split(".", 1)[0]
    return code, normalized


def _sort_stocks_by_symbol(stocks: pd.DataFrame) -> pd.DataFrame:
    if stocks.empty or "symbol" not in stocks.columns:
        return stocks.copy()
    sorted_stocks = stocks.copy()
    sort_values = sorted_stocks["symbol"].map(_stock_code_sort_value)
    sorted_stocks["_stock_code_sort"] = sort_values.map(lambda value: value[0])
    sorted_stocks["_stock_symbol_sort"] = sort_values.map(lambda value: value[1])
    return (
        sorted_stocks.sort_values(["_stock_code_sort", "_stock_symbol_sort"], kind="stable")
        .drop(columns=["_stock_code_sort", "_stock_symbol_sort"])
        .reset_index(drop=True)
    )


def _resolve_live_fetch_controls(
    *,
    is_serverless_runtime: bool,
    stock_count: int,
    is_custom_watchlist: bool,
    tab: str,
    industry: str,
) -> tuple[bool, int]:
    is_single_industry_category = tab == "category" and industry != "all"
    if is_single_industry_category:
        max_live_symbols = max(DEFAULT_LIVE_FETCH_THRESHOLD, stock_count + SINGLE_CATEGORY_LIVE_FETCH_BUFFER)
    elif is_custom_watchlist or not is_serverless_runtime:
        max_live_symbols = max(DEFAULT_LIVE_FETCH_THRESHOLD, stock_count)
    else:
        max_live_symbols = DEFAULT_LIVE_FETCH_THRESHOLD

    allow_live_fetch = (
        (not is_serverless_runtime)
        or stock_count <= DEFAULT_LIVE_FETCH_THRESHOLD
        or is_custom_watchlist
        or is_single_industry_category
    )
    return allow_live_fetch, max_live_symbols


def _build_stock_analysis(
    symbol: str,
    period: str,
    fetch_period: str,
    fetch_interval: str,
    display_period: str,
    price_df: pd.DataFrame,
    signal_df: pd.DataFrame,
    needs_target_price: bool,
) -> dict:
    cache_key = (symbol, period, fetch_period, fetch_interval, display_period, needs_target_price)
    cached = STOCK_ANALYSIS_CACHE.get(cache_key)
    now = time.time()
    if cached and now - cached[0] < _analysis_cache_ttl_seconds(fetch_interval):
        payload = cached[1].copy()
        payload["df"] = cached[1]["df"].copy()
        return payload

    df = price_df.copy()
    raw_signal_df = signal_df.copy() if period == "intraday" else df.copy()
    sort_metrics = {
        "symbol": symbol,
        "close": -1.0,
        "volume": -1.0,
        "change_pct": -999.0,
        "target_ratio": -1.0,
        "signal_score": -999.0,
    }
    target_price_text = "-"
    target_ratio_text = "-"
    if df.empty:
        bucket, status = "watch", "⚪ 抓不到資料"
        close_text = "-"
        signal = {"bucket": bucket, "message": status, "score": -999}
    else:
        df = add_indicators(df)
        df = trim_display_df(df, display_period)
        if raw_signal_df.empty:
            signal = {"bucket": "watch", "message": "⚪ 抓不到形勢判斷資料", "score": -999}
        else:
            raw_signal_df = add_indicators(raw_signal_df)
            signal = analyze_stock_signal(raw_signal_df)
        bucket, status = signal["bucket"], signal["message"]
        close_value = float(df.iloc[-1]["Close"])
        close_text = f"{close_value:.2f}"
        sort_metrics["close"] = close_value
        sort_metrics["volume"] = float(df.iloc[-1]["Volume"]) if "Volume" in df.columns else 0.0
        sort_metrics["signal_score"] = float(signal.get("score", -999))
        intraday_ref_close = float(df.iloc[-1]["RefClose"]) if period == "intraday" and "RefClose" in df.columns else None
        prev_close = float(df.iloc[-2]["Close"]) if len(df) >= 2 else close_value
        reference_close = intraday_ref_close if intraday_ref_close else prev_close
        sort_metrics["change_pct"] = ((close_value - reference_close) / reference_close) * 100 if reference_close else 0.0
        if needs_target_price:
            target_price_text = fetch_target_price(symbol)
            try:
                target_price_value = float(target_price_text)
                if close_value != 0:
                    sort_metrics["target_ratio"] = (target_price_value / close_value) * 100
                    target_ratio_text = f"{sort_metrics['target_ratio']:.1f}%"
            except (TypeError, ValueError):
                target_price_text = "-"
                target_ratio_text = "-"

    payload = {
        "df": df,
        "signal": signal,
        "bucket": signal["bucket"],
        "status": signal["message"],
        "close_text": close_text,
        "sort_metrics": sort_metrics,
        "target_price_text": target_price_text,
        "target_ratio_text": target_ratio_text,
    }
    STOCK_ANALYSIS_CACHE[cache_key] = (now, {**payload, "df": payload["df"].copy()})
    return payload


def app(environ, start_response):
    params = parse_qs(environ.get("QUERY_STRING", ""))
    tab = params.get("tab", ["watchlist"])[0]
    period = params.get("period", ["3mo"])[0]
    interval = params.get("interval", ["1d"])[0]
    limit = _positive_int_param(params, "limit", 30, max_value=120)
    page = _positive_int_param(params, "page", 1)
    status_filter = params.get("status_filter", ["all"])[0]
    group_filter = params.get("group_filter", ["all"])[0]
    subgroup_filter = params.get("subgroup_filter", ["all"])[0]
    stock_meta_filters = {
        field: params.get(f"stock_meta_{field}", ["all"])[0]
        for field in ("action", "trait", "stage", "risk")
    }
    stock_meta_note_filter = params.get("stock_meta_note", [""])[0].strip()
    stock_meta_stock_filter = params.get("stock_meta_stock", [""])[0].strip()
    stock_meta_payload_raw = params.get("stock_meta_payload", [""])[0]
    cards_per_row = _positive_int_param(params, "cards_per_row", 3, max_value=15)
    custom_watchlist_raw = params.get("custom_watchlist", [""])[0]
    show_volume = params.get("show_volume", ["1"])[0] == "1"
    show_price = params.get("show_price", ["1"])[0] == "1"
    show_target_price = params.get("show_target_price", ["0"])[0] == "1"
    card_sort = params.get("card_sort", ["signal_score"])[0]
    compact_progress = params.get("compact_progress", ["1"])[0] == "1"
    sort_options = {"symbol", "close", "volume", "change_pct", "target_ratio", "signal_score"}
    if card_sort not in sort_options:
        card_sort = "signal_score"

    def normalize_stock_meta_entry(entry):
        meta = {field: "" for field in ("action", "trait", "stage", "risk")}
        meta["note"] = ""
        if isinstance(entry, str):
            meta["note"] = entry.strip()
        elif isinstance(entry, dict):
            for field in meta:
                meta[field] = str(entry.get(field) or "").strip()
            if not meta["note"]:
                meta["note"] = str(entry.get("memo") or "").strip()
        return meta

    try:
        stock_meta_payload = json.loads(stock_meta_payload_raw) if stock_meta_payload_raw else {}
        if not isinstance(stock_meta_payload, dict):
            stock_meta_payload = {}
    except json.JSONDecodeError:
        stock_meta_payload = {}
    stock_meta_filters = {
        field: value if value and value != "all" else "all"
        for field, value in stock_meta_filters.items()
    }
    has_stock_meta_filter = (
        any(value != "all" for value in stock_meta_filters.values())
        or bool(stock_meta_note_filter)
        or bool(stock_meta_stock_filter)
    )

    fetch_period, fetch_interval, display_period = resolve_price_params(period, interval)

    file_watchlist = _stock_group_frame(load_watchlist(WATCHLIST_FILE))
    gemini_agent_watchlist = _stock_group_frame(load_gemini_agent_group_map(GEMINI_AGENT_GROUP_FILE))
    llm_watchlist = _stock_group_frame(load_llm_group_map(LLM_GROUP_FILE, LLM_GROUP_SHEET))
    stock_metadata = _merge_stock_group_sources(llm_watchlist, gemini_agent_watchlist, file_watchlist).reset_index(drop=True)
    base_watchlist = file_watchlist.reset_index(drop=True)
    industry_df = load_twse_industry_map()
    industry_df = _ensure_stock_group_columns(industry_df)
    industries = industry_df[["industry", "industry_label"]].drop_duplicates().sort_values("industry")
    valid_industries = set(industries["industry"].astype(str)) if not industries.empty else set()
    industry = params.get("industry", ["all"])[0]
    if industry != "all" and industry not in valid_industries:
        industry = "all"
    watchlist_overrides = (
        stock_metadata[STOCK_GROUP_COLUMNS]
        .assign(symbol_key=lambda d: d["symbol"].map(_symbol_key))
        .drop_duplicates(subset=["symbol"], keep="last")
        .rename(columns={col: f"watch_{col}" for col in STOCK_GROUP_COLUMNS if col != "symbol"})
    )

    all_stocks = _merge_stock_group_sources(
        industry_df[STOCK_GROUP_COLUMNS],
        stock_metadata[STOCK_GROUP_COLUMNS],
    )

    custom_symbols = [x.strip() for x in custom_watchlist_raw.split(",") if x.strip()]
    custom_df = all_stocks[all_stocks["symbol"].isin(custom_symbols)][STOCK_GROUP_COLUMNS]
    missing_symbols = [x for x in custom_symbols if x not in set(custom_df["symbol"]) ]
    if missing_symbols:
        custom_df = pd.concat([
            custom_df,
            pd.DataFrame([{"symbol": s, "name": s, "group": "自訂", "subgroup": "", "summary": "", "reference_url": ""} for s in missing_symbols])
        ], ignore_index=True)
    watchlist = custom_df if not custom_df.empty else base_watchlist

    if tab == "category":
        source_stocks = industry_df.copy()
        if industry != "all":
            source_stocks = source_stocks[source_stocks["industry"] == industry]
        source_stocks = source_stocks[STOCK_GROUP_COLUMNS]
    else:
        source_stocks = watchlist[STOCK_GROUP_COLUMNS].copy()
        if industry != "all":
            industry_symbol_keys = set(
                industry_df.loc[industry_df["industry"] == industry, "symbol"].map(_symbol_key)
            )
            source_stocks = source_stocks[source_stocks["symbol"].map(_symbol_key).isin(industry_symbol_keys)]

    source_stocks["symbol_key"] = source_stocks["symbol"].map(_symbol_key)
    source_stocks = source_stocks.merge(
        watchlist_overrides[["symbol_key", "watch_name", "watch_group", "watch_subgroup", "watch_summary", "watch_reference_url"]],
        on="symbol_key",
        how="left",
    )
    for col in ["name", "group", "subgroup", "summary", "reference_url"]:
        source_stocks[col] = source_stocks[f"watch_{col}"].where(
            source_stocks[f"watch_{col}"].fillna("").astype(str).str.strip().ne(""),
            source_stocks[col],
        )
    source_stocks = source_stocks[STOCK_GROUP_COLUMNS]

    picker_stocks = _sort_stocks_by_symbol(
        _merge_stock_group_sources(all_stocks, watchlist[STOCK_GROUP_COLUMNS], source_stocks)
    )
    stock_filter_stocks = _sort_stocks_by_symbol(
        _merge_stock_group_sources(watchlist[STOCK_GROUP_COLUMNS])
    )

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

    stock_meta_filter_values = {field: set() for field in ("action", "trait", "stage", "risk")}
    for symbol in stocks["symbol"].astype(str):
        meta = normalize_stock_meta_entry(stock_meta_payload.get(symbol, {}))
        for field in stock_meta_filter_values:
            stock_meta_filter_values[field].add(meta[field] or "none")
    for field, selected in stock_meta_filters.items():
        if selected != "all" and selected not in stock_meta_filter_values[field]:
            stock_meta_filters[field] = "all"
    has_stock_meta_filter = (
        any(value != "all" for value in stock_meta_filters.values())
        or bool(stock_meta_note_filter)
        or bool(stock_meta_stock_filter)
    )

    if has_stock_meta_filter:
        note_filter_lower = stock_meta_note_filter.lower()
        stock_filter_tokens = [
            token.strip().lower()
            for token in stock_meta_stock_filter.replace("，", ",").replace("、", ",").replace(";", ",").replace("；", ",").split(",")
            for token in token.split()
            if token.strip()
        ]

        def stock_matches_meta_filters(row):
            symbol = str(row["symbol"])
            name = str(row["name"] or "")
            summary = str(row.get("summary", "") or "")
            meta = normalize_stock_meta_entry(stock_meta_payload.get(symbol, {}))
            tags_match = all(
                selected == "all"
                or (selected == "none" and not meta[field])
                or meta[field] == selected
                for field, selected in stock_meta_filters.items()
            )
            note_matches = not note_filter_lower or note_filter_lower in meta["note"].lower()
            symbol_lower = symbol.lower()
            symbol_key_lower = _symbol_key(symbol).lower()
            name_lower = name.lower()
            summary_lower = summary.lower()
            stock_matches = not stock_filter_tokens or any(
                token in symbol_lower or token in symbol_key_lower or token in name_lower or token in summary_lower
                for token in stock_filter_tokens
            )
            return tags_match and note_matches and stock_matches

        stocks = stocks[stocks.apply(stock_matches_meta_filters, axis=1)]

    is_serverless_runtime = os.environ.get("VERCEL") == "1" or bool(os.environ.get("AWS_LAMBDA_FUNCTION_NAME"))
    max_serverless_analysis_stocks = 240
    candidate_count = len(stocks)
    is_limited_analysis = is_serverless_runtime and candidate_count > max_serverless_analysis_stocks
    if is_limited_analysis:
        # Keep broad dashboard requests inside Vercel's serverless execution window.
        # Users can narrow the set with industry/group/custom-watchlist filters when
        # they need exhaustive scoring across more symbols.
        stocks = stocks.head(max_serverless_analysis_stocks).copy()

    watchlist_symbol_keys = set(watchlist["symbol"].map(_symbol_key))
    # Vercel serverless functions time out quickly when a broad watchlist triggers
    # thousands of live Yahoo Finance requests. Prefer committed prebuilt cache
    # files for broad pages, but allow focused requests (custom lists and a single
    # industry category) to refresh every selected symbol.
    is_custom_watchlist = bool(custom_watchlist_raw.strip())
    allow_live_fetch, max_live_symbols = _resolve_live_fetch_controls(
        is_serverless_runtime=is_serverless_runtime,
        stock_count=len(stocks),
        is_custom_watchlist=is_custom_watchlist,
        tab=tab,
        industry=industry,
    )
    progress_total_stocks = len(stocks)
    price_data_map = prefetch_price_data(
        stocks,
        fetch_period,
        fetch_interval,
        allow_live_fetch=allow_live_fetch,
        allow_stale_disk=True,
        max_live_symbols=max_live_symbols,
    )
    price_ready_count = sum(1 for df in price_data_map.values() if not df.empty)
    signal_data_map = (
        prefetch_price_data(
            stocks,
            "6mo",
            "1d",
            allow_live_fetch=allow_live_fetch,
            allow_stale_disk=True,
            max_live_symbols=max_live_symbols,
        )
        if period == "intraday"
        else {}
    )
    signal_ready_count = sum(1 for df in signal_data_map.values() if not df.empty) if period == "intraday" else progress_total_stocks

    analyzed_stocks = []
    needs_target_price = show_target_price or card_sort == "target_ratio"
    for row in stocks.itertuples(index=False):
        stock_analysis = _build_stock_analysis(
            row.symbol,
            period,
            fetch_period,
            fetch_interval,
            display_period,
            price_data_map.get(row.symbol, pd.DataFrame()),
            signal_data_map.get(row.symbol, pd.DataFrame()),
            needs_target_price,
        )
        analyzed_stocks.append({
            "row": row,
            "df": stock_analysis["df"],
            "signal": stock_analysis["signal"],
            "status": stock_analysis["status"],
            "bucket": stock_analysis["bucket"],
            "close_text": stock_analysis["close_text"],
            "sort_metrics": stock_analysis["sort_metrics"],
            "target_price_text": stock_analysis["target_price_text"] if show_target_price else "-",
            "target_ratio_text": stock_analysis["target_ratio_text"] if show_target_price else "-",
        })

    status_filter_values = {item["bucket"] for item in analyzed_stocks}
    if status_filter != "all" and status_filter not in status_filter_values:
        status_filter = "all"

    sorted_stocks = analyzed_stocks.copy()
    if card_sort == "symbol":
        sorted_stocks.sort(key=lambda item: item["sort_metrics"]["symbol"])
    else:
        sorted_stocks.sort(key=lambda item: item["sort_metrics"][card_sort], reverse=True)

    filtered_stocks = [
        item for item in sorted_stocks
        if status_filter == "all" or item["bucket"] == status_filter
    ]

    total_stocks = len(filtered_stocks)
    total_pages = max(1, math.ceil(total_stocks / limit)) if total_stocks else 1
    page = min(max(page, 1), total_pages)
    start_idx = (page - 1) * limit
    end_idx = start_idx + limit

    client_render_all_cards = len(sorted_stocks) <= 120
    initial_page_symbols = {item["row"].symbol for item in filtered_stocks[start_idx:end_idx]}
    rendered_stock_items = []
    for stock_item in sorted_stocks:
        row = stock_item["row"]
        df = stock_item["df"]
        signal = stock_item["signal"]
        status = stock_item["status"]
        close_text = stock_item["close_text"]
        target_price_text = stock_item["target_price_text"]
        target_ratio_text = stock_item["target_ratio_text"]

        symbol_key = _symbol_key(row.symbol)
        symbol_js = json.dumps(row.symbol, ensure_ascii=False)
        if tab == "watchlist":
            action_btn = (
                "<button type='button' class='watchlist-action is-icon is-remove' "
                f"data-symbol='{html.escape(row.symbol, quote=True)}' "
                f"aria-label='移除 {html.escape(row.name, quote=True)} 自選股' "
                f"title='移除 {html.escape(row.name, quote=True)} 自選股' "
                f"onclick='removeWatchlistStock({symbol_js}, {{ stayOnPage: true }})'>−</button>"
            )
        elif symbol_key in watchlist_symbol_keys:
            action_btn = (
                "<button type='button' class='watchlist-action is-icon is-added' "
                f"aria-label='{html.escape(row.name, quote=True)} 已在自選' "
                f"title='{html.escape(row.name, quote=True)} 已在自選' disabled>✓</button>"
            )
        else:
            action_btn = (
                "<button type='button' class='watchlist-action is-icon is-add' "
                f"data-symbol='{html.escape(row.symbol, quote=True)}' "
                f"aria-label='加入 {html.escape(row.name, quote=True)} 到自選股' "
                f"title='加入 {html.escape(row.name, quote=True)} 到自選股' "
                f"onclick='addWatchlistStock({symbol_js}, {{ stayOnPage: true }})'>＋</button>"
            )
        subgroup_text = row.subgroup if isinstance(row.subgroup, str) and row.subgroup else "-"
        summary_text = _theme_summary_text(getattr(row, "summary", ""))
        reference_html = _theme_reference_html(getattr(row, "reference_url", ""))
        stock_meta_cells = "".join([
            f"<td class='stock-meta-cell'><div class='note-editor' data-symbol='{html.escape(row.symbol)}'>"
            f"<select class='stock-meta-select' data-field='{field}' title='{html.escape(label)}' onchange=\"saveInlineStockMeta(this)\"></select>"
            "</div></td>"
            for field, label in [
                ("action", "操作方法"),
                ("trait", "個股特性"),
                ("stage", "行情階段"),
                ("risk", "風險與觀察"),
            ]
        ])
        note_editor = (
            f"<div class='note-editor' data-symbol='{html.escape(row.symbol)}'>"
            "<input class='stock-note-input' type='text' maxlength='80' placeholder='輸入備註' "
            "oninput=\"queueInlineStockNoteSave(this)\" onchange=\"saveInlineStockNote(this)\">"
            "</div>"
        )
        name_jump_button = (
            "<button type='button' class='stock-jump' "
            f"onclick='scrollToStockCard({symbol_js})' "
            f"title='跳到 {html.escape(row.name, quote=True)} 的曲線圖'>"
            f"{html.escape(row.name)}"
            "</button>"
        )
        row_html = (
            f"<tr data-symbol='{html.escape(row.symbol)}' data-name='{html.escape(row.name, quote=True)}' "
            f"data-summary='{html.escape(summary_text, quote=True)}'>"
            f"<td class='row-action-cell'>{action_btn}</td><td>{html.escape(status.split()[0])}</td><td>{html.escape(row.symbol)}</td>"
            f"<td>{name_jump_button}</td><td>{html.escape(row.group)}</td><td>{html.escape(subgroup_text)}</td>"
            f"<td class='theme-summary-cell'>{html.escape(summary_text)}</td><td class='source-cell'>{reference_html}</td>"
            f"<td>{html.escape(status)}</td><td>{close_text}</td><td>{target_price_text}</td><td>{target_ratio_text}</td>"
            f"{stock_meta_cells}<td class='note-cell'>{note_editor}</td></tr>"
        )
        card_html = ""
        card_html_with_volume = ""
        card_html_without_volume = ""
        card_html_with_volume_price = ""
        card_html_with_volume_no_price = ""
        card_html_without_volume_price = ""
        card_html_without_volume_no_price = ""
        should_render_card = client_render_all_cards or row.symbol in initial_page_symbols
        if should_render_card and not df.empty:
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
            signal_label = str(signal.get("label") or "").strip()
            signal_brief_text = signal_label[:8] + "…" if len(signal_label) > 8 else signal_label
            signal_brief = f"・{signal_brief_text}" if signal_brief_text else ""
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
                    target_ratio_color = "#666"
            card_header_html = (
                "<h3 style='display:flex;justify-content:space-between;align-items:center;gap:8px'>"
                f"<span>{html.escape(row.name)} ({html.escape(row.symbol)}) 收盤 "
                f"<span style='color:{close_color};font-weight:700'>{close_text}{change_text}</span>{html.escape(signal_brief)}</span>"
                f"<span style='font-size:.82rem;color:{target_ratio_color};font-weight:700'>目標價/現價：{target_ratio_text}</span>"
                "</h3>"
                "<div class='theme-card-meta'>"
                f"<p><strong>題材摘要：</strong>{html.escape(summary_text)}</p>"
                f"<p><strong>來源：</strong>{reference_html}</p>"
                "</div>"
            )
            card_html_with_volume_price = (
                card_header_html
                + make_chart_html(df, row.name, True, show_ma, intraday_ref_close=intraday_ref_close, show_price=True)
            )
            card_html_with_volume_no_price = (
                card_header_html
                + make_chart_html(df, row.name, True, show_ma, intraday_ref_close=intraday_ref_close, show_price=False)
            )
            card_html_without_volume_price = (
                card_header_html
                + make_chart_html(df, row.name, False, show_ma, intraday_ref_close=intraday_ref_close, show_price=True)
            )
            card_html_without_volume_no_price = (
                card_header_html
                + make_chart_html(df, row.name, False, show_ma, intraday_ref_close=intraday_ref_close, show_price=False)
            )
            card_html_with_volume = card_html_with_volume_price
            card_html_without_volume = card_html_without_volume_price
            if show_volume and show_price:
                card_html = card_html_with_volume_price
            elif show_volume:
                card_html = card_html_with_volume_no_price
            elif show_price:
                card_html = card_html_without_volume_price
            else:
                card_html = card_html_without_volume_no_price
        rendered_stock_items.append({
            "symbol": row.symbol,
            "bucket": stock_item["bucket"],
            "has_chart_data": not df.empty,
            "row_html": row_html,
            "card_html": card_html,
            "card_html_with_volume": card_html_with_volume,
            "card_html_without_volume": card_html_without_volume,
            "card_html_with_volume_price": card_html_with_volume_price,
            "card_html_with_volume_no_price": card_html_with_volume_no_price,
            "card_html_without_volume_price": card_html_without_volume_price,
            "card_html_without_volume_no_price": card_html_without_volume_no_price,
        })

    visible_rendered_items = [
        item for item in rendered_stock_items
        if status_filter == "all" or item["bucket"] == status_filter
    ]
    visible_page_items = visible_rendered_items[start_idx:end_idx]
    rows = [item["row_html"] for item in visible_page_items]
    cards_data = [
        {"symbol": item["symbol"], "card_html": item["card_html"]}
        for item in visible_page_items
        if item["card_html"]
    ]

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
    limited_notice = (
        f"<div class='notice'>目前候選股共有 {candidate_count} 檔；為避免 Vercel Serverless 逾時，本次先分析前 {max_serverless_analysis_stocks} 檔。可用產業、主題或自訂清單縮小範圍以取得完整排序。</div>"
        if is_limited_analysis
        else ""
    )
    def progress_percent(done: int, total: int) -> int:
        if total <= 0:
            return 100
        return min(100, max(0, round((done / total) * 100)))

    progress_steps = [
        {"label": "股池與篩選", "done": int(candidate_count if not is_limited_analysis else len(stocks)), "total": int(candidate_count), "detail": "已套用頁籤、產業、主題與個人標籤篩選"},
        {"label": "行情資料", "done": int(price_ready_count), "total": int(progress_total_stocks), "detail": "已讀取可用快取或下載結果"},
        {"label": "形勢資料", "done": int(signal_ready_count), "total": int(progress_total_stocks), "detail": "盤中模式會另外讀取日線判斷資料"},
        {"label": "技術分析", "done": int(len(analyzed_stocks)), "total": int(progress_total_stocks), "detail": "已計算均線、量能、形勢分數與排序指標"},
        {"label": "頁面呈現", "done": int(len(rendered_stock_items)), "total": int(len(sorted_stocks)), "detail": "已產生目前表格資料與可用圖卡 HTML"},
    ]
    for step in progress_steps:
        step["percent"] = progress_percent(step["done"], step["total"])
    current_progress_stage = next((step for step in progress_steps if step["percent"] < 100), progress_steps[-1])
    progress_steps_html = "".join([
        f"<li><span class='progress-stage-name'>{html.escape(step['label'])}</span>"
        f"<span class='progress-stage-ratio'>{step['done']} / {step['total']}（{step['percent']}%）</span>"
        f"<div class='progress-bar' aria-hidden='true'><span style='width:{step['percent']}%'></span></div>"
        f"<small>{html.escape(step['detail'])}</small></li>"
        for step in progress_steps
    ])
    pipeline_progress_json = json.dumps(progress_steps, ensure_ascii=False).replace("</", "<\/")

    progress_panel_class = "pipeline-progress is-compact" if compact_progress else "pipeline-progress"

    action_column_label = "移除" if tab == "watchlist" else "自選"
    table_header_html = f"<tr><th>{action_column_label}</th><th>狀態</th><th>代號</th><th>名稱</th><th>主題分類</th><th>次題材</th><th>題材摘要</th><th>來源</th><th>形勢判斷</th><th>收盤</th><th>目標價</th><th>目標價/現價</th><th>操作方法</th><th>個股特性</th><th>行情階段</th><th>風險與觀察</th><th>備註</th></tr>"
    stock_filter_button_text = "選擇自選股" if not stock_meta_stock_filter else f"已選 {len([x for x in stock_meta_stock_filter.replace('，', ',').replace('、', ',').replace(';', ',').replace('；', ',').split(',') for x in x.split() if x.strip()])} 筆條件"
    dashboard_render_items_json = json.dumps(rendered_stock_items, ensure_ascii=False).replace("</", "<\/")
    table_header_html_json = json.dumps(table_header_html, ensure_ascii=False).replace("</", "<\/")

    body = f"""<!doctype html><html lang='zh-Hant'><head><meta charset='utf-8'><title>TW Dashboard</title>
    <style>
      :root{{--bg:#f4f7fb;--panel:#fff;--ink:#172033;--muted:#64748b;--line:#dbe4f0;--brand:#2563eb;--brand-dark:#1d4ed8;--brand-soft:#eaf1ff;--shadow:0 14px 36px rgba(15,23,42,.09);--radius:18px}}
      *{{box-sizing:border-box}}
      body{{font-family:Arial,'Noto Sans TC',sans-serif;margin:0;line-height:1.45;color:var(--ink);background:linear-gradient(180deg,#eef4ff 0,#f7f9fc 240px,var(--bg) 100%);padding:20px}}
      .page-shell{{max-width:1680px;margin:0 auto}}
      .hero{{display:flex;justify-content:space-between;gap:18px;align-items:flex-end;margin:0 0 16px;padding:22px 24px;border:1px solid rgba(255,255,255,.7);border-radius:24px;background:linear-gradient(135deg,#12213f,#2563eb 58%,#43b5ff);box-shadow:var(--shadow);color:#fff}}
      .hero h1{{font-size:1.65rem;margin:0 0 6px;letter-spacing:.02em}}
      .hero p{{margin:0;color:rgba(255,255,255,.82);font-size:.95rem}}
      .hero-badge{{white-space:nowrap;background:rgba(255,255,255,.16);border:1px solid rgba(255,255,255,.28);border-radius:999px;padding:8px 12px;font-size:.88rem}}
      h2{{font-size:1.12rem;margin:0;color:#1e293b}}
      .section-card,.control-panel{{background:rgba(255,255,255,.94);border:1px solid var(--line);border-radius:var(--radius);box-shadow:var(--shadow)}}
      .control-panel{{padding:16px;margin-bottom:16px}}
      .filter-grid{{display:grid;grid-template-columns:repeat(3,minmax(220px,1fr));gap:10px;align-items:stretch}}
      fieldset{{border:1px solid var(--line);border-radius:14px;padding:12px;margin:0;background:#fbfdff;min-width:0}}
      legend{{padding:0 7px;color:#334155;font-size:.86rem;font-weight:700}}
      .field-stack{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}}
      .form-field{{display:grid;gap:4px;color:var(--muted);font-size:.78rem;font-weight:700;letter-spacing:.02em}}
      input,select,button,textarea{{font:inherit}}
      input,select,textarea{{width:100%;font-size:.9rem;padding:8px 10px;border:1px solid #cbd5e1;border-radius:10px;background:#fff;color:#0f172a;min-height:38px}}
      input:focus,select:focus,textarea:focus{{outline:2px solid rgba(37,99,235,.22);border-color:var(--brand)}}
      button{{font-size:.9rem;padding:8px 12px;border:1px solid #cbd5e1;border-radius:999px;background:#fff;color:#1e293b;cursor:pointer;transition:transform .16s ease,box-shadow .16s ease,border-color .16s ease,background .16s ease}}
      button:hover:not(:disabled){{transform:translateY(-1px);box-shadow:0 8px 18px rgba(15,23,42,.12);border-color:#94a3b8}}
      button:disabled{{cursor:not-allowed;opacity:.48}}
      .btn-primary{{background:var(--brand);border-color:var(--brand);color:#fff;font-weight:700}}
      .btn-primary:hover:not(:disabled){{background:var(--brand-dark);border-color:var(--brand-dark)}}
      .btn-soft{{background:var(--brand-soft);border-color:#bfdbfe;color:#1d4ed8;font-weight:700}}
      .form-actions{{display:grid;grid-template-columns:1fr;gap:12px;margin-top:14px;padding-top:14px;border-top:1px solid var(--line);align-items:stretch}}
      .primary-actions,.utility-actions{{position:relative;display:grid;gap:8px;align-content:start;border:1px solid #dbeafe;border-radius:16px;background:linear-gradient(180deg,#fff,#f8fbff);padding:34px 12px 12px;min-width:0}}
      .primary-actions::before,.utility-actions::before{{content:attr(data-title);position:absolute;top:10px;left:12px;color:#1e3a8a;font-size:.78rem;font-weight:900;letter-spacing:.06em}}
      .primary-actions{{grid-template-columns:1fr}}
      .utility-actions{{grid-template-columns:repeat(4,minmax(120px,1fr))}}
      .primary-actions button,.utility-actions button{{width:100%;min-height:40px;display:inline-flex;align-items:center;justify-content:center;text-align:center;line-height:1.2}}
      .watchlist-actions{{display:flex;gap:8px;align-items:center;flex-wrap:wrap}}
      #watchlistStatus{{grid-column:1 / -1;min-height:1.2em;color:#2e7d32;font-size:.86rem}}
      .preset-picker{{grid-column:span 2;display:grid;grid-template-columns:auto minmax(0,1fr);align-items:center;gap:8px;min-width:0;padding:6px 8px;border:1px solid #dbeafe;border-radius:999px;background:#fff}}
      .preset-picker label{{color:var(--muted);font-size:.78rem;font-weight:800;white-space:nowrap}}
      .preset-picker select{{min-width:0;min-height:34px;padding:6px 8px;border-radius:999px}}
      .form-help{{grid-column:1 / -1;color:var(--muted);font-size:.82rem;margin:0;padding:0 4px}}
      .pipeline-progress{{margin:14px 0 0;padding:14px;border:1px solid #bfdbfe;border-radius:16px;background:#f8fbff;color:#172033}}
      .pipeline-progress.is-updating{{border-color:#60a5fa;background:#eff6ff}}
      .pipeline-progress-header{{display:flex;justify-content:space-between;gap:12px;align-items:flex-start;margin-bottom:10px}}
      .pipeline-progress-title{{font-weight:900;color:#1e3a8a}}
      .pipeline-progress-current{{color:#1d4ed8;font-weight:900;white-space:nowrap}}
      .pipeline-progress-message{{margin:0 0 10px;color:var(--muted);font-size:.86rem}}
      .pipeline-progress-list{{display:grid;grid-template-columns:repeat(5,minmax(120px,1fr));gap:8px;list-style:none;padding:0;margin:0}}
      .pipeline-progress-list li{{border:1px solid #dbeafe;border-radius:12px;background:#fff;padding:9px;min-width:0}}
      .progress-stage-name,.progress-stage-ratio{{display:block;font-size:.82rem;font-weight:800}}
      .progress-stage-name{{color:#334155}}
      .progress-stage-ratio{{color:#1d4ed8;margin-top:2px}}
      .progress-bar{{height:7px;border-radius:999px;background:#e2e8f0;overflow:hidden;margin:7px 0}}
      .progress-bar span{{display:block;height:100%;border-radius:999px;background:linear-gradient(90deg,#60a5fa,#2563eb)}}
      .pipeline-progress-list small{{display:block;color:#64748b;font-size:.74rem;line-height:1.3}}
      .pipeline-progress.is-compact{{padding:8px 10px;border-radius:14px}}
      .pipeline-progress.is-compact .pipeline-progress-header{{align-items:center;margin-bottom:6px}}
      .pipeline-progress.is-compact .pipeline-progress-title{{display:inline;font-size:.88rem}}
      .pipeline-progress.is-compact .pipeline-progress-message{{display:none}}
      .pipeline-progress.is-compact .pipeline-progress-current{{font-size:.84rem}}
      .pipeline-progress.is-compact .pipeline-progress-list{{display:flex;gap:6px;overflow-x:auto;padding-bottom:1px}}
      .pipeline-progress.is-compact .pipeline-progress-list li{{display:flex;align-items:center;gap:5px;flex:0 0 auto;border-radius:999px;padding:4px 8px}}
      .pipeline-progress.is-compact .progress-stage-name,.pipeline-progress.is-compact .progress-stage-ratio{{display:inline;font-size:.76rem;line-height:1.1}}
      .pipeline-progress.is-compact .progress-stage-ratio{{margin-top:0}}
      .pipeline-progress.is-compact .progress-bar,.pipeline-progress.is-compact small{{display:none}}
      table{{border-collapse:separate;border-spacing:0;width:100%;font-size:.88rem}}
      th{{position:sticky;top:0;z-index:1;background:#f1f5f9;color:#334155;font-weight:800}}
      td,th{{border-bottom:1px solid #e2e8f0;padding:8px 9px;white-space:nowrap}}
      td:first-child,th:first-child{{border-left:1px solid #e2e8f0}}
      td:last-child,th:last-child{{border-right:1px solid #e2e8f0}}
      tr:hover td{{background:#f8fbff}}
      table th:nth-child(10), table td:nth-child(10), table th:nth-child(11), table td:nth-child(11), table th:nth-child(12), table td:nth-child(12){{text-align:right}}
      .row-action-cell{{text-align:center;width:42px;min-width:42px}}
      .theme-summary-cell{{white-space:normal;min-width:220px;max-width:360px;color:#334155;line-height:1.35}}
      .source-cell{{max-width:140px;overflow:hidden;text-overflow:ellipsis}}
      .source-link{{color:#1565c0;font-weight:700;text-decoration:none}}
      .source-link:hover,.source-link:focus{{text-decoration:underline}}
      .table-wrap{{overflow:auto;border-radius:14px;border:1px solid #e2e8f0;background:#fff}}
      .section-card{{padding:16px;margin:16px 0}}
      .section-header{{display:flex;justify-content:space-between;gap:10px;align-items:center;margin-bottom:12px}}
      .notice{{border:1px solid #fde68a;background:#fffbeb;color:#92400e;border-radius:14px;padding:10px 12px;margin:0 0 12px;font-weight:700}}
      .summary-strip{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;margin:0 0 12px}}
      .summary-item{{border:1px solid var(--line);border-radius:14px;padding:12px;background:linear-gradient(180deg,#fff,#f8fbff)}}
      .summary-label{{display:block;color:var(--muted);font-size:.78rem;font-weight:700}}
      .summary-value{{display:block;font-size:1.12rem;font-weight:800;margin-top:2px}}
      .page-nav{{display:flex;gap:8px;align-items:center;flex-wrap:wrap}}
      .cards-grid{{display:grid;grid-template-columns:repeat({cards_per_row}, minmax(0,1fr));gap:14px}}
      .card{{margin:0;padding:12px;border:1px solid var(--line);border-radius:16px;background:#fff;box-shadow:0 8px 22px rgba(15,23,42,.06);transition:border-color .2s ease,box-shadow .2s ease,background .2s ease,transform .2s ease;overflow:hidden}}
      .card:hover{{transform:translateY(-2px);box-shadow:0 16px 32px rgba(15,23,42,.12)}}
      .card h3{{font-size:.96rem;margin:0 0 8px}}
      .theme-card-meta{{border:1px solid #dbeafe;background:#f8fbff;border-radius:12px;padding:8px 10px;margin:0 0 8px;color:#334155;font-size:.84rem}}
      .theme-card-meta p{{margin:0 0 4px}}
      .theme-card-meta p:last-child{{margin-bottom:0}}
      .card.is-jump-target{{border-color:#1976d2;box-shadow:0 0 0 3px rgba(25,118,210,.16),var(--shadow);background:#f5fbff}}
      .stock-jump{{border:0;background:none;color:#1565c0;text-decoration:underline;cursor:pointer;padding:0;font:inherit;border-radius:4px}}
      .stock-jump:hover,.stock-jump:focus{{color:#0d47a1;text-decoration-thickness:2px;outline:none;box-shadow:none;transform:none}}
      .note-editor{{display:flex;gap:2px;align-items:center;white-space:nowrap}}
      .watchlist-action{{min-width:72px;cursor:pointer;padding:6px 10px}}
      .watchlist-action.is-icon{{display:inline-flex;align-items:center;justify-content:center;width:28px;height:28px;min-width:28px;padding:0;border-radius:999px;font-size:1.12rem;font-weight:900;line-height:1;border:1px solid #cbd5e1;background:#fff;box-shadow:0 2px 6px rgba(15,23,42,.08);transition:background .16s ease,border-color .16s ease,color .16s ease,transform .16s ease,box-shadow .16s ease}}
      .watchlist-action.is-icon:hover,.watchlist-action.is-icon:focus{{transform:translateY(-1px);box-shadow:0 6px 14px rgba(15,23,42,.14);outline:none}}
      .watchlist-action.is-remove{{color:#dc2626;border-color:#fecaca;background:#fff5f5}}
      .watchlist-action.is-remove:hover,.watchlist-action.is-remove:focus{{background:#fee2e2;border-color:#f87171;color:#b91c1c}}
      .watchlist-action.is-add{{color:#2563eb;border-color:#bfdbfe;background:#eff6ff}}
      .watchlist-action.is-add:hover,.watchlist-action.is-add:focus{{background:#dbeafe;border-color:#60a5fa;color:#1d4ed8}}
      .watchlist-action.is-added{{color:#2e7d32;background:#eef8ee;border:1px solid #9ccc9c;cursor:default}}
      .watchlist-batch-modal{{position:fixed;inset:0;background:rgba(0,0,0,.38);display:none;align-items:center;justify-content:center;z-index:9999;padding:16px}}
      .watchlist-batch-modal.is-open{{display:flex}}
      .watchlist-batch-dialog{{background:#fff;border-radius:18px;box-shadow:0 18px 42px rgba(0,0,0,.24);max-width:760px;width:min(760px, 100%);max-height:90vh;display:flex;flex-direction:column;overflow:hidden}}
      .watchlist-batch-header,.watchlist-batch-footer{{display:flex;align-items:center;justify-content:space-between;gap:8px;padding:12px 14px;border-bottom:1px solid #e5e5e5}}
      .watchlist-batch-footer{{border-top:1px solid #e5e5e5;border-bottom:0;justify-content:flex-end;flex-wrap:wrap}}
      .watchlist-batch-body{{padding:12px 14px;overflow:auto;display:grid;gap:10px}}
      .watchlist-batch-row{{display:flex;gap:8px;align-items:center;flex-wrap:wrap}}
      .watchlist-batch-list{{border:1px solid #ddd;border-radius:12px;max-height:260px;overflow:auto;background:#fafafa}}
      .watchlist-batch-item{{display:flex;gap:8px;align-items:center;padding:8px 10px;border-bottom:1px solid #eee;cursor:pointer;min-height:38px}}
      .watchlist-batch-item:last-child{{border-bottom:0}}
      .watchlist-batch-item:hover{{background:#f2f7ff}}
      .watchlist-batch-item.is-added{{color:#777;background:#f5f5f5}}
      .watchlist-batch-item .batch-stock-check{{flex:0 0 16px;width:16px;min-width:16px;height:16px;min-height:16px;margin:0;padding:0;border-radius:3px}}
      .watchlist-batch-item .batch-stock-label{{display:block;flex:1 1 auto;min-width:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;line-height:1.35}}
      .watchlist-batch-item small{{color:#666;margin-left:6px}}
      .watchlist-batch-paste{{width:100%;min-height:70px}}
      .watchlist-batch-help{{color:#666;font-size:.84rem}}
      .stock-filter-picker{{display:block}}
      .stock-filter-picker input[type='hidden']{{display:none}}
      .stock-filter-picker button{{width:100%;min-height:38px}}
      .stock-meta-cell{{width:132px;min-width:132px;max-width:132px}}
      .note-cell{{width:190px;min-width:190px;max-width:190px}}
      .note-editor .stock-meta-select{{width:120px;min-width:0;padding:4px 6px;text-align:left;text-align-last:left;min-height:30px}}
      .note-editor .stock-note-input{{width:170px;min-width:120px;padding:4px 6px;min-height:30px}}
      table th:nth-child(17), table td:nth-child(17){{width:96px;min-width:96px;max-width:96px}}
      @media (max-width: 1180px){{.form-actions{{grid-template-columns:1fr}}.utility-actions{{grid-template-columns:repeat(4,minmax(120px,1fr))}}.pipeline-progress-list{{grid-template-columns:repeat(2,minmax(160px,1fr))}}.cards-grid{{grid-template-columns:repeat(auto-fit,minmax(360px,1fr))}}}}
      @media (max-width: 900px){{.filter-grid{{grid-template-columns:repeat(2,minmax(180px,1fr))}}}}
      @media (max-width: 760px){{body{{padding:10px}}.hero{{display:block;padding:18px}}.hero-badge{{display:inline-block;margin-top:12px}}.filter-grid,.field-stack,.summary-strip,.pipeline-progress-list{{grid-template-columns:1fr}}.form-actions{{gap:10px}}.primary-actions{{grid-template-columns:1fr;padding:32px 10px 10px;border-radius:14px}}.utility-actions{{grid-template-columns:repeat(2,minmax(0,1fr));padding:32px 10px 10px;border-radius:14px}}.preset-picker{{grid-column:1 / -1;grid-template-columns:1fr;border-radius:14px;gap:4px}}.cards-grid{{grid-template-columns:1fr}}input,select,button{{font-size:.84rem}}table{{font-size:.8rem}}}}
      @media (max-width: 390px){{.utility-actions{{grid-template-columns:1fr}}.preset-picker{{grid-column:1}}}}
    </style></head><body>
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
        <fieldset>
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
        <fieldset>
          <legend>K 線與顯示</legend>
          <div class='field-stack'>
            <label class='form-field'>期間<select name='period'><option value='intraday' {'selected' if period=='intraday' else ''}>當日即時K</option><option value='1mo' {'selected' if period=='1mo' else ''}>1個月</option><option value='2mo' {'selected' if period=='2mo' else ''}>2個月</option><option value='3mo' {'selected' if period=='3mo' else ''}>3個月</option><option value='6mo' {'selected' if period=='6mo' else ''}>6個月</option><option value='1y' {'selected' if period=='1y' else ''}>1年</option><option value='5y' {'selected' if period=='5y' else ''}>5年</option></select></label>
            <label class='form-field'>週期<select name='interval'><option value='1m' {'selected' if interval=='1m' else ''}>1 分鐘</option><option value='5m' {'selected' if interval=='5m' else ''}>5 分鐘</option><option value='15m' {'selected' if interval=='15m' else ''}>15 分鐘</option><option value='1d' {'selected' if interval=='1d' else ''}>日線</option><option value='1wk' {'selected' if interval=='1wk' else ''}>週線</option></select></label>
            <label class='form-field'>每列檔數<select name='cards_per_row'>{''.join([f"<option value='{n}' {'selected' if cards_per_row==n else ''}>{n}</option>" for n in range(1, 16)])}</select></label>
            <label class='form-field'>圖塊排序<select name='card_sort'><option value='symbol' {'selected' if card_sort=='symbol' else ''}>個股代號</option><option value='signal_score' {'selected' if card_sort=='signal_score' else ''}>形勢分數</option><option value='close' {'selected' if card_sort=='close' else ''}>成交價</option><option value='volume' {'selected' if card_sort=='volume' else ''}>成交量</option><option value='change_pct' {'selected' if card_sort=='change_pct' else ''}>漲跌幅度</option><option value='target_ratio' {'selected' if card_sort=='target_ratio' else ''}>目標價/現價</option></select></label>
            <label class='form-field'>顯示量K線<select name='show_volume'><option value='1' {'selected' if show_volume else ''}>開啟</option><option value='0' {'selected' if not show_volume else ''}>關閉</option></select></label>
            <label class='form-field'>顯示價K線<select name='show_price'><option value='1' {'selected' if show_price else ''}>開啟</option><option value='0' {'selected' if not show_price else ''}>關閉</option></select></label>
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
      <div id='summaryInfo' class='summary-strip'>
        <div class='summary-item'><span class='summary-label'>符合股數</span><span class='summary-value'>{total_stocks} 檔</span></div>
        <div class='summary-item'><span class='summary-label'>頁面進度</span><span class='summary-value'>{page} / {total_pages}</span></div>
        <div class='summary-item'><span class='summary-label'>每頁顯示</span><span class='summary-value'>{limit} 檔</span></div>
      </div>
      <div id='tableWrap' class='table-wrap'><table>{table_header_html}{''.join(rows) if rows else '<tr><td colspan="17">無符合條件資料</td></tr>'}</table></div>
    </section>
    <section class='section-card' aria-labelledby='chartsTitle'>
      <div class='section-header'><h2 id='chartsTitle'>多股趨勢圖</h2></div>
      <div id='cardsGrid' class='cards-grid'>{''.join([f"<div class='card' data-symbol='{html.escape(cd['symbol'])}'>{cd['card_html']}</div>" for cd in cards_data])}</div>
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
    const STOCK_META_PRESET_LOOKUP = STOCK_META_GROUPS.reduce((lookup, group)=>{{
      group.options.forEach((option)=>{{ lookup[option] = group.id; }});
      return lookup;
    }}, {{}});
    function isTwTradingHours(){{
      const twNow = new Date(new Date().toLocaleString('en-US', {{ timeZone: 'Asia/Taipei' }}));
      const day = twNow.getDay();
      if(day === 0 || day === 6) return false;
      const minutes = twNow.getHours() * 60 + twNow.getMinutes();
      return minutes >= 9 * 60 && minutes <= 13 * 60 + 30;
    }}
    function syncStockMetaPayload(){{
      const payload = document.getElementById('stockMetaPayload');
      if(payload) payload.value = localStorage.getItem(NOTE_STORAGE_KEY) || '{{}}';
    }}
    function serializeForm(){{
      syncStockMetaPayload();
      const fd = new FormData(document.getElementById('cfgForm'));
      return Object.fromEntries(fd.entries());
    }}
    const pipelineProgressSteps = {pipeline_progress_json};
    function selectedOptionText(form, name){{
      const el = form?.elements?.[name];
      if(!el || el.selectedIndex < 0) return '';
      return el.options[el.selectedIndex]?.text?.trim() || '';
    }}
    function buildLoadingMessage(form, reason='更新儀表板'){{
      const tabText = selectedOptionText(form, 'tab') || '目前股池';
      const industryText = selectedOptionText(form, 'industry');
      const periodText = selectedOptionText(form, 'period');
      const intervalText = selectedOptionText(form, 'interval');
      const countText = document.querySelector('#summaryInfo .summary-value')?.textContent?.trim() || '';
      const scope = industryText && !industryText.includes('不限') ? `${{tabText}}／${{industryText}}` : tabText;
      const cadence = [periodText, intervalText].filter(Boolean).join('・');
      const stockHint = countText ? `目前頁面 ${{countText}}；新篩選會由後端重新計算` : '新篩選會由後端重新計算';
      return `${{reason}}：已送出 ${{scope}}（${{stockHint}}）。等待伺服器回傳前，瀏覽器無法取得後端內部逐檔百分比；回傳後此區塊會更新成實際完成比例${{cadence ? `（${{cadence}}）` : ''}}。`;
    }}
    function renderProgressRows(steps){{
      return steps.map((step)=>`
        <li><span class='progress-stage-name'>${{escapeHtmlAttr(step.label)}}</span>
        <span class='progress-stage-ratio'>${{Number(step.done || 0)}} / ${{Number(step.total || 0)}}（${{Number(step.percent || 0)}}%）</span>
        <div class='progress-bar' aria-hidden='true'><span style='width:${{Number(step.percent || 0)}}%'></span></div>
        <small>${{escapeHtmlAttr(step.detail || '')}}</small></li>
      `).join('');
    }}
    function setInlineProgress({{message, current, steps, updating=false}}={{}}){{
      const panel = document.getElementById('pipelineProgress');
      if(!panel) return;
      panel.classList.toggle('is-updating', Boolean(updating));
      const msg = document.getElementById('pipelineProgressMessage');
      const currentEl = document.getElementById('pipelineProgressCurrent');
      const list = document.getElementById('pipelineProgressList');
      if(message && msg) msg.textContent = message;
      if(current && currentEl) currentEl.textContent = current;
      if(Array.isArray(steps) && list) list.innerHTML = renderProgressRows(steps);
    }}
    function hideLoadingProgress(){{
      setInlineProgress({{updating:false}});
    }}
    function showLoadingProgress(reason='更新儀表板'){{
      const form = document.getElementById('cfgForm');
      const waitingSteps = [
        {{label:'瀏覽器送出', done:1, total:1, percent:100, detail:'已同步自選、備註與篩選參數'}},
        {{label:'等待後端', done:0, total:1, percent:0, detail:'後端正在讀取股池、行情與計算；此階段不再顯示假百分比'}},
        ...pipelineProgressSteps.slice(2).map((step)=>({{...step, done:0, percent:0}})),
      ];
      setInlineProgress({{
        updating:true,
        current:'等待後端回應：0%',
        message:buildLoadingMessage(form, reason),
        steps:waitingSteps,
      }});
    }}
    function submitFormWithLoading(form, reason='更新儀表板'){{
      showLoadingProgress(reason);
      window.setTimeout(()=>{{
        if(typeof form.requestSubmit === 'function') form.requestSubmit();
        else form.submit();
      }}, 30);
    }}
    function applyConfig(cfg){{
      const form = document.getElementById('cfgForm');
      Object.entries(cfg).forEach(([k,v])=>{{ if(form.elements[k]) form.elements[k].value = v; }});
      syncStockMetaPayload();
      submitFormWithLoading(form, '讀取設定');
    }}
    function submitConfig(overrides={{}}){{
      const form = document.getElementById('cfgForm');
      Object.entries(overrides).forEach(([k,v])=>{{ if(form.elements[k]) form.elements[k].value = v; }});
      syncStockMetaPayload();
      submitFormWithLoading(form, '更新儀表板');
    }}
    function filteredDashboardItems(){{
      const filter = document.querySelector('[name="status_filter"]')?.value || 'all';
      return dashboardRenderItems.filter((item)=>filter === 'all' || item.bucket === filter);
    }}
    function escapeHtmlAttr(value){{
      return String(value ?? '')
        .replaceAll('&', '&amp;')
        .replaceAll("'", '&#39;')
        .replaceAll('"', '&quot;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;');
    }}
    function selectedCardHtml(item){{
      if(dashboardShowVolume && dashboardShowPrice && item.card_html_with_volume_price) return item.card_html_with_volume_price;
      if(dashboardShowVolume && !dashboardShowPrice && item.card_html_with_volume_no_price) return item.card_html_with_volume_no_price;
      if(!dashboardShowVolume && dashboardShowPrice && item.card_html_without_volume_price) return item.card_html_without_volume_price;
      if(!dashboardShowVolume && !dashboardShowPrice && item.card_html_without_volume_no_price) return item.card_html_without_volume_no_price;
      if(dashboardShowVolume && item.card_html_with_volume) return item.card_html_with_volume;
      if(!dashboardShowVolume && item.card_html_without_volume) return item.card_html_without_volume;
      return item.card_html || '';
    }}
    function syncRenderOnlyUrlParams(){{
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
    }}
    async function renderDashboardPage(page=dashboardCurrentPage){{
      const items = filteredDashboardItems();
      const total = items.length;
      const totalPages = Math.max(1, Math.ceil(total / dashboardPageSize));
      dashboardCurrentPage = Math.min(Math.max(Number(page) || 1, 1), totalPages);
      const start = (dashboardCurrentPage - 1) * dashboardPageSize;
      const pageItems = items.slice(start, start + dashboardPageSize);
      const table = document.querySelector('#tableWrap table');
      if(table){{
        table.innerHTML = dashboardTableHeaderHtml + (pageItems.length ? pageItems.map((item)=>item.row_html).join('') : '<tr><td colspan="17">無符合條件資料</td></tr>');
      }}
      const grid = document.getElementById('cardsGrid');
      if(grid){{
        grid.innerHTML = pageItems
          .map((item)=>({{...item, selected_card_html: selectedCardHtml(item)}}))
          .filter((item)=>item.selected_card_html)
          .map((item)=>`<div class='card' data-symbol='${{escapeHtmlAttr(item.symbol)}}'>${{item.selected_card_html}}</div>`)
          .join('');
        await executeScripts(grid);
      }}
      const summaryValues = document.querySelectorAll('#summaryInfo .summary-value');
      if(summaryValues[0]) summaryValues[0].textContent = `${{total}} 檔`;
      if(summaryValues[1]) summaryValues[1].textContent = `${{dashboardCurrentPage}} / ${{totalPages}}`;
      if(summaryValues[2]) summaryValues[2].textContent = `${{dashboardPageSize}} 檔`;
      const nav = document.getElementById('pageNav');
      if(nav){{
        nav.innerHTML = `<button type='button' onclick='goToPage(${{Math.max(1, dashboardCurrentPage - 1)}})' ${{dashboardCurrentPage <= 1 ? 'disabled' : ''}}>上一頁</button>`
          + `<button type='button' onclick='goToPage(${{Math.min(totalPages, dashboardCurrentPage + 1)}})' ${{dashboardCurrentPage >= totalPages ? 'disabled' : ''}}>下一頁</button>`;
      }}
      populateStockMetaControls();
      applyNotesToTableAndCards();
      updateResponsiveGrid();
      syncRenderOnlyUrlParams();
      hideLoadingProgress();
    }}
    function applyStatusFilterInPlace(){{
      renderDashboardPage(dashboardCurrentPage);
      const selectedText = selectedOptionText(document.getElementById('cfgForm'), 'status_filter') || '全部';
      const isAll = (document.querySelector('[name="status_filter"]')?.value || 'all') === 'all';
      const actionText = isAll ? '已恢復顯示全部形勢判斷' : `已套用「${{selectedText}}」形勢判斷篩選`;
      const cardNote = dashboardHasAllClientCards ? '' : '（大型股池僅表格即時篩選；若要補齊其他頁圖表再換頁更新。）';
      showWatchlistStatus(`${{actionText}}，仍使用目前載入的完整股池，未重新下載行情。${{cardNote}}`);
    }}
    function pageHasClientCards(page){{
      const items = filteredDashboardItems();
      const totalPages = Math.max(1, Math.ceil(items.length / dashboardPageSize));
      const targetPage = Math.min(Math.max(Number(page) || 1, 1), totalPages);
      const start = (targetPage - 1) * dashboardPageSize;
      return items.slice(start, start + dashboardPageSize).every((item)=>!item.has_chart_data || Boolean(selectedCardHtml(item)));
    }}
    function goToPage(page){{
      if(dashboardRenderItems.length && (dashboardHasAllClientCards || pageHasClientCards(page))){{
        renderDashboardPage(page);
        return;
      }}
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

    const allStocks = {json.dumps(picker_stocks[STOCK_GROUP_COLUMNS].to_dict(orient='records'), ensure_ascii=False)};
    const stockFilterStocks = {json.dumps(stock_filter_stocks[STOCK_GROUP_COLUMNS].to_dict(orient='records'), ensure_ascii=False)};
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
        if(autoSubmit) submitConfig();
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
        btn.textContent = btn.classList.contains('is-icon') ? '✓' : '已在自選';
        btn.classList.remove('is-add');
        btn.classList.add('is-added');
        btn.disabled = true;
        btn.title = `${{symbol}} 已在自選`;
        btn.setAttribute('aria-label', `${{symbol}} 已在自選`);
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
        btn.textContent = btn.classList.contains('is-icon') ? '✓' : '已移出';
        btn.disabled = true;
        btn.title = `${{symbol}} 已移出自選`;
        btn.setAttribute('aria-label', `${{symbol}} 已移出自選`);
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
        applyStockMetaFilters();
        return;
      }}
      submitConfig();
    }}
    const batchSelectedSymbols = new Map();
    function getStockLabel(stock){{
      return `${{stock.symbol}} - ${{stock.name || ''}} (${{stock.group || '未分類'}}${{stock.subgroup ? ' / ' + stock.subgroup : ''}})`;
    }}
    function splitStockTokens(value){{
      return String(value || '').split(/[\s,，、;；]+/).map(x => x.trim()).filter(Boolean);
    }}
    function stockMatchesKeyword(stock, keyword=''){{
      const kw = keyword.trim().toLowerCase();
      return !kw || [stock.symbol, stock.name, stock.group, stock.subgroup, stock.summary]
        .filter(Boolean)
        .some(v => String(v).toLowerCase().includes(kw));
    }}
    function syncVisibleStockPickerSelections(selectedSymbols, checkboxSelector, options={{}}){{
      const skipDisabled = options.skipDisabled !== false;
      document.querySelectorAll(checkboxSelector).forEach((el)=>{{
        const key = normalizeWatchlistSymbol(el.value);
        if(el.checked && (!skipDisabled || !el.disabled)) selectedSymbols.set(key, el.value);
        else selectedSymbols.delete(key);
      }});
    }}
    function getStockPickerCheckedSymbols(selectedSymbols, syncFn){{
      syncFn();
      return Array.from(selectedSymbols.values());
    }}
    function renderStockPickerResults({{ keyword='', containerId, stocks, selectedSymbols, checkboxClass, onChange, updatePreview, emptyText, rowState }}){{
      const container = document.getElementById(containerId);
      if(!container) return;
      const rows = stocks.filter(r => stockMatchesKeyword(r, keyword)).slice(0, 200);
      const checkedKeys = new Set(selectedSymbols.keys());
      if(!rows.length){{
        container.innerHTML = `<div class='watchlist-batch-item'>${{emptyText(keyword)}}</div>`;
        updatePreview();
        return;
      }}
      container.innerHTML = rows.map((r)=>{{
        const state = rowState ? rowState(r) : {{ disabled: false, itemClass: '', suffix: '' }};
        const key = normalizeWatchlistSymbol(r.symbol);
        const disabled = Boolean(state.disabled);
        const checked = checkedKeys.has(key) && !disabled;
        return `<label class='watchlist-batch-item${{state.itemClass || ''}}'>
          <input class='${{checkboxClass}}' type='checkbox' value="${{r.symbol}}" ${{checked ? 'checked' : ''}} ${{disabled ? 'disabled' : ''}} onchange='${{onChange}}'>
          <span class="batch-stock-label">${{getStockLabel(r)}}${{state.suffix || ''}}</span>
        </label>`;
      }}).join('');
      updatePreview();
    }}
    function syncVisibleBatchSelections(){{
      syncVisibleStockPickerSelections(batchSelectedSymbols, '.batch-watchlist-check');
    }}
    function getBatchCheckedSymbols(){{
      return getStockPickerCheckedSymbols(batchSelectedSymbols, syncVisibleBatchSelections);
    }}
    function parseBatchSymbolsText(){{
      return splitStockTokens(document.getElementById('batchStockSymbols')?.value || '');
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
      syncVisibleBatchSelections();
      const currentKeys = new Set(getWatchlistSymbols().map(normalizeWatchlistSymbol));
      renderStockPickerResults({{
        keyword,
        containerId: 'batchStockResults',
        stocks: allStocks,
        selectedSymbols: batchSelectedSymbols,
        checkboxClass: 'batch-watchlist-check batch-stock-check',
        onChange: 'syncVisibleBatchSelections(); updateBatchWatchlistPreview()',
        updatePreview: updateBatchWatchlistPreview,
        emptyText: (kw)=>`找不到符合「${{kw}}」的股票`,
        rowState: (stock)=>{{
          const added = currentKeys.has(normalizeWatchlistSymbol(stock.symbol));
          return {{ disabled: added, itemClass: added ? ' is-added' : '', suffix: added ? '<small>已在自選</small>' : '' }};
        }},
      }});
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
      document.querySelectorAll('.batch-watchlist-check:not(:disabled)').forEach((el)=>{{ el.checked = checked; }});
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
    const stockFilterSelectedSymbols = new Map();
    function parseStockFilterValue(){{
      return splitStockTokens(document.getElementById('stockMetaFilter-stock')?.value || '');
    }}
    function seedStockFilterSelectionsFromInput(){{
      stockFilterSelectedSymbols.clear();
      const tokens = parseStockFilterValue();
      if(!tokens.length) return;
      const tokenSet = new Set(tokens.map(normalizeWatchlistSymbol));
      const lowerTokens = tokens.map((token)=>token.toLowerCase());
      stockFilterStocks.forEach((stock)=>{{
        const key = normalizeWatchlistSymbol(stock.symbol);
        const symbol = String(stock.symbol || '').toLowerCase();
        const name = String(stock.name || '').toLowerCase();
        const summary = String(stock.summary || '').toLowerCase();
        if(tokenSet.has(key) || lowerTokens.some((token)=>symbol.includes(token) || name.includes(token) || summary.includes(token))){{
          stockFilterSelectedSymbols.set(key, stock.symbol);
        }}
      }});
    }}
    function syncVisibleStockFilterSelections(){{
      syncVisibleStockPickerSelections(stockFilterSelectedSymbols, '.stock-filter-check');
    }}
    function getStockFilterCheckedSymbols(){{
      return getStockPickerCheckedSymbols(stockFilterSelectedSymbols, syncVisibleStockFilterSelections);
    }}
    function updateStockFilterSummary(){{
      const button = document.getElementById('stockFilterButton');
      if(!button) return;
      const symbols = parseStockFilterValue();
      if(!symbols.length){{
        button.textContent = '選擇自選股';
        button.title = '未套用股名／代號篩選';
        return;
      }}
      button.textContent = `已選 ${{symbols.length}} 筆條件`;
      button.title = symbols.join('、');
    }}
    function updateStockFilterPreview(){{
      const preview = document.getElementById('stockFilterPreview');
      if(!preview) return;
      const selected = getStockFilterCheckedSymbols();
      preview.textContent = selected.length ? `準備以 ${{selected.length}} 檔自選股篩選。` : '未勾選時會清除股名篩選。';
    }}
    function renderStockFilterResults(keyword=''){{
      syncVisibleStockFilterSelections();
      renderStockPickerResults({{
        keyword,
        containerId: 'stockFilterResults',
        stocks: stockFilterStocks,
        selectedSymbols: stockFilterSelectedSymbols,
        checkboxClass: 'stock-filter-check batch-stock-check',
        onChange: 'syncVisibleStockFilterSelections(); updateStockFilterPreview()',
        updatePreview: updateStockFilterPreview,
        emptyText: (kw)=>stockFilterStocks.length ? `找不到符合「${{kw}}」的自選股` : '目前沒有自選股可供股名篩選',
      }});
    }}
    function openStockFilterDialog(){{
      const modal = document.getElementById('stockFilterModal');
      if(!modal) return;
      seedStockFilterSelectionsFromInput();
      modal.classList.add('is-open');
      renderStockFilterResults(document.getElementById('stockFilterKeyword')?.value || '');
      setTimeout(()=>document.getElementById('stockFilterKeyword')?.focus(), 0);
    }}
    function closeStockFilterDialog(){{
      syncVisibleStockFilterSelections();
      document.getElementById('stockFilterModal')?.classList.remove('is-open');
    }}
    function selectVisibleStockFilterStocks(checked){{
      document.querySelectorAll('.stock-filter-check:not(:disabled)').forEach((el)=>{{ el.checked = checked; }});
      syncVisibleStockFilterSelections();
      updateStockFilterPreview();
    }}
    function setStockFilterValue(symbols){{
      const input = document.getElementById('stockMetaFilter-stock');
      if(input) input.value = symbols.join(',');
      updateStockFilterSummary();
    }}
    function applyStockFilterSelection(){{
      const selected = getStockFilterCheckedSymbols();
      setStockFilterValue(selected);
      closeStockFilterDialog();
      applyStockMetaFilters();
      submitConfig({{ page: '1', stock_meta_stock: selected.join(',') }});
    }}
    function clearStockFilterSelection(){{
      stockFilterSelectedSymbols.clear();
      setStockFilterValue([]);
      renderStockFilterResults(document.getElementById('stockFilterKeyword')?.value || '');
      closeStockFilterDialog();
      applyStockMetaFilters();
      submitConfig({{ page: '1', stock_meta_stock: '' }});
    }}
    function normalizeStockMetaEntry(entry){{
      const meta = {{ action: '', trait: '', stage: '', risk: '', note: '' }};
      if(typeof entry === 'string'){{
        const legacyValue = entry.trim();
        const legacyField = STOCK_META_PRESET_LOOKUP[legacyValue];
        if(legacyField) meta[legacyField] = legacyValue;
        else meta.note = legacyValue;
        return meta;
      }}
      if(entry && typeof entry === 'object'){{
        STOCK_META_FIELDS.forEach((field)=>{{
          meta[field] = String(entry[field] || '').trim();
        }});
        meta.note = String(entry.note || entry.memo || '').trim();
      }}
      return meta;
    }}
    function isEmptyStockMeta(meta){{
      return !meta.note && STOCK_META_FIELDS.every((field)=>!meta[field]);
    }}
    function getStockNotes(){{
      try {{
        const raw = localStorage.getItem(NOTE_STORAGE_KEY) || '{{}}';
        const obj = JSON.parse(raw);
        if(!obj || typeof obj !== 'object') return {{}};
        return Object.fromEntries(Object.entries(obj).map(([symbol, entry])=>[symbol, normalizeStockMetaEntry(entry)]));
      }} catch(e) {{
        return {{}};
      }}
    }}
    function setStockNotes(notes){{
      const compact = {{}};
      Object.entries(notes || {{}}).forEach(([symbol, entry])=>{{
        const meta = normalizeStockMetaEntry(entry);
        if(!isEmptyStockMeta(meta)) compact[symbol] = meta;
      }});
      localStorage.setItem(NOTE_STORAGE_KEY, JSON.stringify(compact));
    }}
    function appendOption(parent, value, label){{
      const option = document.createElement('option');
      option.value = value;
      option.textContent = label;
      parent.appendChild(option);
      return option;
    }}
    function populateStockMetaControls(){{
      document.querySelectorAll('.stock-meta-select').forEach((select)=>{{
        const currentValue = select.value;
        const group = STOCK_META_GROUPS.find((item)=>item.id === select.dataset.field);
        select.replaceChildren();
        appendOption(select, '', group ? `設定${{group.label}}` : '未設定');
        if(group) group.options.forEach((value)=>appendOption(select, value, value));
        select.value = group?.options.includes(currentValue) ? currentValue : '';
      }});
    }}
    function refreshStockMetaFilterOptions(){{
      STOCK_META_GROUPS.forEach((group)=>{{
        const filter = document.getElementById(`stockMetaFilter-${{group.id}}`);
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
      }});
    }}
    function applyNotesToTableAndCards(){{
      const notes = getStockNotes();
      document.querySelectorAll('tr[data-symbol]').forEach((tr)=>{{
        const symbol = tr.dataset.symbol;
        const meta = normalizeStockMetaEntry(notes[symbol]);
        STOCK_META_FIELDS.forEach((field)=>{{
          tr.dataset[field] = meta[field] || 'none';
          const select = tr.querySelector(`.stock-meta-select[data-field="${{field}}"]`);
          if(select) select.value = meta[field] || '';
        }});
        tr.dataset.note = meta.note || '';
        const noteInput = tr.querySelector('.stock-note-input');
        if(noteInput && document.activeElement !== noteInput) noteInput.value = meta.note || '';
      }});
      applyStockMetaFilters();
    }}
    function selectedStockMetaFilters(){{
      const filters = Object.fromEntries(STOCK_META_GROUPS.map((group)=>[
        group.id,
        document.getElementById(`stockMetaFilter-${{group.id}}`)?.value || 'all'
      ]));
      filters.note = (document.getElementById('stockMetaFilter-note')?.value || '').trim().toLowerCase();
      filters.stockTokens = (document.getElementById('stockMetaFilter-stock')?.value || '')
        .split(/[\s,，、;；]+/)
        .map((token)=>token.trim().toLowerCase())
        .filter(Boolean);
      return filters;
    }}
    function applyStockMetaFilters(){{
      const filters = selectedStockMetaFilters();
      const visibleSymbols = new Set();
      document.querySelectorAll('tr[data-symbol]').forEach((tr)=>{{
        const removed = tr.dataset.removed === '1';
        const tagMatched = STOCK_META_FIELDS.every((field)=>{{
          const selected = filters[field] || 'all';
          const value = tr.dataset[field] || 'none';
          return selected === 'all' || value === selected || (selected === 'none' && value === 'none');
        }});
        const noteMatched = !filters.note || String(tr.dataset.note || '').toLowerCase().includes(filters.note);
        const stockMatched = !filters.stockTokens.length || filters.stockTokens.some((token)=>{{
          const symbol = String(tr.dataset.symbol || '').toLowerCase();
          const symbolKey = symbol.split('.')[0];
          const name = String(tr.dataset.name || '').toLowerCase();
          const summary = String(tr.dataset.summary || '').toLowerCase();
          return symbol.includes(token) || symbolKey.includes(token) || name.includes(token) || summary.includes(token);
        }});
        const visible = !removed && tagMatched && noteMatched && stockMatched;
        tr.style.display = visible ? '' : 'none';
        if(visible) visibleSymbols.add(tr.dataset.symbol);
      }});
      document.querySelectorAll('.card[data-symbol]').forEach((card)=>{{
        const removed = card.dataset.removed === '1';
        card.style.display = !removed && visibleSymbols.has(card.dataset.symbol) ? '' : 'none';
      }});
    }}
    function saveStockMetaBySymbol(symbol, patch){{
      const notes = getStockNotes();
      const meta = normalizeStockMetaEntry(notes[symbol]);
      Object.assign(meta, patch);
      if(isEmptyStockMeta(meta)) delete notes[symbol];
      else notes[symbol] = meta;
      setStockNotes(notes);
      applyNotesToTableAndCards();
    }}
    function saveInlineStockMeta(selectEl){{
      const editor = selectEl.closest('.note-editor');
      if(!editor) return;
      const field = selectEl.dataset.field;
      if(!STOCK_META_FIELDS.includes(field)) return;
      saveStockMetaBySymbol(editor.dataset.symbol, {{ [field]: (selectEl.value || '').trim() }});
    }}
    function saveInlineStockNote(inputEl){{
      const editor = inputEl.closest('.note-editor');
      if(!editor) return;
      window.clearTimeout(inputEl._saveTimer);
      saveStockMetaBySymbol(editor.dataset.symbol, {{ note: (inputEl.value || '').trim() }});
    }}
    function queueInlineStockNoteSave(inputEl){{
      window.clearTimeout(inputEl._saveTimer);
      inputEl._saveTimer = window.setTimeout(()=>saveInlineStockNote(inputEl), 450);
    }}
    document.getElementById('watchKeyword')?.addEventListener('input', (e)=>renderBatchStockResults(e.target.value));
    document.getElementById('batchStockSymbols')?.addEventListener('input', updateBatchWatchlistPreview);
    document.getElementById('stockFilterKeyword')?.addEventListener('input', (e)=>renderStockFilterResults(e.target.value));
    document.getElementById('watchlistBatchModal')?.addEventListener('click', (e)=>{{
      if(e.target.id === 'watchlistBatchModal') closeBatchWatchlistDialog();
    }});
    document.getElementById('stockFilterModal')?.addEventListener('click', (e)=>{{
      if(e.target.id === 'stockFilterModal') closeStockFilterDialog();
    }});
    document.addEventListener('keydown', (e)=>{{
      if(e.key === 'Escape'){{
        closeBatchWatchlistDialog();
        closeStockFilterDialog();
      }}
    }});
    initServerConfigPicker();
    window.addEventListener('pageshow', hideLoadingProgress);
    if(document.readyState !== 'loading') hideLoadingProgress();
    renderBatchStockResults();
    seedStockFilterSelectionsFromInput();
    updateStockFilterSummary();
    populateStockMetaControls();
    refreshStockMetaFilterOptions();
    applyNotesToTableAndCards();
    STOCK_META_GROUPS.forEach((group)=>{{
      document.getElementById(`stockMetaFilter-${{group.id}}`)?.addEventListener('change', (event)=>{{
        applyStockMetaFilters();
        submitConfig({{ page: '1', [event.target.name]: event.target.value }});
      }});
    }});
    const stockMetaTextFilters = [
      document.getElementById('stockMetaFilter-note'),
      document.getElementById('stockMetaFilter-stock'),
    ].filter(Boolean);
    stockMetaTextFilters.forEach((filter)=>{{
      filter.addEventListener('input', applyStockMetaFilters);
      filter.addEventListener('change', (event)=>{{
        applyStockMetaFilters();
        submitConfig({{ page: '1', [event.target.name]: event.target.value }});
      }});
    }});
    function watchlistSignature(symbols){{
      return symbols.map(normalizeWatchlistSymbol).join(',');
    }}
    function restoreBrowserWatchlistIfAvailable(options={{}}){{
      const raw = localStorage.getItem(WATCHLIST_STORAGE_KEY);
      if(!raw) return false;
      try {{
        const symbols = JSON.parse(raw);
        if(!Array.isArray(symbols) || symbols.length === 0) return false;
        const before = watchlistSignature(getWatchlistSymbols());
        setWatchlistSymbols(symbols.map(String));
        const after = watchlistSignature(getWatchlistSymbols());
        if(options.submit && after !== before) submitConfig({{tab: 'watchlist', page: '1'}});
        return true;
      }} catch(e) {{
        return false;
      }}
    }}
    const hasSavedWatchlist = Boolean(localStorage.getItem(WATCHLIST_STORAGE_KEY));
    if(hasSavedWatchlist && !window.location.search.includes('custom_watchlist=')){{
      restoreBrowserWatchlistIfAvailable({{submit: true}});
    }}
    function autoSubmitConfig(event){{
      const overrides = {{}};
      if(event?.target?.name === 'tab'){{
        overrides.page = '1';
        if(event.target.value === 'watchlist') restoreBrowserWatchlistIfAvailable();
      }}
      submitConfig(overrides);
    }}
    document.getElementById('cfgForm')?.addEventListener('submit', (event)=>{{
      syncStockMetaPayload();
      showLoadingProgress('更新儀表板');
    }});
    const AUTO_SUBMIT_FIELDS = new Set(['tab','industry','period','interval','limit','group_filter','subgroup_filter','show_target_price','compact_progress','card_sort']);
    document.getElementById('cfgForm')?.addEventListener('change', (event)=>{{
      const fieldName = event.target?.name;
      if(fieldName === 'cards_per_row'){{
        dashboardCardsPerRow = Math.min(Math.max(Number(event.target.value) || 3, 1), 15);
        updateResponsiveGrid();
        syncRenderOnlyUrlParams();
        showWatchlistStatus(`已改成每列 ${{dashboardCardsPerRow}} 檔，未重新下載行情或重算篩選。`);
        return;
      }}
      if(fieldName === 'show_volume'){{
        dashboardShowVolume = String(event.target.value) === '1';
        renderDashboardPage(dashboardCurrentPage);
        showWatchlistStatus(`已${{dashboardShowVolume ? '開啟' : '關閉'}}量K線，保留目前頁碼且未重新下載行情。`);
        return;
      }}
      if(fieldName === 'show_price'){{
        dashboardShowPrice = String(event.target.value) === '1';
        renderDashboardPage(dashboardCurrentPage);
        showWatchlistStatus(`已${{dashboardShowPrice ? '開啟' : '關閉'}}價K線，保留目前頁碼且未重新下載行情。`);
        return;
      }}
      if(AUTO_SUBMIT_FIELDS.has(event.target?.name)) autoSubmitConfig(event);
    }});
    document.querySelector('[name="status_filter"]')?.addEventListener('change', applyStatusFilterInPlace);
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
            const timer = window.setTimeout(resolve, 5000);
            script.onload = () => {{ window.clearTimeout(timer); resolve(); }};
            script.onerror = () => {{ window.clearTimeout(timer); reject(); }};
            oldScript.replaceWith(script);
          }}).catch(()=>{{}});
        }} else {{
          script.text = oldScript.textContent;
          oldScript.replaceWith(script);
        }}
      }}
    }}
    function intradayRefreshUrl(){{
      const url = new URL(window.location.href);
      url.searchParams.set('_intraday_refresh', String(Date.now()));
      return url.toString();
    }}
    async function refreshIntradayInPlace({{force=false, reason='背景自動更新'}}={{}}){{
      if(refreshIntradayInPlace.busy || document.hidden || (!force && !isTwTradingHours())) return;
      refreshIntradayInPlace.busy = true;
      try {{
        const response = await fetch(intradayRefreshUrl(), {{ cache: 'no-store' }});
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
        populateStockMetaControls();
        applyNotesToTableAndCards();
        updateResponsiveGrid();
        window.scrollTo(scrollX, scrollY);
        requestAnimationFrame(()=>window.scrollTo(scrollX, scrollY));
        refreshIntradayInPlace.lastSuccessAt = Date.now();
        if(reason !== '背景自動更新') showWatchlistStatus(`${{reason}}完成，已補抓最新即時K線。`);
      }} catch(e) {{
        console.warn('即時K線背景刷新失敗，改用下次排程重試', e);
      }} finally {{
        refreshIntradayInPlace.busy = false;
      }}
    }}
    function refreshIntradayAfterResume(reason){{
      if(!isIntradayMode) return;
      window.setTimeout(()=>refreshIntradayInPlace({{force: isTwTradingHours(), reason}}), 250);
    }}
    if(isIntradayMode){{
      setInterval(()=>refreshIntradayInPlace(), autoRefreshMs);
      window.addEventListener('focus', ()=>refreshIntradayAfterResume('視窗重新啟用'));
      window.addEventListener('online', ()=>refreshIntradayAfterResume('網路恢復'));
      window.addEventListener('pageshow', ()=>refreshIntradayAfterResume('頁面恢復'));
      document.addEventListener('visibilitychange', ()=>{{
        if(!document.hidden) refreshIntradayAfterResume('頁面回到前景');
      }});
    }}
    function resizeDashboardCharts(){{
      if(!window.Plotly?.Plots?.resize) return;
      document.querySelectorAll('#cardsGrid .js-plotly-plot').forEach((chart)=>{{
        if(!chart.offsetParent) return;
        window.Plotly.Plots.resize(chart);
      }});
    }}
    function scheduleDashboardChartAutosize(){{
      window.clearTimeout(scheduleDashboardChartAutosize.timer);
      requestAnimationFrame(()=>requestAnimationFrame(resizeDashboardCharts));
      scheduleDashboardChartAutosize.timer = window.setTimeout(resizeDashboardCharts, 250);
    }}
    function updateResponsiveGrid(){{
      const grid = document.getElementById('cardsGrid');
      if(!grid) return;
      const columns = Math.min(Math.max(Number(dashboardCardsPerRow) || 3, 1), 15);
      grid.style.gridTemplateColumns = `repeat(${{columns}}, minmax(0,1fr))`;
      scheduleDashboardChartAutosize();
    }}
    window.addEventListener('resize', updateResponsiveGrid);
    updateResponsiveGrid();
    </script>
    </div>
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
