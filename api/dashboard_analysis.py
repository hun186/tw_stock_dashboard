from __future__ import annotations

import time

import pandas as pd

from api.market_data import fetch_target_price, get_price_cache_ttl_seconds, trim_display_df
from api.stock_analysis import add_indicators, analyze_stock_signal


STOCK_ANALYSIS_CACHE: dict[tuple[str, str, str, str, str, bool], tuple[float, dict]] = {}


def _analysis_cache_ttl_seconds(fetch_interval: str) -> int:
    return max(get_price_cache_ttl_seconds(fetch_interval), 300)


def build_stock_analysis(
    symbol: str,
    period: str,
    fetch_period: str,
    fetch_interval: str,
    display_period: str,
    price_df: pd.DataFrame,
    signal_df: pd.DataFrame,
    needs_target_price: bool,
) -> dict:
    cache_key = (symbol, period, fetch_period, fetch_interval, display_period, needs_target_price)
    cached = STOCK_ANALYSIS_CACHE.get(cache_key)
    now = time.time()
    if cached and now - cached[0] < _analysis_cache_ttl_seconds(fetch_interval):
        payload = cached[1].copy()
        payload["df"] = cached[1]["df"].copy()
        return payload

    df = price_df.copy()
    raw_signal_df = signal_df.copy() if period == "intraday" else df.copy()
    sort_metrics = {
        "symbol": symbol,
        "close": -1.0,
        "volume": -1.0,
        "change_pct": -999.0,
        "target_ratio": -1.0,
        "signal_score": -999.0,
        "volume_ratio": 0.0,
    }
    target_price_text = "-"
    target_ratio_text = "-"
    if df.empty:
        bucket, status = "watch", "⚪ 抓不到資料"
        close_text = "-"
        signal = {"bucket": bucket, "message": status, "score": -999}
    else:
        df = add_indicators(df)
        df = trim_display_df(df, display_period)
        if raw_signal_df.empty:
            signal = {"bucket": "watch", "message": "⚪ 抓不到形勢判斷資料", "score": -999}
        else:
            raw_signal_df = add_indicators(raw_signal_df)
            signal = analyze_stock_signal(raw_signal_df)
        bucket, status = signal["bucket"], signal["message"]
        close_value = float(df.iloc[-1]["Close"])
        close_text = f"{close_value:.2f}"
        sort_metrics["close"] = close_value
        sort_metrics["volume"] = float(df.iloc[-1]["Volume"]) if "Volume" in df.columns else 0.0
        sort_metrics["volume_ratio"] = (
            float(df.iloc[-1]["volume_ratio"])
            if "volume_ratio" in df.columns and not pd.isna(df.iloc[-1]["volume_ratio"])
            else 0.0
        )
        sort_metrics["signal_score"] = float(signal.get("score", -999))
        intraday_ref_close = float(df.iloc[-1]["RefClose"]) if period == "intraday" and "RefClose" in df.columns else None
        prev_close = float(df.iloc[-2]["Close"]) if len(df) >= 2 else close_value
        reference_close = intraday_ref_close if intraday_ref_close else prev_close
        sort_metrics["change_pct"] = ((close_value - reference_close) / reference_close) * 100 if reference_close else 0.0
        if needs_target_price:
            target_price_text = fetch_target_price(symbol)
            try:
                target_price_value = float(target_price_text)
                if close_value != 0:
                    sort_metrics["target_ratio"] = (target_price_value / close_value) * 100
                    target_ratio_text = f"{sort_metrics['target_ratio']:.1f}%"
            except (TypeError, ValueError):
                target_price_text = "-"
                target_ratio_text = "-"

    payload = {
        "df": df,
        "signal": signal,
        "bucket": signal["bucket"],
        "status": signal["message"],
        "close_text": close_text,
        "sort_metrics": sort_metrics,
        "target_price_text": target_price_text,
        "target_ratio_text": target_ratio_text,
    }
    STOCK_ANALYSIS_CACHE[cache_key] = (now, {**payload, "df": payload["df"].copy()})
    return payload
