from __future__ import annotations

import math

from api.constants import (
    GEMINI_AGENT_GROUP_FILE,
    LLM_GROUP_FILE,
    LLM_GROUP_SHEET,
    WATCHLIST_FILE,
)
from api.data_loader import (
    load_gemini_agent_group_map,
    load_llm_group_map,
    load_twse_industry_map,
    load_watchlist,
)
from api.market_data import (
    _symbol_key,
    prefetch_price_data,
    resolve_price_params,
)
from api.dashboard_analysis import build_stock_analysis as _build_stock_analysis
from api.dashboard_page import render_dashboard_page
from api.dashboard_pipeline import (
    DEFAULT_LIVE_FETCH_THRESHOLD,
    resolve_live_fetch_controls as _resolve_live_fetch_controls,
    run_dashboard_analysis,
)
from api.dashboard_renderers import render_dashboard_stock_items
from api.dashboard_request import parse_dashboard_request, positive_int_param as _positive_int_param
from api.dashboard_stock_pool import (
    apply_stock_meta_filters,
    build_stock_pool,
    ensure_stock_group_columns as _ensure_stock_group_columns,
    merge_stock_group_sources as _merge_stock_group_sources,
    sort_stocks_by_symbol as _sort_stocks_by_symbol,
    stock_code_sort_value as _stock_code_sort_value,
    stock_group_frame as _stock_group_frame,
    stock_meta_filter_values as collect_stock_meta_filter_values,
)


__all__ = [
    "DEFAULT_LIVE_FETCH_THRESHOLD",
    "_ensure_stock_group_columns",
    "_merge_stock_group_sources",
    "_positive_int_param",
    "_resolve_live_fetch_controls",
    "_sort_stocks_by_symbol",
    "_stock_code_sort_value",
    "_stock_group_frame",
    "app",
]


