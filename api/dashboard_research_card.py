"""Helpers for stock research-card payloads and Markdown export."""

from __future__ import annotations

import html
import json

STOCK_META_MARKDOWN_LABELS = (
    ("action", "操作方法"),
    ("trait", "個股特性"),
    ("stage", "行情階段"),
    ("risk", "風險與觀察"),
    ("note", "備註"),
)


def research_card_value(value: object, *, fallback: str = "-") -> str:
    """Return a display-safe plain-text value for research card fields."""
    text = str(value or "").strip()
    return text if text else fallback


def stock_research_payload(
    *,
    row,
    status: str,
    close_text: str,
    target_price_text: str,
    target_ratio_text: str,
    summary_text: str,
    reference_url: object,
) -> dict[str, str]:
    """Build the immutable browser payload used to render/copy a research card."""
    return {
        "symbol": research_card_value(getattr(row, "symbol", "")),
        "name": research_card_value(getattr(row, "name", "")),
        "group": research_card_value(getattr(row, "group", "")),
        "subgroup": research_card_value(getattr(row, "subgroup", "")),
        "summary": research_card_value(summary_text),
        "reference_url": research_card_value(reference_url),
        "status": research_card_value(status),
        "close_text": research_card_value(close_text),
        "target_price_text": research_card_value(target_price_text),
        "target_ratio_text": research_card_value(target_ratio_text),
    }


def render_research_symbol_button(*, symbol: str, compact: bool = False) -> str:
    """Render the stock symbol as the direct trigger for the research card."""
    classes = "research-symbol-button is-compact" if compact else "research-symbol-button"
    escaped_symbol = html.escape(symbol, quote=True)
    symbol_js = html.escape(json.dumps(symbol, ensure_ascii=False), quote=True)
    accessible_label = html.escape(f"展開 {symbol} 研究卡", quote=True)
    return (
        f"<button type='button' class='{classes}' data-research-symbol='{escaped_symbol}' "
        f"onclick='openStockResearchCard({symbol_js})' "
        f"title='{accessible_label}' aria-label='{accessible_label}'>{html.escape(symbol)}</button>"
    )
