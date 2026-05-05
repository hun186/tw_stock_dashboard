from pathlib import Path

import pandas as pd
import requests

from .constants import INDUSTRY_CODE_NAME, TPEX_LISTED_INFO_API, TWSE_LISTED_INFO_API


def load_watchlist(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=["symbol", "name", "group", "subgroup"])
    df = pd.read_csv(path)
    for col in ["symbol", "name", "group"]:
        if col not in df.columns:
            return pd.DataFrame(columns=["symbol", "name", "group", "subgroup"])
    if "subgroup" not in df.columns:
        df["subgroup"] = ""
    for col in ["symbol", "name", "group", "subgroup"]:
        df[col] = df[col].astype(str).str.strip()
    return df[df["symbol"] != ""].copy()


def load_llm_group_map(path: Path, sheet_name: str) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=["symbol", "name", "group", "subgroup"])
    try:
        df = pd.read_excel(path, sheet_name=sheet_name)
    except Exception:
        return pd.DataFrame(columns=["symbol", "name", "group", "subgroup"])
    for col in ["symbol", "name", "group"]:
        if col not in df.columns:
            return pd.DataFrame(columns=["symbol", "name", "group", "subgroup"])
    if "subgroup" not in df.columns:
        df["subgroup"] = ""
    for col in ["symbol", "name", "group", "subgroup"]:
        df[col] = df[col].astype(str).str.strip()
    df = df[df["symbol"] != ""].copy()
    return df[["symbol", "name", "group", "subgroup"]].drop_duplicates(subset=["symbol"], keep="last")


def _load_exchange_industry_map(api_url: str, symbol_suffix: str, market_prefix: str) -> pd.DataFrame:
    try:
        resp = requests.get(api_url, timeout=10)
        resp.raise_for_status()
        df = pd.DataFrame(resp.json())
    except Exception:
        return pd.DataFrame(columns=["industry", "industry_label", "symbol", "name", "group", "subgroup"])

    if not {"公司代號", "公司簡稱", "產業別"}.issubset(df.columns):
        return pd.DataFrame(columns=["industry", "industry_label", "symbol", "name", "group", "subgroup"])

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


def load_twse_industry_map() -> pd.DataFrame:
    twse_df = _load_exchange_industry_map(TWSE_LISTED_INFO_API, ".TW", "上市")
    tpex_df = _load_exchange_industry_map(TPEX_LISTED_INFO_API, ".TWO", "上櫃")
    return pd.concat([twse_df, tpex_df], ignore_index=True).drop_duplicates(subset=["symbol"], keep="last")