def app(environ, start_response):
    request = parse_dashboard_request(environ)
    tab = request.tab
    period = request.period
    interval = request.interval
    limit = request.limit
    page = request.page
    status_filter = request.status_filter
    group_filter = request.group_filter
    subgroup_filter = request.subgroup_filter
    stock_meta_filters = request.stock_meta_filters.copy()
    stock_meta_note_filter = request.stock_meta_note_filter
    stock_meta_stock_filter = request.stock_meta_stock_filter
    stock_meta_payload_raw = request.stock_meta_payload_raw
    stock_meta_payload = request.stock_meta_payload
    cards_per_row = request.cards_per_row
    custom_watchlist_raw = request.custom_watchlist_raw
    show_volume = request.show_volume
    show_price = request.show_price
    show_target_price = request.show_target_price
    card_sort = request.card_sort
    compact_progress = request.compact_progress

    fetch_period, fetch_interval, display_period = resolve_price_params(period, interval)

    stock_pool = build_stock_pool(
        file_watchlist=load_watchlist(WATCHLIST_FILE),
        gemini_agent_watchlist=load_gemini_agent_group_map(GEMINI_AGENT_GROUP_FILE),
        llm_watchlist=load_llm_group_map(LLM_GROUP_FILE, LLM_GROUP_SHEET),
        industry_df=load_twse_industry_map(),
        custom_watchlist_raw=custom_watchlist_raw,
        tab=tab,
        industry=request.industry,
        group_filter=group_filter,
        subgroup_filter=subgroup_filter,
    )
    industry_df = stock_pool.industry_df
    industries = stock_pool.industries
    industry = stock_pool.industry
    watchlist = stock_pool.watchlist
    source_stocks = stock_pool.source_stocks
    picker_stocks = stock_pool.picker_stocks
    stock_filter_stocks = stock_pool.stock_filter_stocks
    valid_groups = stock_pool.valid_groups
    valid_subgroups = stock_pool.valid_subgroups
    group_filter = stock_pool.group_filter
    subgroup_filter = stock_pool.subgroup_filter

    stocks = source_stocks.copy()
    if group_filter != "all":
        stocks = stocks[stocks["group"] == group_filter]
    if subgroup_filter != "all":
        stocks = stocks[stocks["subgroup"] == subgroup_filter]

    stock_meta_filter_values = collect_stock_meta_filter_values(stocks, stock_meta_payload)
    for field, selected in stock_meta_filters.items():
        if selected != "all" and selected not in stock_meta_filter_values[field]:
            stock_meta_filters[field] = "all"
    has_stock_meta_filter = (
        any(value != "all" for value in stock_meta_filters.values())
        or bool(stock_meta_note_filter)
        or bool(stock_meta_stock_filter)
    )

    if has_stock_meta_filter:
        stocks = apply_stock_meta_filters(
            stocks,
            stock_meta_payload=stock_meta_payload,
            stock_meta_filters=stock_meta_filters,
            stock_meta_note_filter=stock_meta_note_filter,
            stock_meta_stock_filter=stock_meta_stock_filter,
        )

    analysis_result = run_dashboard_analysis(
        stocks=stocks,
        period=period,
        fetch_period=fetch_period,
        fetch_interval=fetch_interval,
        display_period=display_period,
        show_target_price=show_target_price,
        card_sort=card_sort,
        status_filter=status_filter,
        tab=tab,
        industry=industry,
        custom_watchlist_raw=custom_watchlist_raw,
        prefetch_price_data=prefetch_price_data,
        build_stock_analysis=_build_stock_analysis,
    )
    stocks = analysis_result.stocks
    analyzed_stocks = analysis_result.analyzed_stocks
    sorted_stocks = analysis_result.sorted_stocks
    filtered_stocks = analysis_result.filtered_stocks
    status_filter = analysis_result.status_filter
    status_filter_values = analysis_result.status_filter_values
    candidate_count = analysis_result.candidate_count
    is_limited_analysis = analysis_result.is_limited_analysis
    max_serverless_analysis_stocks = analysis_result.max_serverless_analysis_stocks
    progress_total_stocks = analysis_result.progress_total_stocks
    price_ready_count = analysis_result.price_ready_count
    signal_ready_count = analysis_result.signal_ready_count

    watchlist_symbol_keys = set(watchlist["symbol"].map(_symbol_key))

    total_stocks = len(filtered_stocks)
    total_pages = max(1, math.ceil(total_stocks / limit)) if total_stocks else 1
    page = min(max(page, 1), total_pages)
    start_idx = (page - 1) * limit
    end_idx = start_idx + limit

    client_render_all_cards = len(sorted_stocks) <= 120
    initial_page_symbols = {item["row"].symbol for item in filtered_stocks[start_idx:end_idx]}
    rendered_stock_items = render_dashboard_stock_items(
        sorted_stocks=sorted_stocks,
        initial_page_symbols=initial_page_symbols,
        client_render_all_cards=client_render_all_cards,
        tab=tab,
        watchlist_symbol_keys=watchlist_symbol_keys,
        period=period,
        show_volume=show_volume,
        show_price=show_price,
    )

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

    body = render_dashboard_page(
        analyzed_stocks=analyzed_stocks,
        candidate_count=candidate_count,
        card_sort=card_sort,
        cards_data=cards_data,
        cards_per_row=cards_per_row,
        client_render_all_cards=client_render_all_cards,
        compact_progress=compact_progress,
        group_filter=group_filter,
        industries=industries,
        industry=industry,
        industry_df=industry_df,
        interval=interval,
        is_limited_analysis=is_limited_analysis,
        limit=limit,
        max_serverless_analysis_stocks=max_serverless_analysis_stocks,
        page=page,
        period=period,
        picker_stocks=picker_stocks,
        price_ready_count=price_ready_count,
        progress_total_stocks=progress_total_stocks,
        rendered_stock_items=rendered_stock_items,
        rows=rows,
        show_price=show_price,
        show_target_price=show_target_price,
        show_volume=show_volume,
        signal_ready_count=signal_ready_count,
        sorted_stocks=sorted_stocks,
        source_stocks=source_stocks,
        status_filter=status_filter,
        status_filter_values=status_filter_values,
        stock_filter_stocks=stock_filter_stocks,
        stock_meta_filter_values=stock_meta_filter_values,
        stock_meta_filters=stock_meta_filters,
        stock_meta_note_filter=stock_meta_note_filter,
        stock_meta_payload_raw=stock_meta_payload_raw,
        stock_meta_stock_filter=stock_meta_stock_filter,
        stocks=stocks,
        subgroup_filter=subgroup_filter,
        tab=tab,
        total_pages=total_pages,
        total_stocks=total_stocks,
        valid_groups=valid_groups,
        valid_subgroups=valid_subgroups,
        watchlist=watchlist,
    )
    data = body.encode("utf-8")
    start_response("200 OK", [("Content-Type", "text/html; charset=utf-8"), ("Content-Length", str(len(data)))])
    return [data]


if __name__ == "__main__":
    from api.dashboard_server import run_dev_server

    run_dev_server(app)
