from __future__ import annotations

import math
from dataclasses import dataclass

from api.dashboard_renderers import render_dashboard_stock_items
from api.dashboard_stock_pool import apply_stock_meta_filters, stock_meta_filter_values as collect_stock_meta_filter_values
from api.market_data import _symbol_key


@dataclass(frozen=True)
class DashboardRenderPayload:
    total_stocks: int
    total_pages: int
    page: int
    rendered_stock_items: list[dict]
    rows: list[str]
    cards_data: list[dict[str, str]]
    client_render_all_cards: bool


def filter_dashboard_stocks(
    source_stocks,
    *,
    group_filter: str,
    subgroup_filter: str,
    stock_meta_payload,
    stock_meta_filters: dict[str, str],
    stock_meta_note_filter: str,
    stock_meta_stock_filter: str,
):
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

    return stocks, stock_meta_filter_values, stock_meta_filters


def build_dashboard_render_payload(
    *,
    filtered_stocks,
    sorted_stocks,
    status_filter: str,
    limit: int,
    page: int,
    watchlist,
    tab: str,
    period: str,
    show_volume: bool,
    show_price: bool,
) -> DashboardRenderPayload:
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

    return DashboardRenderPayload(
        total_stocks=total_stocks,
        total_pages=total_pages,
        page=page,
        rendered_stock_items=rendered_stock_items,
        rows=rows,
        cards_data=cards_data,
        client_render_all_cards=client_render_all_cards,
    )
