from __future__ import annotations

import html
import json
from typing import Iterable

import pandas as pd

from api.charts import make_chart_html
from api.constants import DOWN_COLOR, UP_COLOR
from api.dashboard_theme import (
    theme_compact_html as _theme_compact_html,
    theme_reference_html as _theme_reference_html,
    theme_summary_text as _theme_summary_text,
)
from api.market_data import _symbol_key

STOCK_META_FIELD_LABELS = [
    ("action", "操作方法"),
    ("trait", "個股特性"),
    ("stage", "行情階段"),
    ("risk", "風險與觀察"),
]

EMPTY_CARD_VARIANTS = {
    "card_html": "",
    "card_html_with_volume": "",
    "card_html_without_volume": "",
    "card_html_with_volume_price": "",
    "card_html_with_volume_no_price": "",
    "card_html_without_volume_price": "",
    "card_html_without_volume_no_price": "",
}


def render_watchlist_action_button(*, row, tab: str, watchlist_symbol_keys: set[str]) -> str:
    symbol_js = json.dumps(row.symbol, ensure_ascii=False)
    symbol_key = _symbol_key(row.symbol)
    if tab == "watchlist":
        return (
            "<button type='button' class='watchlist-action is-icon is-remove' "
            f"data-symbol='{html.escape(row.symbol, quote=True)}' "
            f"aria-label='移除 {html.escape(row.name, quote=True)} 自選股' "
            f"title='移除 {html.escape(row.name, quote=True)} 自選股' "
            f"onclick='removeWatchlistStock({symbol_js}, {{ stayOnPage: true }})'>−</button>"
        )
    if symbol_key in watchlist_symbol_keys:
        return (
            "<button type='button' class='watchlist-action is-icon is-added' "
            f"aria-label='{html.escape(row.name, quote=True)} 已在自選' "
            f"title='{html.escape(row.name, quote=True)} 已在自選' disabled>✓</button>"
        )
    return (
        "<button type='button' class='watchlist-action is-icon is-add' "
        f"data-symbol='{html.escape(row.symbol, quote=True)}' "
        f"aria-label='加入 {html.escape(row.name, quote=True)} 到自選股' "
        f"title='加入 {html.escape(row.name, quote=True)} 到自選股' "
        f"onclick='addWatchlistStock({symbol_js}, {{ stayOnPage: true }})'>＋</button>"
    )


def render_stock_meta_cells(symbol: str) -> str:
    return "".join([
        f"<td class='stock-meta-cell'><div class='note-editor' data-symbol='{html.escape(symbol)}'>"
        f"<select class='stock-meta-select' data-field='{field}' title='{html.escape(label)}' onchange=\"saveInlineStockMeta(this)\"></select>"
        "</div></td>"
        for field, label in STOCK_META_FIELD_LABELS
    ])


def render_note_editor(symbol: str) -> str:
    return (
        f"<div class='note-editor' data-symbol='{html.escape(symbol)}'>"
        "<input class='stock-note-input' type='text' maxlength='80' placeholder='輸入備註' "
        "oninput=\"queueInlineStockNoteSave(this)\" onchange=\"saveInlineStockNote(this)\">"
        "</div>"
    )


def render_stock_row(
    *,
    row,
    tab: str,
    watchlist_symbol_keys: set[str],
    status: str,
    close_text: str,
    target_price_text: str,
    target_ratio_text: str,
    summary_text: str,
    reference_html: str,
) -> str:
    symbol_js = json.dumps(row.symbol, ensure_ascii=False)
    action_btn = render_watchlist_action_button(row=row, tab=tab, watchlist_symbol_keys=watchlist_symbol_keys)
    theme_compact_html = _theme_compact_html(row.group, row.subgroup)
    name_jump_button = (
        "<button type='button' class='stock-jump' "
        f"onclick='scrollToStockCard({symbol_js})' "
        f"title='跳到 {html.escape(row.name, quote=True)} 的曲線圖'>"
        f"{html.escape(row.name)}"
        "</button>"
    )
    return (
        f"<tr data-symbol='{html.escape(row.symbol)}' data-name='{html.escape(row.name, quote=True)}' "
        f"data-summary='{html.escape(summary_text, quote=True)}'>"
        f"<td class='row-action-cell'>{action_btn}</td><td class='status-icon-cell'>{html.escape(status.split()[0])}</td><td class='symbol-cell'>{html.escape(row.symbol)}</td>"
        f"<td class='name-cell'>{name_jump_button}</td><td class='signal-cell'>{html.escape(status)}</td>"
        f"<td>{close_text}</td><td>{target_price_text}</td><td>{target_ratio_text}</td><td class='theme-cell'>{theme_compact_html}</td>"
        f"{render_stock_meta_cells(row.symbol)}<td class='note-cell'>{render_note_editor(row.symbol)}</td>"
        f"<td class='theme-summary-cell'>{html.escape(summary_text)}</td><td class='source-cell'>{reference_html}</td></tr>"
    )


def target_ratio_color(target_ratio_text: str) -> str:
    if not target_ratio_text.endswith("%"):
        return "#666"
    try:
        target_ratio_value = float(target_ratio_text[:-1])
    except ValueError:
        return "#666"
    if target_ratio_value >= 110:
        return "#c62828"
    if target_ratio_value >= 100:
        return "#d84315"
    if target_ratio_value >= 90:
        return "#2e7d32"
    return "#0b8f3a"


def render_card_variants(
    *,
    row,
    df: pd.DataFrame,
    signal: dict,
    period: str,
    close_text: str,
    target_ratio_text: str,
    summary_text: str,
    reference_html: str,
    show_volume: bool,
    show_price: bool,
) -> dict[str, str]:
    if df.empty:
        return EMPTY_CARD_VARIANTS.copy()

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
    card_theme_popover = (
        "<span class='theme-title-panel' role='tooltip'>"
        f"<span><strong>題材摘要：</strong>{html.escape(summary_text)}</span>"
        f"<span><strong>來源：</strong>{reference_html}</span>"
        "</span>"
    )
    card_header_html = (
        "<h3 class='card-title'>"
        f"<span class='card-title-main'><span class='theme-title-popover' tabindex='0' aria-label='題材摘要與來源'>{html.escape(row.name)} ({html.escape(row.symbol)}){card_theme_popover}</span><span>收盤 "
        f"<span style='color:{close_color};font-weight:700'>{close_text}{change_text}</span>{html.escape(signal_brief)}</span></span>"
        f"<span class='card-target-ratio' style='color:{target_ratio_color(target_ratio_text)}'>目標價/現價：{target_ratio_text}</span>"
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
    if show_volume and show_price:
        card_html = card_html_with_volume_price
    elif show_volume:
        card_html = card_html_with_volume_no_price
    elif show_price:
        card_html = card_html_without_volume_price
    else:
        card_html = card_html_without_volume_no_price
    return {
        "card_html": card_html,
        "card_html_with_volume": card_html_with_volume_price,
        "card_html_without_volume": card_html_without_volume_price,
        "card_html_with_volume_price": card_html_with_volume_price,
        "card_html_with_volume_no_price": card_html_with_volume_no_price,
        "card_html_without_volume_price": card_html_without_volume_price,
        "card_html_without_volume_no_price": card_html_without_volume_no_price,
    }


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
    reference_html = _theme_reference_html(getattr(row, "reference_url", ""))
    card_variants = (
        render_card_variants(
            row=row,
            df=df,
            signal=signal,
            period=period,
            close_text=close_text,
            target_ratio_text=target_ratio_text,
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
        "has_chart_data": not df.empty,
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
