from __future__ import annotations

import html

import pandas as pd

from api.charts import make_chart_html
from api.constants import DOWN_COLOR, UP_COLOR
from api.dashboard_research_card import render_research_card_button

EMPTY_CARD_VARIANTS = {
    "card_html": "",
    "card_html_with_volume": "",
    "card_html_without_volume": "",
    "card_html_with_volume_price": "",
    "card_html_with_volume_no_price": "",
    "card_html_without_volume_price": "",
    "card_html_without_volume_no_price": "",
}


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
    target_price_text: str,
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
    research_button = render_research_card_button(symbol=row.symbol)
    card_header_html = (
        "<h3 class='card-title'>"
        f"<span class='card-title-main'><span class='theme-title-popover' tabindex='0' aria-label='題材摘要與來源'>{html.escape(row.name)} ({html.escape(row.symbol)}){card_theme_popover}</span><span>收盤 "
        f"<span style='color:{close_color};font-weight:700'>{close_text}{change_text}</span>{html.escape(signal_brief)}</span></span>"
        "<span class='card-title-actions'>"
        f"<span class='card-target-ratio' style='color:{target_ratio_color(target_ratio_text)}'>"
        f"<span>目標價：{html.escape(target_price_text)}</span><span>目標價/現價：{html.escape(target_ratio_text)}</span>"
        "</span>"
        f"{research_button}"
        "</span>"
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
