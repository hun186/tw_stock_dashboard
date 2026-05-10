from __future__ import annotations

import html
import json
from typing import Any

from api.constants import STATUS_FILTERS
from api.dashboard_progress import build_progress_steps, progress_steps_json, render_progress_steps_html


def safe_json_script(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False).replace("</", "<\\/")


def render_industry_options(*, industries, selected_industry: str) -> str:
    return (
        "<option value='all' {}>不限產業</option>".format("selected" if selected_industry == "all" else "")
        + "".join([
            f"<option value='{html.escape(r.industry)}' {'selected' if r.industry == selected_industry else ''}>{html.escape(r.industry_label)}</option>"
            for r in industries.itertuples(index=False)
        ])
    )


def render_status_options(*, selected_status: str, status_filter_values: set[str]) -> str:
    return "".join([
        f"<option value='{k}' {'selected' if k == selected_status else ''}>{v}</option>"
        for k, v in STATUS_FILTERS.items()
        if k == "all" or k in status_filter_values
    ])


def render_topic_options(*, values: list[str], selected_value: str, all_label: str) -> str:
    return f"<option value='all'>{all_label}</option>" + "".join([
        f"<option value='{html.escape(v)}' {'selected' if v == selected_value else ''}>{html.escape(v)}</option>"
        for v in values
    ])


def build_stock_meta_filter_context(stock_meta_filter_values: dict[str, set[str]]) -> dict[str, dict]:
    return {
        "options": {
            field: sorted(value for value in values if value != "none")
            for field, values in stock_meta_filter_values.items()
        },
        "has_empty": {
            field: "none" in values
            for field, values in stock_meta_filter_values.items()
        },
    }


def count_selected_stock_filter_terms(stock_meta_stock_filter: str) -> int:
    normalized_filter = (
        stock_meta_stock_filter.replace("，", ",")
        .replace("、", ",")
        .replace(";", ",")
        .replace("；", ",")
    )
    return len([x for x in normalized_filter.split(",") for x in x.split() if x.strip()])


def stock_filter_button_text(stock_meta_stock_filter: str) -> str:
    if not stock_meta_stock_filter:
        return "選擇自選股"
    return f"已選 {count_selected_stock_filter_terms(stock_meta_stock_filter)} 筆條件"


def build_save_payload(
    *,
    tab: str,
    industry: str,
    period: str,
    interval: str,
    limit: int,
    status_filter: str,
    group_filter: str,
    subgroup_filter: str,
    stock_meta_filters: dict[str, str],
    stock_meta_note_filter: str,
    stock_meta_stock_filter: str,
    stock_meta_payload_raw: str,
    cards_per_row: int,
    watchlist,
    show_volume: bool,
    show_price: bool,
    show_target_price: bool,
    card_sort: str,
    compact_progress: bool,
    page: int,
) -> dict[str, Any]:
    return {
        "tab": tab,
        "industry": industry,
        "period": period,
        "interval": interval,
        "limit": limit,
        "status_filter": status_filter,
        "group_filter": group_filter,
        "subgroup_filter": subgroup_filter,
        **{f"stock_meta_{field}": value for field, value in stock_meta_filters.items()},
        "stock_meta_note": stock_meta_note_filter,
        "stock_meta_stock": stock_meta_stock_filter,
        "stock_meta_payload": stock_meta_payload_raw,
        "cards_per_row": cards_per_row,
        "custom_watchlist": ",".join(watchlist["symbol"].tolist()),
        "show_volume": "1" if show_volume else "0",
        "show_price": "1" if show_price else "0",
        "show_target_price": "1" if show_target_price else "0",
        "card_sort": card_sort,
        "compact_progress": "1" if compact_progress else "0",
        "page": page,
    }


def build_progress_context(
    *,
    analyzed_stocks,
    candidate_count: int,
    is_limited_analysis: bool,
    price_ready_count: int,
    progress_total_stocks: int,
    rendered_stock_items,
    signal_ready_count: int,
    sorted_stocks,
    stocks,
    compact_progress: bool,
) -> dict[str, Any]:
    steps = build_progress_steps(
        analyzed_count=len(analyzed_stocks),
        candidate_count=candidate_count,
        is_limited_analysis=is_limited_analysis,
        price_ready_count=price_ready_count,
        progress_total_stocks=progress_total_stocks,
        rendered_count=len(rendered_stock_items),
        signal_ready_count=signal_ready_count,
        sorted_count=len(sorted_stocks),
        visible_stock_count=len(stocks),
    )
    return {
        "steps": steps,
        "current_stage": next((step for step in steps if step["percent"] < 100), steps[-1]),
        "steps_html": render_progress_steps_html(steps),
        "steps_json": progress_steps_json(steps),
        "panel_class": "pipeline-progress is-compact" if compact_progress else "pipeline-progress",
    }


def render_table_header_html(*, tab: str) -> str:
    action_column_label = "移除" if tab == "watchlist" else "自選"
    return f"<tr><th>{action_column_label}</th><th>狀態</th><th>代號</th><th>名稱</th><th>形勢判斷</th><th>收盤</th><th>目標價</th><th>目標價/現價</th><th>題材</th><th>操作方法</th><th>個股特性</th><th>行情階段</th><th>風險與觀察</th><th>備註</th><th class='theme-summary-cell'>題材摘要</th><th class='source-cell'>來源</th></tr>"
