from __future__ import annotations

import pandas as pd

from api.data_loader import STOCK_GROUP_COLUMNS


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

    # Sources are passed from lowest to highest priority. For every column, keep
    # the highest-priority non-empty value so a legacy watchlist without
    # summary/reference_url does not erase Gemini metadata for the same symbol.
    merged_rows = []
    for symbol, group in combined.groupby("symbol", sort=False):
        row = {"symbol": symbol}
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
