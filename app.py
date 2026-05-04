from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf


APP_DIR = Path(__file__).parent
WATCHLIST_FILE = APP_DIR / "watchlist.csv"


st.set_page_config(
    page_title="多台股監控 Dashboard",
    page_icon="📈",
    layout="wide",
)


def load_watchlist(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=["symbol", "name", "group"])
    df = pd.read_csv(path)
    required = {"symbol", "name", "group"}
    missing = required - set(df.columns)
    if missing:
        st.error(f"watchlist.csv 缺少欄位：{', '.join(missing)}")
        st.stop()
    df["symbol"] = df["symbol"].astype(str).str.strip()
    df["name"] = df["name"].astype(str).str.strip()
    df["group"] = df["group"].astype(str).str.strip()
    return df[df["symbol"] != ""].copy()


@st.cache_data(ttl=900, show_spinner=False)
def fetch_price(symbol: str, period: str, interval: str) -> pd.DataFrame:
    df = yf.download(
        symbol,
        period=period,
        interval=interval,
        auto_adjust=False,
        progress=False,
        threads=False,
    )

    if df is None or df.empty:
        return pd.DataFrame()

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df = df.rename_axis("Date").reset_index()
    needed = ["Date", "Open", "High", "Low", "Close", "Volume"]
    for col in needed:
        if col not in df.columns:
            return pd.DataFrame()

    df = df[needed].dropna(subset=["Close"])
    return df




@st.cache_data(ttl=86400, show_spinner=False)
def resolve_symbol_meta(symbol: str) -> tuple[str, str]:
    try:
        ticker = yf.Ticker(symbol)
        fast_info = ticker.fast_info or {}
        info = ticker.info or {}
        name = info.get("shortName") or info.get("longName") or symbol
        exchange = str(fast_info.get("exchange") or info.get("exchange") or "").upper()

        if exchange in {"TWO", "OTC"}:
            market_group = "上櫃"
        elif exchange in {"TAI", "TWSE"}:
            market_group = "上市"
        else:
            market_group = "臨時加入"

        return str(name).strip() or symbol, market_group
    except Exception:
        return symbol, "臨時加入"

def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["MA5"] = df["Close"].rolling(5).mean()
    df["MA20"] = df["Close"].rolling(20).mean()
    df["MA60"] = df["Close"].rolling(60).mean()

    delta = df["Close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    df["RSI14"] = 100 - (100 / (1 + rs))
    return df


def classify_status(df: pd.DataFrame) -> tuple[str, str]:
    if df.empty or len(df) < 25:
        return "資料不足", "⚪"

    last = df.iloc[-1]
    close = float(last["Close"])
    ma20 = float(last["MA20"]) if not pd.isna(last["MA20"]) else np.nan
    rsi = float(last["RSI14"]) if not pd.isna(last["RSI14"]) else np.nan

    if np.isnan(ma20):
        return "資料不足", "⚪"

    dist = (close - ma20) / ma20 * 100

    if close < ma20:
        return f"跌破 MA20（{dist:.1f}%）", "🟢"
    if 0 <= dist <= 5:
        return f"回檔靠近 MA20（+{dist:.1f}%）", "🟡"
    if dist > 10 and not np.isnan(rsi) and rsi >= 70:
        return f"偏熱，勿追（MA20 +{dist:.1f}%, RSI {rsi:.0f}）", "🟠"
    return f"強勢在 MA20 上（+{dist:.1f}%）", "🔴"


UP_COLOR = "#d60000"  # 台股習慣：上漲紅色
DOWN_COLOR = "#008a00"  # 台股習慣：下跌綠色

def make_chart(df: pd.DataFrame, title: str, height: int = 330) -> go.Figure:
    fig = go.Figure()

    fig.add_trace(
        go.Candlestick(
            x=df["Date"],
            open=df["Open"],
            high=df["High"],
            low=df["Low"],
            close=df["Close"],
            name="K線",
            increasing_line_width=1,
            decreasing_line_width=1,
            increasing_line_color=UP_COLOR,
            increasing_fillcolor=UP_COLOR,
            decreasing_line_color=DOWN_COLOR,
            decreasing_fillcolor=DOWN_COLOR,
            hovertemplate=(
                "日期: %{x|%Y-%m-%d}<br>"
                "開: %{open:.2f}<br>"
                "高: %{high:.2f}<br>"
                "低: %{low:.2f}<br>"
                "收: %{close:.2f}<extra></extra>"
            ),
        )
    )

    fig.add_trace(
        go.Scatter(
            x=df["Date"],
            y=df["Close"],
            mode="lines",
            name="收盤線",
            line=dict(width=0.8, color="#444"),
            opacity=0.35,
            customdata=df[["Open", "High", "Low", "Close"]],
            hovertemplate=(
                "日期: %{x|%Y-%m-%d}<br>"
                "開: %{customdata[0]:.2f}<br>"
                "高: %{customdata[1]:.2f}<br>"
                "低: %{customdata[2]:.2f}<br>"
                "收: %{customdata[3]:.2f}<extra></extra>"
            ),
        )
    )

    for ma in ["MA5", "MA20", "MA60"]:
        fig.add_trace(
            go.Scatter(
                x=df["Date"],
                y=df[ma],
                mode="lines",
                name=ma,
                line=dict(width=1.3),
            )
        )

    fig.update_layout(
        title=title,
        height=height,
        margin=dict(l=8, r=8, t=42, b=8),
        xaxis_rangeslider_visible=False,
        legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="left", x=0),
        hovermode="x unified",
    )

    return fig


