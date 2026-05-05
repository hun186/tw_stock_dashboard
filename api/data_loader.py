from pathlib import Path

import pandas as pd
import requests

from .constants import INDUSTRY_CODE_NAME, TWSE_LISTED_INFO_API


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


def load_twse_industry_map() -> pd.DataFrame:
    try:
        resp = requests.get(TWSE_LISTED_INFO_API, timeout=10)
        resp.raise_for_status()
        df = pd.DataFrame(resp.json())
    except Exception:
        return pd.DataFrame(columns=["industry", "industry_label", "symbol", "name", "group", "subgroup"])

    if not {"公司代號", "公司簡稱", "產業別"}.issubset(df.columns):
        return pd.DataFrame(columns=["industry", "industry_label", "symbol", "name", "group", "subgroup"])

    df["industry"] = df["產業別"].astype(str).str.strip()
    df["industry_label"] = df["industry"].apply(lambda x: f"{x} - {INDUSTRY_CODE_NAME.get(x, '未分類')}")
    df["symbol"] = df["公司代號"].astype(str).str.strip() + ".TW"
    df["name"] = df["公司簡稱"].astype(str).str.strip()
    df["group"] = "上市-" + df["industry"]
    df["subgroup"] = ""
    return df[df["industry"] != ""][["industry", "industry_label", "symbol", "name", "group", "subgroup"]].drop_duplicates()
