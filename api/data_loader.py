import time
from functools import lru_cache
from pathlib import Path

import pandas as pd
import requests

from .constants import INDUSTRY_CODE_NAME, TPEX_LISTED_INFO_API, TWSE_LISTED_INFO_API


def _empty_watchlist_df() -> pd.DataFrame:
    return pd.DataFrame(columns=["symbol", "name", "group", "subgroup"])


@lru_cache(maxsize=8)
def _load_watchlist_cached(path_text: str, mtime_ns: int) -> pd.DataFrame:
    path = Path(path_text)
    if not path.exists():
        return _empty_watchlist_df()
    df = pd.read_csv(path)
    for col in ["symbol", "name", "group"]:
        if col not in df.columns:
            return _empty_watchlist_df()
    if "subgroup" not in df.columns:
        df["subgroup"] = ""
    for col in ["symbol", "name", "group", "subgroup"]:
        df[col] = df[col].astype(str).str.strip()
    return df[df["symbol"] != ""].copy()


def load_watchlist(path: Path) -> pd.DataFrame:
    mtime_ns = path.stat().st_mtime_ns if path.exists() else 0
    return _load_watchlist_cached(str(path), mtime_ns).copy()


GROUP_COLUMN_ALIASES = {
    "symbol": ["symbol", "股票代號", "代號", "code"],
    "name": ["name", "股票名稱", "公司簡稱", "名稱"],
    "group": ["group", "theme", "題材", "主題材", "產業題材"],
    "subgroup": ["subgroup", "subtheme", "次題材", "子題材", "次產業", "次產業別"],
}


def _normalize_group_map(df: pd.DataFrame) -> pd.DataFrame:
    rename_map = {}
    for target, aliases in GROUP_COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in df.columns:
                rename_map[alias] = target
                break
    df = df.rename(columns=rename_map).copy()

    for col in ["symbol", "name", "group"]:
        if col not in df.columns:
            return _empty_watchlist_df()
    if "subgroup" not in df.columns:
        df["subgroup"] = ""

    for col in ["symbol", "name", "group", "subgroup"]:
        df[col] = df[col].fillna("").astype(str).str.strip()
    df = df[(df["symbol"] != "") & (df["group"] != "")].copy()
    return df[["symbol", "name", "group", "subgroup"]].drop_duplicates(subset=["symbol"], keep="last")


@lru_cache(maxsize=16)
def _load_excel_group_map_cached(path_text: str, sheet_name: str | int, mtime_ns: int) -> pd.DataFrame:
    path = Path(path_text)
    if not path.exists():
        return _empty_watchlist_df()
    try:
        df = pd.read_excel(path, sheet_name=sheet_name)
    except Exception:
        return _empty_watchlist_df()
    return _normalize_group_map(df)


def load_llm_group_map(path: Path, sheet_name: str) -> pd.DataFrame:
    mtime_ns = path.stat().st_mtime_ns if path.exists() else 0
    return _load_excel_group_map_cached(str(path), sheet_name, mtime_ns).copy()


def load_gemini_agent_group_map(path: Path) -> pd.DataFrame:
    mtime_ns = path.stat().st_mtime_ns if path.exists() else 0
    return _load_excel_group_map_cached(str(path), 0, mtime_ns).copy()


def _empty_industry_df() -> pd.DataFrame:
    return pd.DataFrame(columns=["industry", "industry_label", "symbol", "name", "group", "subgroup"])


def _load_exchange_industry_map(api_url: str, symbol_suffix: str, market_prefix: str) -> pd.DataFrame:
    try:
        resp = requests.get(api_url, timeout=10)
        resp.raise_for_status()
        df = pd.DataFrame(resp.json())
    except Exception:
        return _empty_industry_df()

    if not {"公司代號", "公司簡稱", "產業別"}.issubset(df.columns):
        return _empty_industry_df()

    code = df["公司代號"].astype(str).str.strip()
    df["industry"] = df["產業別"].astype(str).str.strip()

    etf_mask = df["industry"].eq("") & code.str.match(r"^00[0-9A-Z]+$", na=False)
    df.loc[etf_mask, "industry"] = "ETF"

    df["industry_label"] = df["industry"].apply(
        lambda x: "ETF - 指數股票型基金" if x == "ETF" else f"{x} - {INDUSTRY_CODE_NAME.get(x, '未分類')}"
    )
    df["symbol"] = code + symbol_suffix
    df["name"] = df["公司簡稱"].astype(str).str.strip()
    df["group"] = market_prefix + "-" + df["industry"]
    df["subgroup"] = ""
    df.loc[df["industry"].eq("ETF"), "subgroup"] = "ETF"
    return df[df["industry"] != ""][["industry", "industry_label", "symbol", "name", "group", "subgroup"]].drop_duplicates()


@lru_cache(maxsize=4)
def _load_twse_industry_map_cached(cache_bucket: int) -> pd.DataFrame:
    twse_df = _load_exchange_industry_map(TWSE_LISTED_INFO_API, ".TW", "上市")
    tpex_df = _load_exchange_industry_map(TPEX_LISTED_INFO_API, ".TWO", "上櫃")
    return pd.concat([twse_df, tpex_df], ignore_index=True).drop_duplicates(subset=["symbol"], keep="last")


def load_twse_industry_map() -> pd.DataFrame:
    cache_bucket = int(time.time() // (60 * 60 * 6))
    return _load_twse_industry_map_cached(cache_bucket).copy()
