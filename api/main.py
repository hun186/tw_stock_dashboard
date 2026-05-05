from __future__ import annotations

import html
import json
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import parse_qs

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import yfinance as yf

APP_DIR = Path(__file__).resolve().parent.parent
WATCHLIST_FILE = APP_DIR / "watchlist.csv"
TWSE_LISTED_INFO_API = "https://openapi.twse.com.tw/v1/opendata/t187ap03_L"

UP_COLOR = "#d60000"
DOWN_COLOR = "#008a00"
MA5_COLOR = "#ffd400"
MA20_COLOR = "#8a2be2"
MA60_COLOR = "#6ec6ff"

INDUSTRY_CODE_NAME = {
    "01": "水泥工業", "02": "食品工業", "03": "塑膠工業", "04": "紡織纖維", "05": "電機機械",
    "06": "電器電纜", "08": "玻璃陶瓷", "09": "造紙工業", "10": "鋼鐵工業", "11": "橡膠工業",
    "12": "汽車工業", "14": "建材營造", "15": "航運業", "16": "觀光餐旅", "17": "金融保險",
    "18": "貿易百貨", "20": "其他", "21": "化學工業", "22": "生技醫療", "23": "油電燃氣",
    "24": "半導體業", "25": "電腦及週邊", "26": "光電業", "27": "通信網路", "28": "電子零組件",
    "29": "電子通路", "30": "資訊服務", "31": "其他電子", "32": "文化創意", "33": "農業科技",
    "34": "電子商務", "35": "綠能環保", "36": "數位雲端", "37": "運動休閒", "38": "居家生活",
    "80": "管理股票",
}

STATUS_FILTERS = {
    "all": "全部",
    "watch": "⚪ 資料不足",
    "bull": "🔴 偏多",
    "observe": "🟡 觀察",
    "warn": "🟠 風險",
    "bear": "🟢 轉弱",
    "neutral": "⚪ 中性",
}


def load_watchlist(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=["symbol", "name", "group", "subgroup"])
    df = pd.read_csv(path)
    for col in ["symbol", "name", "group"]:
        if col not in df.columns:
            return pd.DataFrame(columns=["symbol", "name", "group", "subgroup"])
    if "subgroup" not in df.columns:
        df["subgroup"] = ""
    df["symbol"] = df["symbol"].astype(str).str.strip()
    df["name"] = df["name"].astype(str).str.strip()
    df["group"] = df["group"].astype(str).str.strip()
    df["subgroup"] = df["subgroup"].astype(str).str.strip()
    return df[df["symbol"] != ""].copy()


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


PRICE_CACHE: dict[tuple[str, str, str], tuple[float, pd.DataFrame]] = {}


def _cache_ttl_seconds(interval: str) -> int:
    if interval == "1m":
        return 20
    if interval.endswith("m"):
        return 60
    return 300


