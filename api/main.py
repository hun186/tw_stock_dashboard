from __future__ import annotations

import html
import json
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
    "buy": "🟢 可關注",
    "pullback": "🟡 回檔觀察",
    "overheat": "🟠 偏熱",
    "strong": "🔴 強勢",
}


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
        return pd.DataFrame(columns=["industry", "industry_label", "symbol", "name", "group"])

    if not {"公司代號", "公司簡稱", "產業別"}.issubset(df.columns):
        return pd.DataFrame(columns=["industry", "industry_label", "symbol", "name", "group"])

    df["industry"] = df["產業別"].astype(str).str.strip()
    df["industry_label"] = df["industry"].apply(lambda x: f"{x} - {INDUSTRY_CODE_NAME.get(x, '未分類')}")
    df["symbol"] = df["公司代號"].astype(str).str.strip() + ".TW"
    df["name"] = df["公司簡稱"].astype(str).str.strip()
    df["group"] = "上市-" + df["industry"]
    return df[df["industry"] != ""][["industry", "industry_label", "symbol", "name", "group"]].drop_duplicates()


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


def classify_status(df: pd.DataFrame) -> tuple[str, str]:
    if len(df) < 25:
        return "watch", "⚪ 資料不足"
    last = df.iloc[-1]
    close = float(last["Close"])
    ma20 = float(last["MA20"]) if not pd.isna(last["MA20"]) else np.nan
    rsi = float(last["RSI14"]) if not pd.isna(last["RSI14"]) else np.nan
    if np.isnan(ma20):
        return "watch", "⚪ 資料不足"
    dist = (close - ma20) / ma20 * 100
    if close < ma20:
        return "buy", f"🟢 跌破 ({dist:.1f}%)"
    if 0 <= dist <= 5:
        return "pullback", f"🟡 回檔 (+{dist:.1f}%)"
    if dist > 10 and not np.isnan(rsi) and rsi >= 70:
        return "overheat", f"🟠 過熱 (RSI {rsi:.0f})"
    return "strong", f"🔴 強勢 (+{dist:.1f}%)"


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
    limit = int(params.get("limit", ["30"])[0])
    status_filter = params.get("status_filter", ["all"])[0]

    watchlist = load_watchlist(WATCHLIST_FILE).head(limit)
    industry_df = load_twse_industry_map()
    industries = industry_df[["industry", "industry_label"]].drop_duplicates().sort_values("industry")
    industry = params.get("industry", [industries.iloc[0]["industry"] if not industries.empty else ""])[0]

    if tab == "category" and industry:
        stocks = industry_df[industry_df["industry"] == industry][["symbol", "name", "group"]].head(limit)
    else:
        stocks = watchlist

    rows = []
    cards = []
    for row in stocks.itertuples(index=False):
        df = fetch_price(row.symbol, period, interval)
        if df.empty:
            bucket, status = "watch", "⚪ 抓不到資料"
            close_text = "-"
        else:
            df = add_indicators(df)
            bucket, status = classify_status(df)
            close_text = f"{float(df.iloc[-1]['Close']):.2f}"

        if status_filter != "all" and bucket != status_filter:
            continue

        rows.append(
            f"<tr><td>{html.escape(status.split()[0])}</td><td>{html.escape(row.symbol)}</td><td>{html.escape(row.name)}</td><td>{html.escape(status)}</td><td>{close_text}</td></tr>"
        )
        if not df.empty:
            cards.append(f"<h3>{html.escape(row.name)} ({html.escape(row.symbol)}) 收盤 {close_text}</h3>{make_chart_html(df, row.name)}")

    industry_options = "".join([
        f"<option value='{html.escape(r.industry)}' {'selected' if r.industry == industry else ''}>{html.escape(r.industry_label)}</option>"
        for r in industries.itertuples(index=False)
    ])
    status_options = "".join([
        f"<option value='{k}' {'selected' if k == status_filter else ''}>{v}</option>" for k, v in STATUS_FILTERS.items()
    ])

    save_payload = {
        "tab": tab,
        "industry": industry,
        "period": period,
        "interval": interval,
        "limit": limit,
        "status_filter": status_filter,
    }

    body = f"""<!doctype html><html lang='zh-Hant'><head><meta charset='utf-8'><title>TW Dashboard</title>
    <style>body{{font-family:Arial;margin:20px}} table{{border-collapse:collapse;width:100%}}td,th{{border:1px solid #ddd;padding:6px}} .card{{margin:18px 0;padding:10px;border:1px solid #ddd;border-radius:8px}}</style></head><body>
    <h1>多台股監控 Dashboard（Vercel 版）</h1>
    <form id='cfgForm'>
    <label>頁籤</label><select name='tab'><option value='watchlist' {'selected' if tab=='watchlist' else ''}>自選股監控</option><option value='category' {'selected' if tab=='category' else ''}>分類股池</option></select>
    <label>產業</label><select name='industry'>{industry_options}</select>
    <label>期間</label><select name='period'><option {'selected' if period=='3mo' else ''}>3mo</option><option {'selected' if period=='6mo' else ''}>6mo</option><option {'selected' if period=='1y' else ''}>1y</option></select>
    <label>週期</label><select name='interval'><option {'selected' if interval=='1d' else ''}>1d</option><option {'selected' if interval=='1wk' else ''}>1wk</option></select>
    <label>檔數</label><input name='limit' value='{limit}' size='3'/>
    <label>判斷篩選</label><select name='status_filter'>{status_options}</select>
    <button type='submit'>更新</button>
    <button type='button' onclick='saveLocal()'>存到瀏覽器</button>
    <button type='button' onclick='loadLocal()'>讀取瀏覽器設定</button>
    <button type='button' onclick='downloadConfig()'>下載設定檔</button>
    <input type='file' id='cfgFile' accept='application/json' style='display:none' onchange='importConfig(event)'>
    <button type='button' onclick="document.getElementById('cfgFile').click()">匯入設定檔</button>
    </form>
    <h2>總覽</h2><table><tr><th>狀態</th><th>代號</th><th>名稱</th><th>判斷</th><th>收盤</th></tr>{''.join(rows) if rows else '<tr><td colspan="5">無符合條件資料</td></tr>'}</table>
    <h2>多股趨勢圖</h2>{''.join([f"<div class='card'>{c}</div>" for c in cards])}
    <script>
    const defaultConfig = {json.dumps(save_payload, ensure_ascii=False)};
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
