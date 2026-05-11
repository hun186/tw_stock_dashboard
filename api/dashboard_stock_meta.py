from __future__ import annotations

import pandas as pd

from api.dashboard_request import STOCK_META_FIELDS
from api.market_data import _symbol_key


def normalize_stock_meta_entry(entry) -> dict[str, str]:
    meta = {field: "" for field in STOCK_META_FIELDS}
    meta["note"] = ""
    if isinstance(entry, str):
        meta["note"] = entry.strip()
    elif isinstance(entry, dict):
        for field in meta:
            meta[field] = str(entry.get(field) or "").strip()
        if not meta["note"]:
            meta["note"] = str(entry.get("memo") or "").strip()
    return meta


def stock_meta_filter_values(stocks: pd.DataFrame, stock_meta_payload: dict) -> dict[str, set[str]]:
    values = {field: set() for field in STOCK_META_FIELDS}
    for symbol in stocks["symbol"].astype(str):
        meta = normalize_stock_meta_entry(stock_meta_payload.get(symbol, {}))
        for field in values:
            values[field].add(meta[field] or "none")
    return values


def stock_filter_tokens(stock_meta_stock_filter: str) -> list[str]:
    return [
        token.strip().lower()
        for token in stock_meta_stock_filter.replace("，", ",").replace("、", ",").replace(";", ",").replace("；", ",").split(",")
        for token in token.split()
        if token.strip()
    ]


def apply_stock_meta_filters(
    stocks: pd.DataFrame,
    *,
    stock_meta_payload: dict,
    stock_meta_filters: dict[str, str],
    stock_meta_note_filter: str,
    stock_meta_stock_filter: str,
) -> pd.DataFrame:
    note_filter_lower = stock_meta_note_filter.lower()
    filter_tokens = stock_filter_tokens(stock_meta_stock_filter)

    def stock_matches_meta_filters(row):
        symbol = str(row["symbol"])
        name = str(row["name"] or "")
        summary = str(row.get("summary", "") or "")
        meta = normalize_stock_meta_entry(stock_meta_payload.get(symbol, {}))
        tags_match = all(
            selected == "all"
            or (selected == "none" and not meta[field])
            or meta[field] == selected
            for field, selected in stock_meta_filters.items()
        )
        note_matches = not note_filter_lower or note_filter_lower in meta["note"].lower()
        symbol_lower = symbol.lower()
        symbol_key_lower = _symbol_key(symbol).lower()
        name_lower = name.lower()
        summary_lower = summary.lower()
        stock_matches = not filter_tokens or any(
            token in symbol_lower or token in symbol_key_lower or token in name_lower or token in summary_lower
            for token in filter_tokens
        )
        return tags_match and note_matches and stock_matches

    return stocks[stocks.apply(stock_matches_meta_filters, axis=1)]
