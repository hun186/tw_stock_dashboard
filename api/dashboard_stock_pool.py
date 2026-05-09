from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from api.data_loader import STOCK_GROUP_COLUMNS
from api.market_data import _symbol_key
from api.dashboard_request import STOCK_META_FIELDS


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


@dataclass(slots=True)
class StockPoolResult:
    stock_metadata: pd.DataFrame
    base_watchlist: pd.DataFrame
    industry_df: pd.DataFrame
    industries: pd.DataFrame
    valid_industries: set[str]
    industry: str
    watchlist: pd.DataFrame
    all_stocks: pd.DataFrame
    source_stocks: pd.DataFrame
    picker_stocks: pd.DataFrame
    stock_filter_stocks: pd.DataFrame
    valid_groups: list[str]
    valid_subgroups: list[str]
    group_filter: str
    subgroup_filter: str


def build_stock_pool(
    *,
    file_watchlist: pd.DataFrame,
    gemini_agent_watchlist: pd.DataFrame,
    llm_watchlist: pd.DataFrame,
    industry_df: pd.DataFrame,
    custom_watchlist_raw: str,
    tab: str,
    industry: str,
    group_filter: str,
    subgroup_filter: str,
) -> StockPoolResult:
    file_watchlist = stock_group_frame(file_watchlist)
    gemini_agent_watchlist = stock_group_frame(gemini_agent_watchlist)
    llm_watchlist = stock_group_frame(llm_watchlist)
    stock_metadata = merge_stock_group_sources(llm_watchlist, gemini_agent_watchlist, file_watchlist).reset_index(drop=True)
    base_watchlist = file_watchlist.reset_index(drop=True)
    industry_df = ensure_stock_group_columns(industry_df)
    industries = industry_df[["industry", "industry_label"]].drop_duplicates().sort_values("industry")
    valid_industries = set(industries["industry"].astype(str)) if not industries.empty else set()
    if industry != "all" and industry not in valid_industries:
        industry = "all"
    watchlist_overrides = (
        stock_metadata[STOCK_GROUP_COLUMNS]
        .assign(symbol_key=lambda d: d["symbol"].map(_symbol_key))
        .drop_duplicates(subset=["symbol"], keep="last")
        .rename(columns={col: f"watch_{col}" for col in STOCK_GROUP_COLUMNS if col != "symbol"})
    )

    all_stocks = merge_stock_group_sources(
        industry_df[STOCK_GROUP_COLUMNS],
        stock_metadata[STOCK_GROUP_COLUMNS],
    )

    custom_symbols = [x.strip() for x in custom_watchlist_raw.split(",") if x.strip()]
    custom_df = all_stocks[all_stocks["symbol"].isin(custom_symbols)][STOCK_GROUP_COLUMNS]
    missing_symbols = [x for x in custom_symbols if x not in set(custom_df["symbol"])]
    if missing_symbols:
        custom_df = pd.concat([
            custom_df,
            pd.DataFrame([
                {"symbol": s, "name": s, "group": "自訂", "subgroup": "", "summary": "", "reference_url": ""}
                for s in missing_symbols
            ]),
        ], ignore_index=True)
    watchlist = custom_df if not custom_df.empty else base_watchlist

    if tab == "category":
        source_stocks = industry_df.copy()
        if industry != "all":
            source_stocks = source_stocks[source_stocks["industry"] == industry]
        source_stocks = source_stocks[STOCK_GROUP_COLUMNS]
    else:
        source_stocks = watchlist[STOCK_GROUP_COLUMNS].copy()
        if industry != "all":
            industry_symbol_keys = set(
                industry_df.loc[industry_df["industry"] == industry, "symbol"].map(_symbol_key)
            )
            source_stocks = source_stocks[source_stocks["symbol"].map(_symbol_key).isin(industry_symbol_keys)]

    source_stocks["symbol_key"] = source_stocks["symbol"].map(_symbol_key)
    source_stocks = source_stocks.merge(
        watchlist_overrides[["symbol_key", "watch_name", "watch_group", "watch_subgroup", "watch_summary", "watch_reference_url"]],
        on="symbol_key",
        how="left",
    )
    for col in ["name", "group", "subgroup", "summary", "reference_url"]:
        source_stocks[col] = source_stocks[f"watch_{col}"].where(
            source_stocks[f"watch_{col}"].fillna("").astype(str).str.strip().ne(""),
            source_stocks[col],
        )
    source_stocks = source_stocks[STOCK_GROUP_COLUMNS]

    picker_stocks = sort_stocks_by_symbol(
        merge_stock_group_sources(all_stocks, watchlist[STOCK_GROUP_COLUMNS], source_stocks)
    )
    stock_filter_stocks = sort_stocks_by_symbol(
        merge_stock_group_sources(watchlist[STOCK_GROUP_COLUMNS])
    )

    valid_groups = sorted([g for g in source_stocks["group"].dropna().astype(str).str.strip().unique() if g])
    if group_filter != "all" and group_filter not in valid_groups:
        group_filter = "all"
    subgroup_source = source_stocks if group_filter == "all" else source_stocks[source_stocks["group"] == group_filter]
    valid_subgroups = sorted([g for g in subgroup_source["subgroup"].dropna().astype(str).str.strip().unique() if g])
    if subgroup_filter != "all" and subgroup_filter not in valid_subgroups:
        subgroup_filter = "all"

    return StockPoolResult(
        stock_metadata=stock_metadata,
        base_watchlist=base_watchlist,
        industry_df=industry_df,
        industries=industries,
        valid_industries=valid_industries,
        industry=industry,
        watchlist=watchlist,
        all_stocks=all_stocks,
        source_stocks=source_stocks,
        picker_stocks=picker_stocks,
        stock_filter_stocks=stock_filter_stocks,
        valid_groups=valid_groups,
        valid_subgroups=valid_subgroups,
        group_filter=group_filter,
        subgroup_filter=subgroup_filter,
    )


def stock_meta_filter_values(stocks: pd.DataFrame, stock_meta_payload: dict) -> dict[str, set[str]]:
    values = {field: set() for field in STOCK_META_FIELDS}
    for symbol in stocks["symbol"].astype(str):
        meta = normalize_stock_meta_entry(stock_meta_payload.get(symbol, {}))
        for field in values:
            values[field].add(meta[field] or "none")
    return values


def apply_stock_meta_filters(
    stocks: pd.DataFrame,
    *,
    stock_meta_payload: dict,
    stock_meta_filters: dict[str, str],
    stock_meta_note_filter: str,
    stock_meta_stock_filter: str,
) -> pd.DataFrame:
    note_filter_lower = stock_meta_note_filter.lower()
    stock_filter_tokens = [
        token.strip().lower()
        for token in stock_meta_stock_filter.replace("，", ",").replace("、", ",").replace(";", ",").replace("；", ",").split(",")
        for token in token.split()
        if token.strip()
    ]

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
        stock_matches = not stock_filter_tokens or any(
            token in symbol_lower or token in symbol_key_lower or token in name_lower or token in summary_lower
            for token in stock_filter_tokens
        )
        return tags_match and note_matches and stock_matches

    return stocks[stocks.apply(stock_matches_meta_filters, axis=1)]
