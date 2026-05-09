from __future__ import annotations

import pandas as pd


def _symbol_key(symbol: str) -> str:
    s = str(symbol).strip().upper()
    if s.endswith(".TW"):
        return s[:-3]
    if s.endswith(".TWO"):
        return s[:-4]
    return s

def _prepare_price_df(symbol: str, df: pd.DataFrame | None, interval: str) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    df = df.copy()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.rename_axis("Date").reset_index() if "Date" not in df.columns else df.reset_index(drop=True)
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
    return df

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
