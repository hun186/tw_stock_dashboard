from __future__ import annotations

import pandas as pd

from api.data_loader import STOCK_GROUP_COLUMNS
from api.market_utils import _symbol_key


def ensure_stock_group_columns(df: pd.DataFrame) -> pd.DataFrame:
    normalized = df.copy()
    for col in STOCK_GROUP_COLUMNS:
        if col not in normalized.columns:
            normalized[col] = ""
        normalized[col] = normalized[col].fillna("").astype(str).str.strip()
    return normalized


def stock_group_frame(df: pd.DataFrame) -> pd.DataFrame:
    return ensure_stock_group_columns(df)[STOCK_GROUP_COLUMNS].copy()


def merge_stock_group_sources(*sources: pd.DataFrame) -> pd.DataFrame:
    frames = [stock_group_frame(source) for source in sources if source is not None]
    if not frames:
        return pd.DataFrame(columns=STOCK_GROUP_COLUMNS)
    combined = pd.concat(frames, ignore_index=True)
    combined = combined[combined["symbol"] != ""].copy()
    if combined.empty:
        return pd.DataFrame(columns=STOCK_GROUP_COLUMNS)

    # Treat .TW and .TWO variants of the same code as the same stock. Some
    # upstream LLM-generated metadata can contain the wrong Taiwan suffix (for
    # example 8069.TW instead of the official 8069.TWO); merging by symbol key
    # prevents duplicate rows while still allowing the higher-priority source to
    # enrich non-symbol metadata. Suffix-only symbols such as ".TWO" normalize to
    # an empty key and are discarded because they cannot be fetched or matched.
    combined["_symbol_key"] = combined["symbol"].map(_symbol_key)
    combined = combined[combined["_symbol_key"] != ""].copy()
    if combined.empty:
        return pd.DataFrame(columns=STOCK_GROUP_COLUMNS)

    # Sources are passed from lowest to highest priority. Keep the first valid
    # symbol for a key so official exchange symbols from lower-priority sources
    # stay canonical, but for every descriptive column keep the highest-priority
    # non-empty value so legacy watchlists do not erase richer metadata.
    merged_rows = []
    for _, group in combined.groupby("_symbol_key", sort=False):
        row = {"symbol": group["symbol"].iloc[0]}
        for col in [c for c in STOCK_GROUP_COLUMNS if c != "symbol"]:
            values = group[col].tolist()
            row[col] = next((value for value in reversed(values) if value), "")
        merged_rows.append(row)
    return pd.DataFrame(merged_rows, columns=STOCK_GROUP_COLUMNS)


def stock_code_sort_value(symbol: object) -> tuple[str, str]:
    normalized = str(symbol or "").strip().upper()
    code = normalized.split(".", 1)[0]
    return code, normalized


def sort_stocks_by_symbol(stocks: pd.DataFrame) -> pd.DataFrame:
    if stocks.empty or "symbol" not in stocks.columns:
        return stocks.copy()
    sorted_stocks = stocks.copy()
    sort_values = sorted_stocks["symbol"].map(stock_code_sort_value)
    sorted_stocks["_stock_code_sort"] = sort_values.map(lambda value: value[0])
    sorted_stocks["_stock_symbol_sort"] = sort_values.map(lambda value: value[1])
    return (
        sorted_stocks.sort_values(["_stock_code_sort", "_stock_symbol_sort"], kind="stable")
        .drop(columns=["_stock_code_sort", "_stock_symbol_sort"])
        .reset_index(drop=True)
    )
