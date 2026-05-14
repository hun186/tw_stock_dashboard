from __future__ import annotations

import json
from dataclasses import dataclass
from urllib.parse import parse_qs

from api.dashboard_theme_selector import (
    normalize_signal_bucket,
    normalize_signal_code,
    normalize_summary_keyword,
    normalize_volume_ratio,
)

STOCK_META_FIELDS = ("action", "trait", "stage", "risk")


def positive_int_param(params, name: str, default: int, *, max_value: int | None = None) -> int:
    try:
        value = int(params.get(name, [str(default)])[0])
    except (TypeError, ValueError):
        value = default
    if value <= 0:
        value = default
    if max_value is not None:
        value = min(value, max_value)
    return value


def parse_stock_meta_payload(raw: str) -> dict:
    try:
        payload = json.loads(raw) if raw else {}
        if not isinstance(payload, dict):
            return {}
        return payload
    except json.JSONDecodeError:
        return {}


@dataclass(slots=True)
class DashboardRequest:
    tab: str
    period: str
    interval: str
    limit: int
    page: int
    status_filter: str
    group_filter: str
    subgroup_filter: str
    industry: str
    stock_meta_filters: dict[str, str]
    stock_meta_note_filter: str
    stock_meta_stock_filter: str
    stock_meta_payload_raw: str
    stock_meta_payload: dict
    theme_summary_keyword: str
    theme_signal_code: str
    theme_signal_bucket: str
    theme_volume_ratio: str
    cards_per_row: int
    custom_watchlist_raw: str
    show_volume: bool
    show_price: bool
    show_target_price: bool
    card_sort: str
    card_sort_direction: str
    compact_progress: bool

    @property
    def has_stock_meta_filter(self) -> bool:
        return (
            any(value != "all" for value in self.stock_meta_filters.values())
            or bool(self.stock_meta_note_filter)
            or bool(self.stock_meta_stock_filter)
        )

    @property
    def has_theme_selector_filter(self) -> bool:
        return (
            bool(self.theme_summary_keyword)
            or self.theme_signal_code != "all"
            or self.theme_signal_bucket != "all"
            or self.theme_volume_ratio != "all"
        )


def parse_dashboard_request(environ) -> DashboardRequest:
    params = parse_qs(environ.get("QUERY_STRING", ""))
    stock_meta_filters = {
        field: params.get(f"stock_meta_{field}", ["all"])[0]
        for field in STOCK_META_FIELDS
    }
    stock_meta_filters = {
        field: value if value and value != "all" else "all"
        for field, value in stock_meta_filters.items()
    }
    card_sort = params.get("card_sort", ["signal_score"])[0]
    sort_options = {"symbol", "close", "volume", "change_pct", "target_ratio", "signal_score"}
    if card_sort not in sort_options:
        card_sort = "signal_score"
    card_sort_direction = params.get("card_sort_direction", ["desc"])[0]
    if card_sort_direction not in {"asc", "desc"}:
        card_sort_direction = "desc"
    stock_meta_payload_raw = params.get("stock_meta_payload", [""])[0]
    return DashboardRequest(
        tab=params.get("tab", ["watchlist"])[0],
        period=params.get("period", ["3mo"])[0],
        interval=params.get("interval", ["1d"])[0],
        limit=positive_int_param(params, "limit", 30, max_value=120),
        page=positive_int_param(params, "page", 1),
        status_filter=params.get("status_filter", ["all"])[0],
        group_filter=params.get("group_filter", ["all"])[0],
        subgroup_filter=params.get("subgroup_filter", ["all"])[0],
        industry=params.get("industry", ["all"])[0],
        stock_meta_filters=stock_meta_filters,
        stock_meta_note_filter=params.get("stock_meta_note", [""])[0].strip(),
        stock_meta_stock_filter=params.get("stock_meta_stock", [""])[0].strip(),
        stock_meta_payload_raw=stock_meta_payload_raw,
        stock_meta_payload=parse_stock_meta_payload(stock_meta_payload_raw),
        theme_summary_keyword=normalize_summary_keyword(params.get("theme_summary", [""])[0]),
        theme_signal_code=normalize_signal_code(params.get("theme_signal_code", ["all"])[0]),
        theme_signal_bucket=normalize_signal_bucket(params.get("theme_signal_bucket", ["all"])[0]),
        theme_volume_ratio=normalize_volume_ratio(params.get("theme_volume_ratio", ["all"])[0]),
        cards_per_row=positive_int_param(params, "cards_per_row", 3, max_value=15),
        custom_watchlist_raw=params.get("custom_watchlist", [""])[0],
        show_volume=params.get("show_volume", ["1"])[0] == "1",
        show_price=params.get("show_price", ["1"])[0] == "1",
        show_target_price=params.get("show_target_price", ["0"])[0] == "1",
        card_sort=card_sort,
        card_sort_direction=card_sort_direction,
        compact_progress=params.get("compact_progress", ["1"])[0] == "1",
    )
