from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Callable

import pandas as pd

from api.dashboard_live_fetch import DEFAULT_LIVE_FETCH_THRESHOLD, resolve_live_fetch_controls
from api.dashboard_theme_selector import (
    collect_signal_code_options,
    filter_analyzed_stocks,
    latest_volume_ratio_from_df,
    normalize_signal_code,
)

MAX_SERVERLESS_ANALYSIS_STOCKS = 240
MAX_SERVERLESS_TOPIC_ANALYSIS_STOCKS = 320


def _serverless_analysis_limit(*, group_filter: str, subgroup_filter: str) -> int:
    """Return the symbol cap for serverless analysis requests.

    Broad category scans stay conservative to avoid Vercel timeouts, but a
    selected topic with all subtopics (for example ETF與基金) often lands just
    above the broad cap and is exactly when users need a complete subtheme
    radar. Give those focused topic requests a slightly larger budget.
    """
    has_topic_filter = group_filter != "all" or subgroup_filter != "all"
    return MAX_SERVERLESS_TOPIC_ANALYSIS_STOCKS if has_topic_filter else MAX_SERVERLESS_ANALYSIS_STOCKS


@dataclass(slots=True)
class DashboardAnalysisResult:
    stocks: pd.DataFrame
    analyzed_stocks: list[dict]
    sorted_stocks: list[dict]
    filtered_stocks: list[dict]
    status_filter: str
    status_filter_values: set[str]
    signal_code_options: list[tuple[str, str]]
    candidate_count: int
    is_limited_analysis: bool
    max_serverless_analysis_stocks: int
    progress_total_stocks: int
    price_ready_count: int
    signal_ready_count: int
    allow_live_fetch: bool
    max_live_symbols: int


def run_dashboard_analysis(
    *,
    stocks: pd.DataFrame,
    period: str,
    fetch_period: str,
    fetch_interval: str,
    display_period: str,
    show_target_price: bool,
    card_sort: str,
    card_sort_direction: str = "desc",
    status_filter: str,
    theme_signal_code: str = "all",
    theme_signal_bucket: str = "all",
    theme_volume_ratio: str = "all",
    tab: str,
    industry: str,
    custom_watchlist_raw: str,
    group_filter: str = "all",
    subgroup_filter: str = "all",
    prefetch_price_data: Callable,
    build_stock_analysis: Callable,
) -> DashboardAnalysisResult:
    is_serverless_runtime = os.environ.get("VERCEL") == "1" or bool(os.environ.get("AWS_LAMBDA_FUNCTION_NAME"))
    candidate_count = len(stocks)
    analysis_limit = _serverless_analysis_limit(group_filter=group_filter, subgroup_filter=subgroup_filter)
    is_limited_analysis = is_serverless_runtime and candidate_count > analysis_limit
    if is_limited_analysis:
        # Keep broad dashboard requests inside Vercel's serverless execution window.
        # Users can narrow the set with industry/group/custom-watchlist filters when
        # they need exhaustive scoring across more symbols.
        stocks = stocks.head(analysis_limit).copy()

    is_custom_watchlist = bool(custom_watchlist_raw.strip())
    allow_live_fetch, max_live_symbols = resolve_live_fetch_controls(
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
        stock_analysis = build_stock_analysis(
            row.symbol,
            period,
            fetch_period,
            fetch_interval,
            display_period,
            price_data_map.get(row.symbol, pd.DataFrame()),
            signal_data_map.get(row.symbol, pd.DataFrame()),
            needs_target_price,
        )
        latest_volume_ratio = latest_volume_ratio_from_df(stock_analysis["df"])
        if latest_volume_ratio or "volume_ratio" not in stock_analysis["sort_metrics"]:
            stock_analysis["sort_metrics"]["volume_ratio"] = latest_volume_ratio
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

    signal_code_options = collect_signal_code_options(analyzed_stocks)
    theme_signal_code = normalize_signal_code(theme_signal_code, {code for code, _label in signal_code_options})

    sorted_stocks = analyzed_stocks.copy()
    is_descending = card_sort_direction != "asc"
    if card_sort == "symbol":
        sorted_stocks.sort(key=lambda item: item["sort_metrics"]["symbol"], reverse=is_descending)
    else:
        sorted_stocks.sort(key=lambda item: item["sort_metrics"][card_sort], reverse=is_descending)

    filtered_stocks = filter_analyzed_stocks(
        sorted_stocks,
        status_filter=status_filter,
        signal_bucket_filter=theme_signal_bucket,
        signal_code_filter=theme_signal_code,
        volume_ratio_filter=theme_volume_ratio,
    )

    return DashboardAnalysisResult(
        stocks=stocks,
        analyzed_stocks=analyzed_stocks,
        sorted_stocks=sorted_stocks,
        filtered_stocks=filtered_stocks,
        status_filter=status_filter,
        status_filter_values=status_filter_values,
        signal_code_options=signal_code_options,
        candidate_count=candidate_count,
        is_limited_analysis=is_limited_analysis,
        max_serverless_analysis_stocks=analysis_limit,
        progress_total_stocks=progress_total_stocks,
        price_ready_count=price_ready_count,
        signal_ready_count=signal_ready_count,
        allow_live_fetch=allow_live_fetch,
        max_live_symbols=max_live_symbols,
    )