def fetch_price(symbol: str, period: str = "3mo", interval: str = "1d") -> pd.DataFrame:
    cache_key = (symbol, period, interval)
    now = time.time()
    cache_ttl = _cache_ttl_seconds(interval)
    cached = PRICE_CACHE.get(cache_key)
    if cached and now - cached[0] < cache_ttl:
        return cached[1].copy()

    df = yf.download(symbol, period=period, interval=interval, auto_adjust=False, progress=False, threads=False)
    if df is None or df.empty:
        return pd.DataFrame()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.rename_axis("Date").reset_index()
    need = ["Date", "Open", "High", "Low", "Close", "Volume"]
    if not set(need).issubset(df.columns):
        return pd.DataFrame()
    df = df[need].dropna(subset=["Close"])
    if interval.endswith("m"):
        date_col = pd.to_datetime(df["Date"], errors="coerce")
        if getattr(date_col.dt, "tz", None) is None:
            source_tz = "Asia/Taipei" if symbol.endswith((".TW", ".TWO")) else "UTC"
            date_col = date_col.dt.tz_localize(source_tz)
        date_col = date_col.dt.tz_convert("Asia/Taipei")
        df["Date"] = date_col.dt.tz_localize(None)
        intraday_mask = (df["Date"].dt.time >= pd.Timestamp("09:00").time()) & (df["Date"].dt.time <= pd.Timestamp("13:30").time())
        df = df[intraday_mask].copy()
        if not df.empty:
            trade_dates = df["Date"].dt.date
            latest_date = trade_dates.max()
            prev_day_close = df.loc[trade_dates < latest_date, "Close"].dropna()
            reference_close = float(prev_day_close.iloc[-1]) if not prev_day_close.empty else float(df.iloc[0]["Open"])
            df = df[trade_dates == latest_date].copy()
            df["RefClose"] = reference_close
    PRICE_CACHE[cache_key] = (now, df.copy())
    return df


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
    if not np.isnan(prev_high_20) and close > prev_high_20 and volume_ratio >= 1.5 and close > ma20:
        return {"emoji": "🔴", "label": "放量突破", "message": f"🔴 放量突破 20日新高 ({close_change_pct:+.1f}%, 量{volume_ratio:.1f}x)", "code": "BREAKOUT", "score": 90, "risk": "medium", "bucket": "bull"}
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
        return {"emoji": "🔴", "label": "強勢", "message": f"🔴 強勢 (距MA20 {ma20_distance_pct:+.1f}%)", "code": "STRONG", "score": 55, "risk": "low", "bucket": "bull"}
    if range_5_pct <= 8 and (not np.isnan(vol_ma20)) and recent5_avg_vol <= vol_ma20 * 0.8:
        return {"emoji": "⚪", "label": "縮量盤整", "message": f"⚪ 縮量盤整 (5日區間 {round(range_5_pct,1):.1f}%)", "code": "CONSOLIDATION", "score": 0, "risk": "low", "bucket": "neutral"}
    return {"emoji": "⚪", "label": "中性", "message": "⚪ 中性", "code": "NEUTRAL", "score": 0, "risk": "low", "bucket": "neutral"}


