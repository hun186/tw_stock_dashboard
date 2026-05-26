import logging
import time
from functools import lru_cache
from pathlib import Path

import pandas as pd
import requests

from .constants import INDUSTRY_CODE_NAME, TPEX_LISTED_INFO_API, TWSE_LISTED_INFO_API


STOCK_GROUP_COLUMNS = ["symbol", "name", "group", "subgroup", "summary", "reference_url"]

logger = logging.getLogger(__name__)
_LAST_GROUP_MAP_WARNINGS: list[str] = []


def _empty_watchlist_df() -> pd.DataFrame:
    return pd.DataFrame(columns=STOCK_GROUP_COLUMNS)


@lru_cache(maxsize=8)
def _load_watchlist_cached(path_text: str, mtime_ns: int) -> pd.DataFrame:
    path = Path(path_text)
    if not path.exists():
        return _empty_watchlist_df()
    df = pd.read_csv(path)
    for col in ["symbol", "name", "group"]:
        if col not in df.columns:
            return _empty_watchlist_df()
    for col in ["subgroup", "summary", "reference_url"]:
        if col not in df.columns:
            df[col] = ""
    for col in STOCK_GROUP_COLUMNS:
        df[col] = df[col].fillna("").astype(str).str.strip()
    return df[df["symbol"] != ""][STOCK_GROUP_COLUMNS].copy()


def load_watchlist(path: Path) -> pd.DataFrame:
    mtime_ns = path.stat().st_mtime_ns if path.exists() else 0
    return _load_watchlist_cached(str(path), mtime_ns).copy()


GROUP_COLUMN_ALIASES = {
    "symbol": ["symbol", "股票代號", "代號", "code"],
    "name": ["name", "股票名稱", "公司簡稱", "名稱"],
    "group": ["group", "theme", "題材", "主題材", "產業題材"],
    "subgroup": ["subgroup", "subtheme", "次題材", "子題材", "次產業", "次產業別"],
    "summary": ["summary", "摘要", "題材摘要"],
    "reference_url": ["reference_url", "url", "來源", "資料來源"],
}


def _normalize_group_map(df: pd.DataFrame) -> pd.DataFrame:
    global _LAST_GROUP_MAP_WARNINGS
    _LAST_GROUP_MAP_WARNINGS = []
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
    for col in ["subgroup", "summary", "reference_url"]:
        if col not in df.columns:
            df[col] = ""

    for col in STOCK_GROUP_COLUMNS:
        df[col] = df[col].fillna("").astype(str).str.strip()
    df = df[(df["symbol"] != "") & (df["group"] != "")].copy()
    return _resolve_conflicting_symbol_names(df[STOCK_GROUP_COLUMNS])


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
    return pd.DataFrame(columns=["industry", "industry_label", *STOCK_GROUP_COLUMNS])


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
    df["summary"] = ""
    df["reference_url"] = ""
    return df[df["industry"] != ""][["industry", "industry_label", *STOCK_GROUP_COLUMNS]].drop_duplicates()


@lru_cache(maxsize=4)
def _load_twse_industry_map_cached(cache_bucket: int) -> pd.DataFrame:
    twse_df = _load_exchange_industry_map(TWSE_LISTED_INFO_API, ".TW", "上市")
    tpex_df = _load_exchange_industry_map(TPEX_LISTED_INFO_API, ".TWO", "上櫃")
    return pd.concat([twse_df, tpex_df], ignore_index=True).drop_duplicates(subset=["symbol"], keep="last")


def load_twse_industry_map() -> pd.DataFrame:
    cache_bucket = int(time.time() // (60 * 60 * 6))
    return _load_twse_industry_map_cached(cache_bucket).copy()


def _resolve_conflicting_symbol_names(df: pd.DataFrame) -> pd.DataFrame:
    conflicts = df.groupby("symbol")["name"].nunique()
    conflict_symbols = conflicts[conflicts > 1].index.tolist()
    if not conflict_symbols:
        return df.drop_duplicates(subset=["symbol"], keep="last")

    official_name_map: dict[str, str] = {}
    try:
        industry_df = load_twse_industry_map()
        if not industry_df.empty and {"symbol", "name"}.issubset(industry_df.columns):
            official_name_map = (
                industry_df[["symbol", "name"]]
                .dropna()
                .assign(symbol=lambda d: d["symbol"].astype(str).str.strip(), name=lambda d: d["name"].astype(str).str.strip())
                .drop_duplicates(subset=["symbol"], keep="last")
                .set_index("symbol")["name"]
                .to_dict()
            )
    except Exception:
        logger.exception("載入上市櫃公司名稱對照失敗，將以原始資料去重")

    parts: list[pd.DataFrame] = []
    for symbol, group in df.groupby("symbol", sort=False):
        if symbol not in conflict_symbols:
            parts.append(group.tail(1))
            continue

        official_name = official_name_map.get(symbol, "")
        if official_name:
            matched = group[group["name"] == official_name]
            if not matched.empty:
                parts.append(matched.tail(1))
                warning = f"偵測到代號 {symbol} 出現多個名稱，已保留與官方名稱一致資料：{official_name}"
                _LAST_GROUP_MAP_WARNINGS.append(warning)
                logger.warning("%s", warning)
                continue

        parts.append(group.tail(1))
        warning = (
            f"偵測到代號 {symbol} 出現多個名稱（{', '.join(group["name"].tolist())}），"
            "但找不到可驗證官方名稱，暫時保留最後一筆"
        )
        _LAST_GROUP_MAP_WARNINGS.append(warning)
        logger.warning("%s", warning)

    resolved = pd.concat(parts, ignore_index=True)
    return resolved.drop_duplicates(subset=["symbol"], keep="last")


def get_last_group_map_warnings() -> list[str]:
    return list(_LAST_GROUP_MAP_WARNINGS)
