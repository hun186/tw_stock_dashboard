from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from api.dashboard_stock_groups import (
    ensure_stock_group_columns,
    merge_stock_group_sources,
    sort_stocks_by_symbol,
    stock_code_sort_value,
    stock_group_frame,
)
from api.dashboard_stock_meta import (
    apply_stock_meta_filters,
    normalize_stock_meta_entry,
    stock_filter_tokens,
    stock_meta_filter_values,
)
from api.data_loader import STOCK_GROUP_COLUMNS
from api.market_data import _symbol_key


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
        .drop_duplicates(subset=["symbol_key"], keep="last")
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
        if industry == "all":
            source_stocks = all_stocks[STOCK_GROUP_COLUMNS].copy()
        else:
            source_stocks = industry_df[industry_df["industry"] == industry][STOCK_GROUP_COLUMNS].copy()
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


__all__ = [
    "StockPoolResult",
    "apply_stock_meta_filters",
    "build_stock_pool",
    "ensure_stock_group_columns",
    "merge_stock_group_sources",
    "normalize_stock_meta_entry",
    "sort_stocks_by_symbol",
    "stock_code_sort_value",
    "stock_filter_tokens",
    "stock_group_frame",
    "stock_meta_filter_values",
]
