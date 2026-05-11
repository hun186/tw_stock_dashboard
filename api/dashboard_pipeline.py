from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Callable

import pandas as pd

from api.dashboard_live_fetch import DEFAULT_LIVE_FETCH_THRESHOLD, resolve_live_fetch_controls

MAX_SERVERLESS_ANALYSIS_STOCKS = 240


@dataclass(slots=True)
class DashboardAnalysisResult:
    stocks: pd.DataFrame
    analyzed_stocks: list[dict]
    sorted_stocks: list[dict]
    filtered_stocks: list[dict]
    status_filter: str
    status_filter_values: set[str]
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
    status_filter: str,
    tab: str,
    industry: str,
    custom_watchlist_raw: str,
    prefetch_price_data: Callable,
    build_stock_analysis: Callable,
) -> DashboardAnalysisResult:
    is_serverless_runtime = os.environ.get("VERCEL") == "1" or bool(os.environ.get("AWS_LAMBDA_FUNCTION_NAME"))
    candidate_count = len(stocks)
    is_limited_analysis = is_serverless_runtime and candidate_count > MAX_SERVERLESS_ANALYSIS_STOCKS
    if is_limited_analysis:
        # Keep broad dashboard requests inside Vercel's serverless execution window.
        # Users can narrow the set with industry/group/custom-watchlist filters when
        # they need exhaustive scoring across more symbols.
        stocks = stocks.head(MAX_SERVERLESS_ANALYSIS_STOCKS).copy()

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

    return DashboardAnalysisResult(
        stocks=stocks,
        analyzed_stocks=analyzed_stocks,
        sorted_stocks=sorted_stocks,
        filtered_stocks=filtered_stocks,
        status_filter=status_filter,
        status_filter_values=status_filter_values,
        candidate_count=candidate_count,
        is_limited_analysis=is_limited_analysis,
        max_serverless_analysis_stocks=MAX_SERVERLESS_ANALYSIS_STOCKS,
        progress_total_stocks=progress_total_stocks,
        price_ready_count=price_ready_count,
        signal_ready_count=signal_ready_count,
        allow_live_fetch=allow_live_fetch,
        max_live_symbols=max_live_symbols,
    )
