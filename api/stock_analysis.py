from __future__ import annotations

import numpy as np
import pandas as pd


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["MA5"] = df["Close"].rolling(5).mean()
    df["MA20"] = df["Close"].rolling(20).mean()
    df["MA60"] = df["Close"].rolling(60).mean()
    df["VMA5"] = df["Volume"].rolling(5).mean()
    df["VMA20"] = df["Volume"].rolling(20).mean()
    df["VMA60"] = df["Volume"].rolling(60).mean()
    delta = df["Close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    rs = gain.rolling(14).mean() / loss.rolling(14).mean().replace(0, np.nan)
    df["RSI14"] = 100 - (100 / (1 + rs))
    df["vol_ma5"] = df["VMA5"]
    df["vol_ma20"] = df["VMA20"]
    df["high_20"] = df["High"].rolling(20).max()
    df["low_20"] = df["Low"].rolling(20).min()
    df["close_change_pct"] = df["Close"].pct_change() * 100
    safe_vol_ma20 = df["vol_ma20"].replace(0, np.nan)
    df["volume_ratio"] = df["Volume"] / safe_vol_ma20
    safe_ma20 = df["MA20"].replace(0, np.nan)
    safe_ma60 = df["MA60"].replace(0, np.nan)
    df["ma20_distance_pct"] = (df["Close"] - df["MA20"]) / safe_ma20 * 100
    df["ma60_distance_pct"] = (df["Close"] - df["MA60"]) / safe_ma60 * 100
    return df


def analyze_stock_signal(df: pd.DataFrame) -> dict:
    if len(df) < 20:
        return {"emoji": "⚪", "label": "資料不足", "message": "⚪ 資料不足", "code": "INSUFFICIENT_DATA", "score": 0, "risk": "low", "bucket": "watch"}

    last = df.iloc[-1]
    prev = df.iloc[-2]

    close = float(last["Close"])
    open_ = float(last["Open"])
    high = float(last["High"])
    low = float(last["Low"])
    ma20 = float(last["MA20"])
    rsi14 = float(last["RSI14"]) if not pd.isna(last["RSI14"]) else np.nan
    close_change_pct = round(float(last["close_change_pct"]), 1) if not pd.isna(last["close_change_pct"]) else 0.0
    volume_ratio = round(float(last["volume_ratio"]), 1) if not pd.isna(last["volume_ratio"]) else 0.0
    ma20_distance_pct = round(float(last["ma20_distance_pct"]), 1) if not pd.isna(last["ma20_distance_pct"]) else np.nan
    prev_high_20 = float(prev["high_20"]) if not pd.isna(prev["high_20"]) else np.nan
    prev_close = float(prev["Close"])
    prev_ma20 = float(prev["MA20"]) if not pd.isna(prev["MA20"]) else np.nan
    prev_prev_high_20 = float(df.iloc[-3]["high_20"]) if len(df) >= 21 and not pd.isna(df.iloc[-3]["high_20"]) else np.nan
    prev_volume_ratio = float(prev["volume_ratio"]) if not pd.isna(prev["volume_ratio"]) else np.nan
    upper_shadow_ratio = (high - max(open_, close)) / max(high - low, 0.01)

    recent5 = df.tail(5)
    range_5_pct = ((recent5["High"].max() - recent5["Low"].min()) / max(close, 0.01)) * 100
    recent5_avg_vol = recent5["Volume"].mean()
    vol_ma20 = float(last["vol_ma20"]) if not pd.isna(last["vol_ma20"]) else np.nan

    if close_change_pct <= -4 and volume_ratio >= 2.0:
        return {"emoji": "🟢", "label": "放量崩盤", "message": f"🟢 放量崩盤 ({close_change_pct:+.1f}%, 量{volume_ratio:.1f}x)", "code": "VOLUME_CRASH", "score": -90, "risk": "high", "bucket": "bear"}
    if not np.isnan(prev_ma20) and prev_close >= prev_ma20 and close < ma20:
        return {"emoji": "🟢", "label": "跌破 MA20", "message": f"🟢 跌破 MA20 ({close_change_pct:+.1f}%)", "code": "BREAK_MA20", "score": -70, "risk": "high", "bucket": "bear"}
    if volume_ratio >= 2.0 and upper_shadow_ratio >= 0.4 and close < high * 0.97:
        return {"emoji": "🟠", "label": "爆量長上影", "message": f"🟠 爆量長上影，追高風險 (量{volume_ratio:.1f}x)", "code": "UPPER_SHADOW_SELL", "score": -55, "risk": "high", "bucket": "warn"}

    # 假突破：前一日突破 20 日高點，隔日收盤跌回前高下方
    prev_day_broke_out = (
        not np.isnan(prev_prev_high_20)
        and not np.isnan(prev_volume_ratio)
        and prev_close > prev_prev_high_20
        and prev_volume_ratio >= 1.5
    )
    if prev_day_broke_out and (not np.isnan(prev_high_20)) and close <= prev_high_20 and close_change_pct < 0:
        return {"emoji": "⚠️", "label": "假突破", "message": f"⚠️ 假突破：突破後跌回區間 ({close_change_pct:+.1f}%, 量{volume_ratio:.1f}x)", "code": "FALSE_BREAKOUT", "score": -45, "risk": "high", "bucket": "warn"}

    if not np.isnan(prev_high_20) and close > prev_high_20 and volume_ratio >= 1.5 and close > ma20:
        if volume_ratio >= 4.0:
            return {"emoji": "🔥", "label": "爆發突破", "message": f"🔥 爆發突破 20日新高 ({close_change_pct:+.1f}%, 量{volume_ratio:.1f}x)", "code": "BREAKOUT_EXPLOSIVE", "score": 96, "risk": "high", "bucket": "bull"}
        if volume_ratio >= 2.5:
            return {"emoji": "🔴", "label": "強突破", "message": f"🔴 強突破 20日新高 ({close_change_pct:+.1f}%, 量{volume_ratio:.1f}x)", "code": "BREAKOUT_STRONG", "score": 92, "risk": "medium", "bucket": "bull"}
        return {"emoji": "🔴", "label": "小突破", "message": f"🔴 小突破 20日新高 ({close_change_pct:+.1f}%, 量{volume_ratio:.1f}x)", "code": "BREAKOUT_MINOR", "score": 85, "risk": "medium", "bucket": "bull"}
    if close_change_pct >= 3 and volume_ratio >= 1.8 and close > ma20:
        return {"emoji": "🔴", "label": "放量上漲", "message": f"🔴 放量上漲 ({close_change_pct:+.1f}%, 量{volume_ratio:.1f}x)", "code": "VOLUME_UP", "score": 75, "risk": "medium", "bucket": "bull"}
    if low <= ma20 * 1.02 and close >= ma20 and volume_ratio <= 1.2:
        return {"emoji": "🟡", "label": "回測 MA20 不破", "message": f"🟡 回測 MA20 不破 ({close_change_pct:+.1f}%, 量{volume_ratio:.1f}x)", "code": "MA20_SUPPORT", "score": 45, "risk": "medium", "bucket": "observe"}
    if close_change_pct <= -1.5 and volume_ratio <= 0.8 and close > ma20:
        return {"emoji": "🟡", "label": "縮量回檔", "message": f"🟡 縮量回檔 ({close_change_pct:+.1f}%, 量{volume_ratio:.1f}x)", "code": "LOW_VOLUME_PULLBACK", "score": 30, "risk": "low", "bucket": "observe"}
    if (not np.isnan(rsi14) and rsi14 >= 75) or (not np.isnan(ma20_distance_pct) and ma20_distance_pct >= 15):
        rsi_text = f"{round(rsi14,1):.1f}" if not np.isnan(rsi14) else "-"
        return {"emoji": "🟠", "label": "過熱", "message": f"🟠 過熱 (RSI {rsi_text}, 距MA20 {ma20_distance_pct:+.1f}%)", "code": "OVERHEATED", "score": -20, "risk": "medium", "bucket": "warn"}
    if close > ma20 and (not np.isnan(ma20_distance_pct)) and ma20_distance_pct >= 5 and (np.isnan(rsi14) or rsi14 < 75):
        if ma20_distance_pct >= 25:
            return {"emoji": "🔥", "label": "強勢-高風險", "message": f"🔥 強勢乖離過大：高風險 (距MA20 {ma20_distance_pct:+.1f}%)", "code": "STRONG_OVERHEAT_HIGH", "score": 20, "risk": "high", "bucket": "warn"}
        if ma20_distance_pct >= 15:
            return {"emoji": "⚠️", "label": "強勢-過熱邊緣", "message": f"⚠️ 強勢乖離偏高：過熱邊緣 (距MA20 {ma20_distance_pct:+.1f}%)", "code": "STRONG_OVERHEAT_EDGE", "score": 40, "risk": "medium", "bucket": "warn"}
        return {"emoji": "🔴", "label": "強勢", "message": f"🔴 強勢 (距MA20 {ma20_distance_pct:+.1f}%)", "code": "STRONG", "score": 55, "risk": "low", "bucket": "bull"}
    if range_5_pct <= 8 and (not np.isnan(vol_ma20)) and recent5_avg_vol <= vol_ma20 * 0.8:
        return {"emoji": "⚪", "label": "縮量盤整", "message": f"⚪ 縮量盤整 (5日區間 {round(range_5_pct,1):.1f}%)", "code": "CONSOLIDATION", "score": 0, "risk": "low", "bucket": "neutral"}
    return {"emoji": "⚪", "label": "中性", "message": "⚪ 中性", "code": "NEUTRAL", "score": 0, "risk": "low", "bucket": "neutral"}


