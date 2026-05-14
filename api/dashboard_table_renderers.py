from __future__ import annotations

import html
import json

from api.dashboard_research_card import render_research_symbol_button
from api.dashboard_theme import theme_compact_html as _theme_compact_html
from api.market_data import _symbol_key

STOCK_META_FIELD_LABELS = [
    ("action", "操作方法"),
    ("trait", "個股特性"),
    ("stage", "行情階段"),
    ("risk", "風險與觀察"),
]


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


def render_change_pct_text(sort_metrics: dict | None) -> str:
    if not isinstance(sort_metrics, dict):
        return "-"
    try:
        value = float(sort_metrics.get('change_pct'))
    except (TypeError, ValueError):
        return "-"
    return "-" if value <= -998 else f"{value:+.2f}%"


def render_stock_row(
    *,
    row,
    tab: str,
    watchlist_symbol_keys: set[str],
    status: str,
    close_text: str,
    target_price_text: str,
    target_ratio_text: str,
    change_pct_text: str,
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
    research_symbol_button = render_research_symbol_button(symbol=row.symbol, compact=True)
    return (
        f"<tr data-symbol='{html.escape(row.symbol)}' data-name='{html.escape(row.name, quote=True)}' "
        f"data-summary='{html.escape(summary_text, quote=True)}'>"
        f"<td class='row-action-cell'>{action_btn}</td><td class='status-icon-cell'>{html.escape(status.split()[0])}</td><td class='symbol-cell'>{research_symbol_button}</td>"
        f"<td class='name-cell'><div class='name-cell-actions'>{name_jump_button}</div></td><td class='signal-cell'>{html.escape(status)}</td>"
        f"<td>{close_text}</td><td class='change-pct-cell'>{change_pct_text}</td><td>{target_price_text}</td><td>{target_ratio_text}</td><td class='theme-cell'>{theme_compact_html}</td>"
        f"{render_stock_meta_cells(row.symbol)}<td class='note-cell'>{render_note_editor(row.symbol)}</td>"
        f"<td class='theme-summary-cell'>{html.escape(summary_text)}</td><td class='source-cell'>{reference_html}</td></tr>"
    )