def make_volume_chart(df: pd.DataFrame, height: int = 120) -> go.Figure:
    fig = go.Figure()
    prev_close = df["Close"].shift(1).fillna(df["Open"])
    bar_colors = np.where(df["Close"] >= prev_close, UP_COLOR, DOWN_COLOR)

    fig.add_trace(
        go.Bar(
            x=df["Date"],
            y=df["Volume"],
            name="成交量",
            marker_color=bar_colors,
        )
    )
    fig.update_layout(
        height=height,
        margin=dict(l=8, r=8, t=8, b=8),
        showlegend=False,
    )
    return fig


def make_rsi_chart(df: pd.DataFrame, height: int = 120) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df["Date"],
            y=df["RSI14"],
            mode="lines",
            name="RSI14",
            line=dict(width=1.5),
        )
    )
    fig.add_hline(y=70, line_dash="dash")
    fig.add_hline(y=30, line_dash="dash")
    fig.update_yaxes(range=[0, 100])
    fig.update_layout(
        height=height,
        margin=dict(l=8, r=8, t=8, b=8),
        showlegend=False,
    )
    return fig


def compact_metrics(df: pd.DataFrame) -> dict:
    last = df.iloc[-1]
    prev = df.iloc[-2] if len(df) >= 2 else last
    close = float(last["Close"])
    prev_close = float(prev["Close"])
    change_pct = (close - prev_close) / prev_close * 100 if prev_close else 0

    ma20 = float(last["MA20"]) if not pd.isna(last["MA20"]) else np.nan
    ma60 = float(last["MA60"]) if not pd.isna(last["MA60"]) else np.nan
    rsi = float(last["RSI14"]) if not pd.isna(last["RSI14"]) else np.nan

    dist20 = (close - ma20) / ma20 * 100 if not np.isnan(ma20) else np.nan
    dist60 = (close - ma60) / ma60 * 100 if not np.isnan(ma60) else np.nan

    return {
        "close": close,
        "change_pct": change_pct,
        "dist20": dist20,
        "dist60": dist60,
        "rsi": rsi,
    }




def status_tag(icon: str, status_text: str) -> str:
    if icon == "🟡":
        return "🟡 回檔"
    if icon == "🔴":
        return "🔴 強勢"
    if icon == "🟠":
        return "🟠 過熱"
    if icon == "🟢":
        return "🟢 跌破"
    return "⚪ 資料不足/抓不到"

st.title("📈 多台股監控 Dashboard")
st.caption("一頁掌握多檔台股是否回檔、靠近均線、過熱或轉弱。資料來源：Yahoo Finance，可能有延遲。")

watchlist = load_watchlist(WATCHLIST_FILE)

with st.sidebar:
    st.header("設定")
    period = st.selectbox("資料期間", ["3mo", "6mo", "1y", "2y"], index=0)
    interval = st.selectbox("K線週期", ["1d", "1wk"], index=0)
    max_cards = st.slider("最多顯示檔數", min_value=3, max_value=24, value=12, step=3)
    columns_per_row = st.selectbox("每列幾檔", [1, 2, 3, 4], index=2)

    groups = ["全部"] + sorted(watchlist["group"].dropna().unique().tolist())
    group = st.selectbox("分類", groups)

    status_options = ["🟡 回檔", "🔴 強勢", "🟠 過熱", "🟢 跌破", "⚪ 資料不足/抓不到"]
    selected_status = st.multiselect("狀態篩選", status_options, default=[])

    st.divider()
    st.subheader("快速加入代號")
    st.write("格式例：`2330.TW`、`4971.TWO`")
    manual_symbols = st.text_area("臨時股票代號，一行一檔", value="", height=120)

