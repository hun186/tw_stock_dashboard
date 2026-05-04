from __future__ import annotations

from pathlib import Path
from urllib.parse import parse_qs

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import requests
import yfinance as yf

APP_DIR = Path(__file__).resolve().parent.parent
WATCHLIST_FILE = APP_DIR / "watchlist.csv"
TWSE_LISTED_INFO_API = "https://openapi.twse.com.tw/v1/opendata/t187ap03_L"

UP_COLOR = "#d60000"
DOWN_COLOR = "#008a00"


def load_watchlist(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=["symbol", "name", "group"])
    df = pd.read_csv(path)
    for col in ["symbol", "name", "group"]:
        if col not in df.columns:
            return pd.DataFrame(columns=["symbol", "name", "group"])
    df["symbol"] = df["symbol"].astype(str).str.strip()
    df["name"] = df["name"].astype(str).str.strip()
    df["group"] = df["group"].astype(str).str.strip()
    return df[df["symbol"] != ""].copy()


def load_twse_industry_map() -> pd.DataFrame:
    try:
        resp = requests.get(TWSE_LISTED_INFO_API, timeout=10)
        resp.raise_for_status()
        df = pd.DataFrame(resp.json())
    except Exception:
        return pd.DataFrame(columns=["industry", "symbol", "name", "group"])

    if not {"公司代號", "公司簡稱", "產業別"}.issubset(df.columns):
        return pd.DataFrame(columns=["industry", "symbol", "name", "group"])

    df["industry"] = df["產業別"].astype(str).str.strip()
    df["symbol"] = df["公司代號"].astype(str).str.strip() + ".TW"
    df["name"] = df["公司簡稱"].astype(str).str.strip()
    df["group"] = "上市-" + df["industry"]
    return df[df["industry"] != ""][ ["industry", "symbol", "name", "group"] ].drop_duplicates()


def fetch_price(symbol: str, period: str = "3mo", interval: str = "1d") -> pd.DataFrame:
    df = yf.download(symbol, period=period, interval=interval, auto_adjust=False, progress=False, threads=False)
    if df is None or df.empty:
        return pd.DataFrame()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.rename_axis("Date").reset_index()
    need = ["Date", "Open", "High", "Low", "Close", "Volume"]
    if not set(need).issubset(df.columns):
        return pd.DataFrame()
    return df[need].dropna(subset=["Close"])


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["MA20"] = df["Close"].rolling(20).mean()
    delta = df["Close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    rs = gain.rolling(14).mean() / loss.rolling(14).mean().replace(0, np.nan)
    df["RSI14"] = 100 - (100 / (1 + rs))
    return df


def classify_status(df: pd.DataFrame) -> str:
    if len(df) < 25:
        return "⚪ 資料不足"
    last = df.iloc[-1]
    close = float(last["Close"])
    ma20 = float(last["MA20"]) if not pd.isna(last["MA20"]) else np.nan
    rsi = float(last["RSI14"]) if not pd.isna(last["RSI14"]) else np.nan
    if np.isnan(ma20):
        return "⚪ 資料不足"
    dist = (close - ma20) / ma20 * 100
    if close < ma20:
        return f"🟢 跌破 ({dist:.1f}%)"
    if 0 <= dist <= 5:
        return f"🟡 回檔 (+{dist:.1f}%)"
    if dist > 10 and not np.isnan(rsi) and rsi >= 70:
        return f"🟠 過熱 (RSI {rsi:.0f})"
    return f"🔴 強勢 (+{dist:.1f}%)"


def make_chart_html(df: pd.DataFrame, title: str) -> str:
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=df["Date"], open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"], name="K線",
                                 increasing_line_color=UP_COLOR, decreasing_line_color=DOWN_COLOR))
    fig.add_trace(go.Scatter(x=df["Date"], y=df["MA20"], mode="lines", name="MA20"))
    fig.update_layout(title=title, height=320, margin=dict(l=4, r=4, t=36, b=4), xaxis_rangeslider_visible=False)
    return fig.to_html(full_html=False, include_plotlyjs="cdn")


def app(environ, start_response):
    params = parse_qs(environ.get("QUERY_STRING", ""))
    tab = params.get("tab", ["watchlist"])[0]
    period = params.get("period", ["3mo"])[0]
    interval = params.get("interval", ["1d"])[0]
    limit = int(params.get("limit", ["8"])[0])

    watchlist = load_watchlist(WATCHLIST_FILE).head(limit)
    industry_df = load_twse_industry_map()
    industries = sorted(industry_df["industry"].dropna().unique().tolist())
    industry = params.get("industry", [industries[0] if industries else ""])[0]

    if tab == "category" and industry:
        stocks = industry_df[industry_df["industry"] == industry][["symbol", "name", "group"]].head(limit)
    else:
        stocks = watchlist

    rows = []
    cards = []
    for row in stocks.itertuples(index=False):
        df = fetch_price(row.symbol, period, interval)
        if df.empty:
            rows.append(f"<tr><td>⚪</td><td>{row.symbol}</td><td>{row.name}</td><td>抓不到資料</td></tr>")
            continue
        df = add_indicators(df)
        status = classify_status(df)
        close = float(df.iloc[-1]["Close"])
        rows.append(f"<tr><td>{status.split()[0]}</td><td>{row.symbol}</td><td>{row.name}</td><td>{status}</td></tr>")
        cards.append(f"<h3>{row.name} ({row.symbol}) 收盤 {close:.2f}</h3>{make_chart_html(df, row.name)}")

    industry_options = "".join([f"<option {'selected' if i==industry else ''}>{i}</option>" for i in industries])
    body = f"""<!doctype html><html lang='zh-Hant'><head><meta charset='utf-8'><title>TW Dashboard</title>
    <style>body{{font-family:Arial;margin:20px}} table{{border-collapse:collapse;width:100%}}td,th{{border:1px solid #ddd;padding:6px}} .card{{margin:18px 0;padding:10px;border:1px solid #ddd;border-radius:8px}}</style></head><body>
    <h1>多台股監控 Dashboard（Vercel 版）</h1>
    <form>
    <label>頁籤</label><select name='tab'><option value='watchlist' {'selected' if tab=='watchlist' else ''}>自選股監控</option><option value='category' {'selected' if tab=='category' else ''}>分類股池</option></select>
    <label>產業</label><select name='industry'>{industry_options}</select>
    <label>期間</label><select name='period'><option>3mo</option><option>6mo</option><option>1y</option></select>
    <label>週期</label><select name='interval'><option>1d</option><option>1wk</option></select>
    <label>檔數</label><input name='limit' value='{limit}' size='3'/>
    <button type='submit'>更新</button></form>
    <h2>總覽</h2><table><tr><th>狀態</th><th>代號</th><th>名稱</th><th>判斷</th></tr>{''.join(rows)}</table>
    <h2>多股趨勢圖</h2>{''.join([f"<div class='card'>{c}</div>" for c in cards])}
    </body></html>"""

    data = body.encode("utf-8")
    start_response("200 OK", [("Content-Type", "text/html; charset=utf-8"), ("Content-Length", str(len(data)))])
    return [data]
