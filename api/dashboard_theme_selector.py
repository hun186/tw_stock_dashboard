from __future__ import annotations

import html
import math
from typing import Iterable

import pandas as pd

SIGNAL_BUCKET_LABELS = {
    "all": "全部訊號分類",
    "bull": "偏多",
    "observe": "觀察",
    "warn": "警示",
    "bear": "轉弱",
    "neutral": "中性",
    "watch": "資料不足 / 觀察",
}

VOLUME_RATIO_OPTIONS = {
    "all": "不限量能",
    "1.5": "成交量 ≥ 20日均量 1.5x",
    "2": "成交量 ≥ 20日均量 2x",
    "4": "成交量 ≥ 20日均量 4x",
}


def normalize_summary_keyword(value: str | None) -> str:
    return (value or "").strip()


def normalize_signal_bucket(value: str | None) -> str:
    return value if value in SIGNAL_BUCKET_LABELS else "all"


def normalize_signal_code(value: str | None, valid_codes: Iterable[str] | None = None) -> str:
    value = (value or "all").strip()
    if not value or value == "all":
        return "all"
    if valid_codes is not None and value not in set(valid_codes):
        return "all"
    return value


def normalize_volume_ratio(value: str | None) -> str:
    return value if value in VOLUME_RATIO_OPTIONS else "all"


def volume_ratio_threshold(value: str) -> float | None:
    if value == "all":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def filter_stocks_by_summary_keyword(stocks: pd.DataFrame, summary_keyword: str) -> pd.DataFrame:
    keyword = normalize_summary_keyword(summary_keyword)
    if not keyword or "summary" not in stocks.columns:
        return stocks
    summary = stocks["summary"].fillna("").astype(str)
    return stocks[summary.str.contains(keyword, case=False, na=False, regex=False)]


def latest_volume_ratio_from_df(df: pd.DataFrame) -> float:
    if df.empty or "volume_ratio" not in df.columns:
        return 0.0
    value = df.iloc[-1].get("volume_ratio", 0.0)
    try:
        ratio = float(value)
    except (TypeError, ValueError):
        return 0.0
    return 0.0 if math.isnan(ratio) else ratio


def signal_code(item: dict) -> str:
    signal = item.get("signal", {})
    return str(signal.get("code", "")) if isinstance(signal, dict) else ""


def signal_label(item: dict) -> str:
    signal = item.get("signal", {})
    if not isinstance(signal, dict):
        return signal_code(item)
    label = str(signal.get("label", "") or "")
    code = signal_code(item)
    return f"{label} ({code})" if label and code else code or label


def collect_signal_code_options(analyzed_stocks: list[dict]) -> list[tuple[str, str]]:
    options: dict[str, str] = {}
    for item in analyzed_stocks:
        code = signal_code(item)
        if code:
            options[code] = signal_label(item)
    return sorted(options.items(), key=lambda pair: pair[1])


def filter_analyzed_stocks(
    analyzed_stocks: list[dict],
    *,
    status_filter: str,
    signal_bucket_filter: str,
    signal_code_filter: str,
    volume_ratio_filter: str,
) -> list[dict]:
    bucket_filter = normalize_signal_bucket(signal_bucket_filter)
    code_filter = normalize_signal_code(signal_code_filter)
    threshold = volume_ratio_threshold(normalize_volume_ratio(volume_ratio_filter))

    filtered = []
    for item in analyzed_stocks:
        if status_filter != "all" and item.get("bucket") != status_filter:
            continue
        if bucket_filter != "all" and item.get("bucket") != bucket_filter:
            continue
        if code_filter != "all" and signal_code(item) != code_filter:
            continue
        volume_ratio = float(item.get("sort_metrics", {}).get("volume_ratio", 0.0) or 0.0)
        if threshold is not None and volume_ratio < threshold:
            continue
        filtered.append(item)
    return filtered


def render_signal_bucket_options(selected_bucket: str, available_buckets: Iterable[str] | None = None) -> str:
    selected_bucket = normalize_signal_bucket(selected_bucket)
    available = set(available_buckets or [])
    if available and selected_bucket not in available:
        selected_bucket = "all"
    values = [
        (value, label)
        for value, label in SIGNAL_BUCKET_LABELS.items()
        if value == "all" or not available or value in available
    ]
    return "".join(
        f"<option value='{html.escape(value)}' {'selected' if value == selected_bucket else ''}>{html.escape(label)}</option>"
        for value, label in values
    )


def render_signal_code_options(options: list[tuple[str, str]], selected_code: str) -> str:
    valid_codes = {code for code, _label in options}
    selected_code = normalize_signal_code(selected_code, valid_codes)
    rendered = [f"<option value='all' {'selected' if selected_code == 'all' else ''}>全部技術訊號</option>"]
    rendered.extend(
        f"<option value='{html.escape(code)}' {'selected' if code == selected_code else ''}>{html.escape(label)}</option>"
        for code, label in options
    )
    return "".join(rendered)


def render_volume_ratio_options(selected_ratio: str, available_ratios: Iterable[str] | None = None) -> str:
    selected_ratio = normalize_volume_ratio(selected_ratio)
    available = set(available_ratios or [])
    if available and selected_ratio not in available:
        selected_ratio = "all"
    values = [
        (value, label)
        for value, label in VOLUME_RATIO_OPTIONS.items()
        if value == "all" or not available or value in available
    ]
    return "".join(
        f"<option value='{html.escape(value)}' {'selected' if value == selected_ratio else ''}>{html.escape(label)}</option>"
        for value, label in values
    )