def make_chart_html(df: pd.DataFrame, title: str, show_volume: bool, show_ma: bool, intraday_ref_close: float | None = None) -> str:
    row_heights = [0.7, 0.3] if show_volume else [1.0]
    fig = make_subplots(rows=2 if show_volume else 1, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=row_heights)
    price_open = df["Open"] if intraday_ref_close is None else np.full(len(df), intraday_ref_close)
    fig.add_trace(go.Candlestick(
        x=df["Date"], open=price_open, high=df["High"], low=df["Low"], close=df["Close"], name="價格K線",
        increasing_line_color=UP_COLOR, decreasing_line_color=DOWN_COLOR,
        increasing_fillcolor=UP_COLOR, decreasing_fillcolor=DOWN_COLOR,
        increasing=dict(line=dict(color=UP_COLOR), fillcolor=UP_COLOR),
        decreasing=dict(line=dict(color=DOWN_COLOR), fillcolor=DOWN_COLOR),
    ), row=1, col=1)
    if show_ma:
        fig.add_trace(go.Scatter(x=df["Date"], y=df["MA5"], mode="lines", name="MA5", line=dict(color=MA5_COLOR)), row=1, col=1)
        fig.add_trace(go.Scatter(x=df["Date"], y=df["MA20"], mode="lines", name="MA20", line=dict(color=MA20_COLOR)), row=1, col=1)
        fig.add_trace(go.Scatter(x=df["Date"], y=df["MA60"], mode="lines", name="MA60", line=dict(color=MA60_COLOR)), row=1, col=1)

    if show_volume:
        ref_series = df["RefClose"] if "RefClose" in df.columns else df["Open"]
        volume_colors = np.where(df["Close"] >= ref_series, UP_COLOR, DOWN_COLOR)
        fig.add_trace(go.Bar(x=df["Date"], y=df["Volume"], name="量K線", marker_color=volume_colors, opacity=0.8), row=2, col=1)
        if show_ma:
            fig.add_trace(go.Scatter(x=df["Date"], y=df["VMA5"], mode="lines", name="VMA5", line=dict(color=MA5_COLOR)), row=2, col=1)
            fig.add_trace(go.Scatter(x=df["Date"], y=df["VMA20"], mode="lines", name="VMA20", line=dict(color=MA20_COLOR)), row=2, col=1)
            fig.add_trace(go.Scatter(x=df["Date"], y=df["VMA60"], mode="lines", name="VMA60", line=dict(color=MA60_COLOR)), row=2, col=1)
        fig.update_yaxes(title_text="價格", row=1, col=1)
        fig.update_yaxes(title_text="成交量", row=2, col=1)

    if intraday_ref_close is not None:
        ref_close = float(intraday_ref_close)
        limit_up = ref_close * 1.1
        limit_down = ref_close * 0.9
        session_date = pd.to_datetime(df["Date"]).max().normalize()
        session_start = session_date + pd.Timedelta(hours=9)
        session_end = session_date + pd.Timedelta(hours=13, minutes=30)
        fig.update_xaxes(range=[session_start, session_end], row=1, col=1)
        if show_volume:
            fig.update_xaxes(range=[session_start, session_end], row=2, col=1)
        fig.update_yaxes(range=[limit_down, limit_up], row=1, col=1)
        fig.update_yaxes(
            tickmode="array",
            tickvals=[limit_down, ref_close, limit_up],
            ticktext=[f"跌停 {limit_down:.2f}", f"昨收 {ref_close:.2f}", f"漲停 {limit_up:.2f}"],
            row=1,
            col=1,
        )
        fig.add_hline(y=ref_close, line_color="#666", line_width=1, line_dash="dot", row=1, col=1)

    fig.update_layout(title=title, height=500 if show_volume else 320, margin=dict(l=4, r=4, t=36, b=4), xaxis_rangeslider_visible=False)
    return fig.to_html(full_html=False, include_plotlyjs="cdn")




def resolve_price_params(period: str, interval: str) -> tuple[str, str, str]:
    if period == "intraday":
        return "2d", "1m", period

    ma_warmup_period_map = {
        "1mo": "6mo",
        "2mo": "6mo",
        "3mo": "6mo",
        "6mo": "1y",
        "1y": "2y",
        "5y": "max",
    }
    fetch_period = ma_warmup_period_map.get(period, period)
    return fetch_period, interval, period




def prefetch_price_data(stocks: pd.DataFrame, period: str, interval: str) -> dict[str, pd.DataFrame]:
    symbols = [s for s in stocks["symbol"].dropna().astype(str).tolist() if s]
    if not symbols:
        return {}

    max_workers = min(8, len(symbols))
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = executor.map(lambda sym: (sym, fetch_price(sym, period, interval)), symbols)
        return {symbol: df for symbol, df in results}

def trim_display_df(df: pd.DataFrame, display_period: str) -> pd.DataFrame:
    if df.empty or display_period in {"intraday", "max"}:
        return df

    period_days = {
        "1mo": 31,
        "2mo": 62,
        "3mo": 93,
        "6mo": 186,
        "1y": 366,
        "2y": 732,
        "5y": 1828,
    }
    days = period_days.get(display_period)
    if days is None:
        return df

    end_date = pd.to_datetime(df["Date"]).max()
    start_date = end_date - pd.Timedelta(days=days)
    trimmed = df[pd.to_datetime(df["Date"]) >= start_date].copy()
    return trimmed if not trimmed.empty else df