if group != "全部":
    watchlist = watchlist[watchlist["group"] == group].copy()

manual_rows = []
for line in manual_symbols.splitlines():
    symbol = line.strip()
    if symbol:
        name, group_name = resolve_symbol_meta(symbol)
        manual_rows.append({"symbol": symbol, "name": name, "group": group_name})
if manual_rows:
    watchlist = pd.concat([watchlist, pd.DataFrame(manual_rows)], ignore_index=True)

watchlist = watchlist.drop_duplicates(subset=["symbol"]).head(max_cards)

if watchlist.empty:
    st.warning("watchlist.csv 沒有股票。請加入 symbol,name,group。")
    st.stop()

summary_rows = []
data_cache = {}

progress = st.progress(0, text="下載股價資料中...")
for i, row in enumerate(watchlist.itertuples(index=False), start=1):
    df = fetch_price(row.symbol, period, interval)
    if not df.empty:
        df = add_indicators(df)
        data_cache[row.symbol] = df
        status, icon = classify_status(df)
        m = compact_metrics(df)
        summary_rows.append({
            "狀態": icon,
            "代號": row.symbol,
            "名稱": row.name,
            "分類": row.group,
            "收盤": round(m["close"], 2),
            "日漲跌%": round(m["change_pct"], 2),
            "距MA20%": None if np.isnan(m["dist20"]) else round(m["dist20"], 2),
            "距MA60%": None if np.isnan(m["dist60"]) else round(m["dist60"], 2),
            "RSI14": None if np.isnan(m["rsi"]) else round(m["rsi"], 1),
            "判斷": status,
            "篩選": status_tag(icon, status),
        })
    else:
        summary_rows.append({
            "狀態": "⚪",
            "代號": row.symbol,
            "名稱": row.name,
            "分類": row.group,
            "收盤": None,
            "日漲跌%": None,
            "距MA20%": None,
            "距MA60%": None,
            "RSI14": None,
            "判斷": "抓不到資料",
            "篩選": "⚪ 資料不足/抓不到",
        })
    progress.progress(i / len(watchlist), text=f"下載股價資料中... {i}/{len(watchlist)}")
progress.empty()

summary = pd.DataFrame(summary_rows)

if selected_status:
    summary = summary[summary["篩選"].isin(selected_status)].copy()

st.subheader("總覽")
st.dataframe(summary.drop(columns=["篩選"], errors="ignore"), use_container_width=True, hide_index=True)

if summary.empty:
    st.info("目前篩選條件下沒有符合的股票。")
    st.stop()

filtered_symbols = summary["代號"].tolist()
filtered_watchlist = watchlist[watchlist["symbol"].isin(filtered_symbols)].copy()

st.subheader("多股趨勢圖")
cols = st.columns(columns_per_row)

for idx, row in enumerate(filtered_watchlist.itertuples(index=False)):
    with cols[idx % columns_per_row]:
        df = data_cache.get(row.symbol)
        if df is None or df.empty:
            st.error(f"{row.name}（{row.symbol}）抓不到資料")
            continue

        status, icon = classify_status(df)
        m = compact_metrics(df)

        st.markdown(f"### {icon} {row.name} `{row.symbol}`")
        metric_cols = st.columns(4)
        metric_cols[0].metric("收盤", f"{m['close']:.2f}", f"{m['change_pct']:.2f}%")
        metric_cols[1].metric("距 MA20", "-" if np.isnan(m["dist20"]) else f"{m['dist20']:.1f}%")
        metric_cols[2].metric("距 MA60", "-" if np.isnan(m["dist60"]) else f"{m['dist60']:.1f}%")
        metric_cols[3].metric("RSI14", "-" if np.isnan(m["rsi"]) else f"{m['rsi']:.0f}")

        st.caption(status)
        st.plotly_chart(make_chart(df, f"{row.name} {row.symbol}"), use_container_width=True)
        with st.expander("成交量 / RSI"):
            st.plotly_chart(make_volume_chart(df), use_container_width=True)
            st.plotly_chart(make_rsi_chart(df), use_container_width=True)

st.divider()
st.caption("提醒：這是監控工具，不是買賣建議。台股資料來自 Yahoo Finance，可能有延遲或缺漏。")
