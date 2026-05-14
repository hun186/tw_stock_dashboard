from __future__ import annotations

from api.constants import (
    GEMINI_AGENT_GROUP_FILE,
    LLM_GROUP_FILE,
    LLM_GROUP_SHEET,
    WATCHLIST_FILE,
)
from api.dashboard_analysis import build_stock_analysis as _build_stock_analysis
from api.dashboard_page import render_dashboard_page
from api.dashboard_pipeline import run_dashboard_analysis
from api.dashboard_request import DashboardRequest
from api.dashboard_theme_rotation import build_theme_rotation_rows, render_theme_rotation_radar
from api.dashboard_theme_selector import filter_stocks_by_summary_keyword
from api.dashboard_stock_pool import build_stock_pool
from api.dashboard_view_model import (
    build_dashboard_render_payload,
    filter_dashboard_stocks,
)
from api.data_loader import (
    load_gemini_agent_group_map,
    load_llm_group_map,
    load_twse_industry_map,
    load_watchlist,
)
from api.market_data import (
    prefetch_price_data,
    resolve_price_params,
)


def render_dashboard_response(request: DashboardRequest) -> str:
    """Build the dashboard HTML for a parsed WSGI request."""
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
    card_sort_direction = request.card_sort_direction
    compact_progress = request.compact_progress
    theme_summary_keyword = request.theme_summary_keyword
    theme_signal_code = request.theme_signal_code
    theme_signal_bucket = request.theme_signal_bucket
    theme_volume_ratio = request.theme_volume_ratio

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

    stocks, stock_meta_filter_values, stock_meta_filters = filter_dashboard_stocks(
        source_stocks,
        group_filter=group_filter,
        subgroup_filter=subgroup_filter,
        stock_meta_payload=stock_meta_payload,
        stock_meta_filters=stock_meta_filters,
        stock_meta_note_filter=stock_meta_note_filter,
        stock_meta_stock_filter=stock_meta_stock_filter,
    )
    stocks = filter_stocks_by_summary_keyword(stocks, theme_summary_keyword)

    analysis_result = run_dashboard_analysis(
        stocks=stocks,
        period=period,
        fetch_period=fetch_period,
        fetch_interval=fetch_interval,
        display_period=display_period,
        show_target_price=show_target_price,
        card_sort=card_sort,
        card_sort_direction=card_sort_direction,
        status_filter=status_filter,
        theme_signal_code=theme_signal_code,
        theme_signal_bucket=theme_signal_bucket,
        theme_volume_ratio=theme_volume_ratio,
        tab=tab,
        industry=industry,
        custom_watchlist_raw=custom_watchlist_raw,
        group_filter=group_filter,
        subgroup_filter=subgroup_filter,
        prefetch_price_data=prefetch_price_data,
        build_stock_analysis=_build_stock_analysis,
    )
    stocks = analysis_result.stocks
    analyzed_stocks = analysis_result.analyzed_stocks
    sorted_stocks = analysis_result.sorted_stocks
    filtered_stocks = analysis_result.filtered_stocks
    status_filter = analysis_result.status_filter
    status_filter_values = analysis_result.status_filter_values
    signal_code_options = analysis_result.signal_code_options
    candidate_count = analysis_result.candidate_count
    is_limited_analysis = analysis_result.is_limited_analysis
    max_serverless_analysis_stocks = analysis_result.max_serverless_analysis_stocks
    progress_total_stocks = analysis_result.progress_total_stocks
    price_ready_count = analysis_result.price_ready_count
    signal_ready_count = analysis_result.signal_ready_count

    theme_rotation_rows = build_theme_rotation_rows(filtered_stocks)
    theme_rotation_html = render_theme_rotation_radar(theme_rotation_rows)

    render_payload = build_dashboard_render_payload(
        filtered_stocks=filtered_stocks,
        sorted_stocks=sorted_stocks,
        status_filter=status_filter,
        limit=limit,
        page=page,
        watchlist=watchlist,
        tab=tab,
        period=period,
        show_volume=show_volume,
        show_price=show_price,
    )

    return render_dashboard_page(
        analyzed_stocks=analyzed_stocks,
        candidate_count=candidate_count,
        card_sort=card_sort,
        card_sort_direction=card_sort_direction,
        cards_data=render_payload.cards_data,
        cards_per_row=cards_per_row,
        client_render_all_cards=render_payload.client_render_all_cards,
        compact_progress=compact_progress,
        group_filter=group_filter,
        industries=industries,
        industry=industry,
        industry_df=industry_df,
        interval=interval,
        is_limited_analysis=is_limited_analysis,
        limit=limit,
        max_serverless_analysis_stocks=max_serverless_analysis_stocks,
        page=render_payload.page,
        period=period,
        picker_stocks=picker_stocks,
        price_ready_count=price_ready_count,
        progress_total_stocks=progress_total_stocks,
        rendered_stock_items=render_payload.rendered_stock_items,
        rows=render_payload.rows,
        show_price=show_price,
        show_target_price=show_target_price,
        show_volume=show_volume,
        signal_code_options=signal_code_options,
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
        theme_summary_keyword=theme_summary_keyword,
        theme_signal_code=theme_signal_code,
        theme_signal_bucket=theme_signal_bucket,
        theme_volume_ratio=theme_volume_ratio,
        stocks=stocks,
        subgroup_filter=subgroup_filter,
        tab=tab,
        total_pages=render_payload.total_pages,
        theme_rotation_html=theme_rotation_html,
        total_stocks=render_payload.total_stocks,
        valid_groups=valid_groups,
        valid_subgroups=valid_subgroups,
        watchlist=watchlist,
    )