def app(environ, start_response):
    params = parse_qs(environ.get("QUERY_STRING", ""))
    tab = params.get("tab", ["watchlist"])[0]
    period = params.get("period", ["3mo"])[0]
    interval = params.get("interval", ["1d"])[0]
    limit = int(params.get("limit", ["30"])[0])
    status_filter = params.get("status_filter", ["all"])[0]
    group_filter = params.get("group_filter", ["all"])[0]
    subgroup_filter = params.get("subgroup_filter", ["all"])[0]
    cards_per_row = int(params.get("cards_per_row", ["3"])[0])
    cards_per_row = cards_per_row if cards_per_row in [1, 2, 3, 4] else 3
    custom_watchlist_raw = params.get("custom_watchlist", [""])[0]
    show_volume = params.get("show_volume", ["1"])[0] == "1"
    fetch_period, fetch_interval, display_period = resolve_price_params(period, interval)

    base_watchlist = load_watchlist(WATCHLIST_FILE)
    industry_df = load_twse_industry_map()
    industries = industry_df[["industry", "industry_label"]].drop_duplicates().sort_values("industry")
    industry = params.get("industry", [industries.iloc[0]["industry"] if not industries.empty else ""])[0]

    all_stocks = pd.concat([
        base_watchlist[["symbol", "name", "group", "subgroup"]],
        industry_df[["symbol", "name", "group", "subgroup"]]
    ], ignore_index=True).drop_duplicates(subset=["symbol"])

    custom_symbols = [x.strip() for x in custom_watchlist_raw.split(",") if x.strip()]
    custom_df = all_stocks[all_stocks["symbol"].isin(custom_symbols)][["symbol", "name", "group", "subgroup"]]
    missing_symbols = [x for x in custom_symbols if x not in set(custom_df["symbol"]) ]
    if missing_symbols:
        custom_df = pd.concat([
            custom_df,
            pd.DataFrame([{"symbol": s, "name": s, "group": "自訂", "subgroup": ""} for s in missing_symbols])
        ], ignore_index=True)
    watchlist = custom_df if not custom_df.empty else base_watchlist

    if tab == "category" and industry:
        source_stocks = industry_df[industry_df["industry"] == industry][["symbol", "name", "group", "subgroup"]]
    else:
        source_stocks = watchlist[["symbol", "name", "group", "subgroup"]]

    valid_groups = sorted([g for g in source_stocks["group"].dropna().astype(str).str.strip().unique() if g])
    if group_filter != "all" and group_filter not in valid_groups:
        group_filter = "all"
    subgroup_source = source_stocks if group_filter == "all" else source_stocks[source_stocks["group"] == group_filter]
    valid_subgroups = sorted([g for g in subgroup_source["subgroup"].dropna().astype(str).str.strip().unique() if g])
    if subgroup_filter != "all" and subgroup_filter not in valid_subgroups:
        subgroup_filter = "all"

    stocks = source_stocks.copy()
    if group_filter != "all":
        stocks = stocks[stocks["group"] == group_filter]
    if subgroup_filter != "all":
        stocks = stocks[stocks["subgroup"] == subgroup_filter]
    stocks = stocks.head(limit)

    rows_data = []
    cards = []
    price_data_map = prefetch_price_data(stocks, fetch_period, fetch_interval)
    signal_data_map = prefetch_price_data(stocks, "6mo", "1d") if period == "intraday" else {}

    for row in stocks.itertuples(index=False):
        df = price_data_map.get(row.symbol, pd.DataFrame()).copy()
        signal_df = signal_data_map.get(row.symbol, pd.DataFrame()).copy() if period == "intraday" else df.copy()
        if df.empty:
            bucket, status = "watch", "⚪ 抓不到資料"
            close_text = "-"
            signal = {"score": -999}
        else:
            df = add_indicators(df)
            df = trim_display_df(df, display_period)
            if signal_df.empty:
                signal = {"bucket": "watch", "message": "⚪ 抓不到判斷資料", "score": -999}
            else:
                signal_df = add_indicators(signal_df)
                signal = analyze_stock_signal(signal_df)
            bucket, status = signal["bucket"], signal["message"]
            close_text = f"{float(df.iloc[-1]['Close']):.2f}"

        if status_filter != "all" and bucket != status_filter:
            continue

        action_btn = (
            f"<button type='button' onclick=\"removeWatchlistStock('{html.escape(row.symbol)}')\">移出自選</button>"
            if tab == "watchlist"
            else f"<button type='button' onclick=\"addWatchlistStock('{html.escape(row.symbol)}')\">加入自選</button>"
        )
        subgroup_text = row.subgroup if isinstance(row.subgroup, str) and row.subgroup else "-"
        rows_data.append({"score": signal["score"] if not df.empty else -999, "row_html": f"<tr><td>{html.escape(status.split()[0])}</td><td>{html.escape(row.symbol)}</td><td>{html.escape(row.name)}</td><td>{html.escape(row.group)}</td><td>{html.escape(subgroup_text)}</td><td>{html.escape(status)}</td><td>{close_text}</td><td>{action_btn}</td></tr>"})
        if not df.empty:
            show_ma = period != "intraday"
            intraday_ref_close = float(df.iloc[-1]["RefClose"]) if show_ma is False and "RefClose" in df.columns else None
            prev_close = float(df.iloc[-2]["Close"]) if len(df) >= 2 else float(df.iloc[-1]["Close"])
            now_close = float(df.iloc[-1]["Close"])
            reference_close = intraday_ref_close if period == "intraday" and intraday_ref_close else prev_close
            close_color = UP_COLOR if now_close >= reference_close else DOWN_COLOR
            if period == "intraday" and reference_close != 0:
                change_pct = ((now_close - reference_close) / reference_close) * 100
                change_text = f" ({change_pct:+.2f}%)"
            else:
                change_text = ""
            cards.append(
                f"<h3>{html.escape(row.name)} ({html.escape(row.symbol)}) 收盤 "
                f"<span style='color:{close_color};font-weight:700'>{close_text}{change_text}</span></h3>"
                f"{make_chart_html(df, row.name, show_volume, show_ma, intraday_ref_close=intraday_ref_close)}"
            )

    rows_data.sort(key=lambda x: x["score"], reverse=True)
    rows = [x["row_html"] for x in rows_data]

    industry_options = "".join([
        f"<option value='{html.escape(r.industry)}' {'selected' if r.industry == industry else ''}>{html.escape(r.industry_label)}</option>"
        for r in industries.itertuples(index=False)
    ])
    status_options = "".join([
        f"<option value='{k}' {'selected' if k == status_filter else ''}>{v}</option>" for k, v in STATUS_FILTERS.items()
    ])
    group_options = "<option value='all'>全部主題</option>" + "".join([
        f"<option value='{html.escape(v)}' {'selected' if v == group_filter else ''}>{html.escape(v)}</option>" for v in valid_groups
    ])
    subgroup_options = "<option value='all'>全部次題材</option>" + "".join([
        f"<option value='{html.escape(v)}' {'selected' if v == subgroup_filter else ''}>{html.escape(v)}</option>" for v in valid_subgroups
    ])

    save_payload = {
        "tab": tab,
        "industry": industry,
        "period": period,
        "interval": interval,
        "limit": limit,
        "status_filter": status_filter,
        "group_filter": group_filter,
        "subgroup_filter": subgroup_filter,
        "cards_per_row": cards_per_row,
        "custom_watchlist": ",".join(watchlist["symbol"].tolist()),
        "show_volume": "1" if show_volume else "0",
    }

    body = f"""<!doctype html><html lang='zh-Hant'><head><meta charset='utf-8'><title>TW Dashboard</title>
    <style>
      body{{font-family:Arial;margin:16px;line-height:1.35}}
      h1{{font-size:1.35rem;margin:0 0 10px}}
      h2{{font-size:1.1rem;margin:12px 0 8px}}
      form{{display:flex;flex-wrap:wrap;gap:6px 8px;align-items:center}}
      label{{font-size:.9rem;color:#333}}
      input,select,button{{font-size:.9rem;padding:4px 6px}}
      table{{border-collapse:collapse;width:100%;font-size:.88rem}}
      td,th{{border:1px solid #ddd;padding:5px;white-space:nowrap}}
      .table-wrap{{overflow-x:auto}}
      .card{{margin:8px 0;padding:8px;border:1px solid #ddd;border-radius:8px}}
      .card h3{{font-size:.95rem;margin:4px 0 6px}}
      @media (max-width: 900px){{ body{{margin:10px}} }}
      @media (max-width: 720px){{
        form{{gap:4px 6px}}
        input,select,button{{font-size:.82rem;padding:3px 5px}}
        label{{font-size:.8rem}}
        table{{font-size:.8rem}}
      }}
    </style></head><body>
    <h1>多台股監控 Dashboard（Vercel 版）</h1>
    <form id='cfgForm'>
    <label>頁籤</label><select name='tab'><option value='watchlist' {'selected' if tab=='watchlist' else ''}>自選股監控</option><option value='category' {'selected' if tab=='category' else ''}>分類股池</option></select>
    <label>產業</label><select name='industry'>{industry_options}</select>
    <label>期間</label><select name='period'><option value='intraday' {'selected' if period=='intraday' else ''}>當日即時K</option><option value='1mo' {'selected' if period=='1mo' else ''}>1個月</option><option value='2mo' {'selected' if period=='2mo' else ''}>2個月</option><option value='3mo' {'selected' if period=='3mo' else ''}>3個月</option><option value='6mo' {'selected' if period=='6mo' else ''}>6個月</option><option value='1y' {'selected' if period=='1y' else ''}>1年</option><option value='5y' {'selected' if period=='5y' else ''}>5年</option></select>
    <label>週期</label><select name='interval'><option value='1m' {'selected' if interval=='1m' else ''}>1 分鐘</option><option value='5m' {'selected' if interval=='5m' else ''}>5 分鐘</option><option value='15m' {'selected' if interval=='15m' else ''}>15 分鐘</option><option value='1d' {'selected' if interval=='1d' else ''}>日線</option><option value='1wk' {'selected' if interval=='1wk' else ''}>週線</option></select>
    <label>檔數</label><input name='limit' value='{limit}' size='3'/>
    <label>主題</label><select name='group_filter'>{group_options}</select>
    <label>次題材</label><select name='subgroup_filter'>{subgroup_options}</select>
    <label>判斷篩選</label><select name='status_filter'>{status_options}</select>
    <label>每列檔數</label><select name='cards_per_row'><option value='1' {'selected' if cards_per_row==1 else ''}>1</option><option value='2' {'selected' if cards_per_row==2 else ''}>2</option><option value='3' {'selected' if cards_per_row==3 else ''}>3</option><option value='4' {'selected' if cards_per_row==4 else ''}>4</option></select>
    <label>顯示量K線</label><select name='show_volume'><option value='1' {'selected' if show_volume else ''}>開啟</option><option value='0' {'selected' if not show_volume else ''}>關閉</option></select>
    <button type='submit'>更新</button>
    <button type='button' onclick='saveLocal()'>存到瀏覽器</button>
    <button type='button' onclick='loadLocal()'>讀取瀏覽器設定</button>
    <button type='button' onclick='exportBrowserMemory()'>匯出瀏覽器記憶</button>
    <input type='file' id='memoryFile' accept='application/json' style='display:none' onchange='importBrowserMemory(event)'>
    <button type='button' onclick="document.getElementById('memoryFile').click()">匯入瀏覽器記憶</button>
    <button type='button' onclick='downloadConfig()'>下載設定檔</button>
    <input type='file' id='cfgFile' accept='application/json' style='display:none' onchange='importConfig(event)'>
    <button type='button' onclick="document.getElementById('cfgFile').click()">匯入設定檔</button>
    <hr>
    <label>關鍵字</label><input id='watchKeyword' placeholder='輸入名稱或代號'>
    <label>加入自選</label><select id='stockPicker'></select>
    <button type='button' onclick='addSelectedStock()'>加入</button>
    <input type='hidden' name='custom_watchlist' id='customWatchlist' value='{html.escape(','.join(watchlist['symbol'].tolist()))}'>
    </form>
    <h2>總覽</h2><div class='table-wrap'><table><tr><th>狀態</th><th>代號</th><th>名稱</th><th>主題分類</th><th>次題材</th><th>判斷</th><th>收盤</th><th>互動</th></tr>{''.join(rows) if rows else '<tr><td colspan="8">無符合條件資料</td></tr>'}</table></div>
    <h2>多股趨勢圖</h2><div id='cardsGrid' style='display:grid;grid-template-columns:repeat({cards_per_row}, minmax(0,1fr));gap:8px'>{''.join([f"<div class='card'>{c}</div>" for c in cards])}</div>
    <script>
    const defaultConfig = {json.dumps(save_payload, ensure_ascii=False)};
    const autoRefreshMs = 20000;
    const isIntradayMode = defaultConfig.period === 'intraday';
    function serializeForm(){{
      const fd = new FormData(document.getElementById('cfgForm'));
      return Object.fromEntries(fd.entries());
    }}
    function applyConfig(cfg){{
      const form = document.getElementById('cfgForm');
      Object.entries(cfg).forEach(([k,v])=>{{ if(form.elements[k]) form.elements[k].value = v; }});
      form.submit();
    }}
    function saveLocal(){{
      localStorage.setItem('tw_dashboard_config', JSON.stringify(serializeForm()));
      alert('設定已存到瀏覽器');
    }}
    function loadLocal(){{
      const raw = localStorage.getItem('tw_dashboard_config');
      if(!raw) return alert('找不到瀏覽器設定');
      try {{ applyConfig(JSON.parse(raw)); }} catch(e) {{ alert('設定格式錯誤'); }}
    }}
    function exportBrowserMemory(){{
      const raw = localStorage.getItem('tw_dashboard_config');
      if(!raw) return alert('找不到可匯出的瀏覽器記憶');
      const payload = {{
        key: 'tw_dashboard_config',
        exported_at: new Date().toISOString(),
        data: JSON.parse(raw),
      }};
      const blob = new Blob([JSON.stringify(payload, null, 2)], {{type: 'application/json'}});
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = 'tw-dashboard-browser-memory.json';
      a.click();
      URL.revokeObjectURL(a.href);
    }}
    function importBrowserMemory(evt){{
      const file = evt.target.files[0];
      if(!file) return;
      const reader = new FileReader();
      reader.onload = () => {{
        try {{
          const payload = JSON.parse(reader.result);
          const cfg = payload?.data ?? payload;
          if(typeof cfg !== 'object' || cfg === null) throw new Error('invalid');
          localStorage.setItem('tw_dashboard_config', JSON.stringify(cfg));
          applyConfig(cfg);
        }} catch(e) {{
          alert('匯入失敗：瀏覽器記憶格式錯誤');
        }}
      }};
      reader.readAsText(file);
      evt.target.value = '';
    }}

    const allStocks = {json.dumps(all_stocks[['symbol', 'name', 'group']].to_dict(orient='records'), ensure_ascii=False)};
    function getWatchlistSymbols(){{
      const raw = document.getElementById('customWatchlist').value.trim();
      return raw ? raw.split(',').map(x=>x.trim()).filter(Boolean) : [];
    }}
    function setWatchlistSymbols(symbols){{
      document.getElementById('customWatchlist').value = [...new Set(symbols)].join(',');
    }}
    function addWatchlistStock(symbol){{
      const symbols = getWatchlistSymbols();
      if(!symbols.includes(symbol)) symbols.push(symbol);
      setWatchlistSymbols(symbols);
      document.getElementById('cfgForm').submit();
    }}
    function removeWatchlistStock(symbol){{
      const symbols = getWatchlistSymbols().filter(s => s !== symbol);
      setWatchlistSymbols(symbols);
      document.getElementById('cfgForm').submit();
    }}
    function fillStockPicker(keyword=''){{
      const picker = document.getElementById('stockPicker');
      const kw = keyword.trim().toLowerCase();
      const rows = allStocks.filter(r => !kw || r.symbol.toLowerCase().includes(kw) || r.name.toLowerCase().includes(kw));
      picker.innerHTML = rows.slice(0, 200).map(r => `<option value="${{r.symbol}}">${{r.symbol}} - ${{r.name}} (${{r.group}})</option>`).join('');
    }}
    function addSelectedStock(){{
      const symbol = document.getElementById('stockPicker').value;
      if(!symbol) return alert('請先選擇股票');
      addWatchlistStock(symbol);
    }}
    document.getElementById('watchKeyword').addEventListener('input', (e)=>fillStockPicker(e.target.value));
    fillStockPicker();
    function autoSubmitConfig(){{
      document.getElementById('cfgForm').submit();
    }}
    ['tab','industry','period','interval','status_filter','group_filter','subgroup_filter','cards_per_row','show_volume'].forEach((name)=>{{
      const el = document.querySelector(`[name="${{name}}"]`);
      if(el) el.addEventListener('change', autoSubmitConfig);
    }});
    const limitInput = document.querySelector('[name="limit"]');
    if(limitInput){{
      limitInput.addEventListener('change', autoSubmitConfig);
      limitInput.addEventListener('blur', autoSubmitConfig);
    }}
    if(isIntradayMode){{
      setInterval(()=>{{
        if(!document.hidden) window.location.reload();
      }}, autoRefreshMs);
    }}
    function updateResponsiveGrid(){{
      const grid = document.getElementById('cardsGrid');
      const w = window.innerWidth;
      if (w <= 640) grid.style.gridTemplateColumns = '1fr';
      else if (w <= 1024) grid.style.gridTemplateColumns = 'repeat(2, minmax(0,1fr))';
      else grid.style.gridTemplateColumns = `repeat(${{defaultConfig.cards_per_row || 3}}, minmax(0,1fr))`;
    }}
    window.addEventListener('resize', updateResponsiveGrid);
    updateResponsiveGrid();
    function downloadConfig(){{
      const blob = new Blob([JSON.stringify(serializeForm(), null, 2)], {{type: 'application/json'}});
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = 'tw-dashboard-config.json';
      a.click();
      URL.revokeObjectURL(a.href);
    }}
    function importConfig(evt){{
      const file = evt.target.files[0];
      if(!file) return;
      const reader = new FileReader();
      reader.onload = () => {{
        try {{ applyConfig(JSON.parse(reader.result)); }} catch(e) {{ alert('匯入失敗：JSON 格式錯誤'); }}
      }};
      reader.readAsText(file);
      evt.target.value = '';
    }}
    </script>
    </body></html>"""

    data = body.encode("utf-8")
    start_response("200 OK", [("Content-Type", "text/html; charset=utf-8"), ("Content-Length", str(len(data)))])
    return [data]

if __name__ == "__main__":
    import os

    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8000"))

    try:
        from waitress import serve

        print(f"Serving with waitress on http://{host}:{port}")
        serve(app, host=host, port=port)
    except ImportError:
        from wsgiref.simple_server import make_server

        print("waitress not installed, fallback to wsgiref (development only).")
        print(f"Serving on http://{host}:{port}")
        with make_server(host, port, app) as httpd:
            httpd.serve_forever()
