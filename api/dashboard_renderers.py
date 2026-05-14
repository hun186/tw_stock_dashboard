from __future__ import annotations

from typing import Iterable

from api.dashboard_card_renderers import EMPTY_CARD_VARIANTS, render_card_variants, target_ratio_color
from api.dashboard_research_card import stock_research_payload
from api.dashboard_table_renderers import (
    STOCK_META_FIELD_LABELS,
    render_note_editor,
    render_stock_meta_cells,
    render_stock_row,
    render_watchlist_action_button,
)
from api.dashboard_theme_selector import signal_code, signal_label
from api.dashboard_theme import (
    theme_reference_html as _theme_reference_html,
    theme_summary_text as _theme_summary_text,
)


def render_stock_item(
    *,
    stock_item: dict,
    tab: str,
    watchlist_symbol_keys: set[str],
    period: str,
    show_volume: bool,
    show_price: bool,
    should_render_card: bool,
) -> dict:
    row = stock_item["row"]
    df = stock_item["df"]
    signal = stock_item["signal"]
    status = stock_item["status"]
    close_text = stock_item["close_text"]
    target_price_text = stock_item["target_price_text"]
    target_ratio_text = stock_item["target_ratio_text"]
    summary_text = _theme_summary_text(getattr(row, "summary", ""))
    reference_url = getattr(row, "reference_url", "")
    reference_html = _theme_reference_html(reference_url)
    card_variants = (
        render_card_variants(
            row=row,
            df=df,
            signal=signal,
            period=period,
            close_text=close_text,
            target_ratio_text=target_ratio_text,
            target_price_text=target_price_text,
            summary_text=summary_text,
            reference_html=reference_html,
            show_volume=show_volume,
            show_price=show_price,
        )
        if should_render_card
        else EMPTY_CARD_VARIANTS.copy()
    )
    return {
        "symbol": row.symbol,
        "bucket": stock_item["bucket"],
        "signal_code": signal_code(stock_item),
        "signal_label": signal_label(stock_item),
        "volume_ratio": float(stock_item.get("sort_metrics", {}).get("volume_ratio", 0.0) or 0.0),
        "sort_metrics": stock_item.get("sort_metrics", {}).copy(),
        "has_chart_data": not df.empty,
        "research": stock_research_payload(
            row=row,
            status=status,
            close_text=close_text,
            target_price_text=target_price_text,
            target_ratio_text=target_ratio_text,
            summary_text=summary_text,
            reference_url=reference_url,
        ),
        "row_html": render_stock_row(
            row=row,
            tab=tab,
            watchlist_symbol_keys=watchlist_symbol_keys,
            status=status,
            close_text=close_text,
            target_price_text=target_price_text,
            target_ratio_text=target_ratio_text,
            summary_text=summary_text,
            reference_html=reference_html,
        ),
        **card_variants,
    }


def render_dashboard_stock_items(
    *,
    sorted_stocks: Iterable[dict],
    initial_page_symbols: set[str],
    client_render_all_cards: bool,
    tab: str,
    watchlist_symbol_keys: set[str],
    period: str,
    show_volume: bool,
    show_price: bool,
) -> list[dict]:
    return [
        render_stock_item(
            stock_item=stock_item,
            tab=tab,
            watchlist_symbol_keys=watchlist_symbol_keys,
            period=period,
            show_volume=show_volume,
            show_price=show_price,
            should_render_card=client_render_all_cards or stock_item["row"].symbol in initial_page_symbols,
        )
        for stock_item in sorted_stocks
    ]


__all__ = [
    "EMPTY_CARD_VARIANTS",
    "STOCK_META_FIELD_LABELS",
    "render_card_variants",
    "render_dashboard_stock_items",
    "render_note_editor",
    "render_stock_item",
    "render_stock_meta_cells",
    "render_stock_row",
    "render_watchlist_action_button",
    "target_ratio_color",
]
