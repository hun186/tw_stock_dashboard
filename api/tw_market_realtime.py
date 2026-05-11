from __future__ import annotations

import pandas as pd
import yfinance as yf

from api.market_utils import _prepare_price_df
from api.tw_market_quote import _fetch_tw_realtime_quote_snapshot
from api.tw_market_time import _expected_latest_tw_daily_date, _should_use_tw_intraday_daily_snapshot


def _tw_intraday_snapshot_from_minutes(symbol: str, minute_df: pd.DataFrame | None) -> pd.DataFrame:
    intraday_df = _prepare_price_df(symbol, minute_df, "1m")
    if intraday_df.empty:
        return pd.DataFrame()

    expected_date = _expected_latest_tw_daily_date()
    intraday_df = intraday_df[pd.to_datetime(intraday_df["Date"], errors="coerce").dt.normalize() == expected_date]
    if intraday_df.empty:
        return pd.DataFrame()

    minute_snapshot = pd.DataFrame([{
        "Date": expected_date,
        "Open": float(intraday_df.iloc[0]["Open"]),
        "High": float(intraday_df["High"].max()),
        "Low": float(intraday_df["Low"].min()),
        "Close": float(intraday_df.iloc[-1]["Close"]),
        "Volume": float(intraday_df["Volume"].fillna(0).sum()),
    }])

    quote_snapshot = _fetch_tw_realtime_quote_snapshot(symbol, "1d")
    if not quote_snapshot.empty:
        quote_dates = pd.to_datetime(quote_snapshot["Date"], errors="coerce").dt.normalize()
        if not quote_dates.empty and quote_dates.max() == expected_date:
            return _merge_price_frames(minute_snapshot, quote_snapshot)

    return minute_snapshot


def _merge_intraday_realtime_quote(symbol: str, df: pd.DataFrame, quote_snapshot: pd.DataFrame | None = None) -> pd.DataFrame:
    if not symbol.endswith((".TW", ".TWO")) or df.empty:
        return df
    snapshot_df = quote_snapshot if quote_snapshot is not None else _fetch_tw_realtime_quote_snapshot(symbol, "1m")
    if snapshot_df.empty:
        return df
    latest_existing = pd.to_datetime(df["Date"], errors="coerce").max() if "Date" in df.columns else pd.NaT
    quote_time = pd.to_datetime(snapshot_df["Date"], errors="coerce").max()
    if isinstance(latest_existing, pd.Timestamp) and latest_existing.tzinfo is not None:
        latest_existing = latest_existing.tz_convert("Asia/Taipei").tz_localize(None)
    if isinstance(quote_time, pd.Timestamp) and quote_time.tzinfo is not None:
        quote_time = quote_time.tz_convert("Asia/Taipei").tz_localize(None)
    if pd.isna(quote_time) or (not pd.isna(latest_existing) and quote_time <= latest_existing):
        return df
    df = df.copy()
    df_dates = pd.to_datetime(df["Date"], errors="coerce")
    if getattr(df_dates.dt, "tz", None) is not None:
        df_dates = df_dates.dt.tz_convert("Asia/Taipei").dt.tz_localize(None)
    df["Date"] = df_dates
    if "RefClose" in df.columns:
        snapshot_df = snapshot_df.copy()
        snapshot_df["RefClose"] = float(df["RefClose"].dropna().iloc[-1]) if not df["RefClose"].dropna().empty else float(df.iloc[0]["Open"])
    return _merge_price_frames(df, snapshot_df)


def _fetch_tw_intraday_daily_snapshot(symbol: str) -> pd.DataFrame:
    if not _should_use_tw_intraday_daily_snapshot():
        return pd.DataFrame()
    try:
        minute_df = yf.download(symbol, period="1d", interval="1m", auto_adjust=False, progress=False, threads=False)
    except Exception:
        return pd.DataFrame()
    return _tw_intraday_snapshot_from_minutes(symbol, minute_df)


def _bulk_fetch_tw_intraday_daily_snapshots(symbols: list[str]) -> dict[str, pd.DataFrame]:
    tw_symbols = [symbol for symbol in symbols if symbol.endswith((".TW", ".TWO"))]
    if not tw_symbols or not _should_use_tw_intraday_daily_snapshot():
        return {}
    try:
        downloaded = yf.download(
            tw_symbols,
            period="1d",
            interval="1m",
            auto_adjust=False,
            progress=False,
            threads=True,
            group_by="ticker",
        )
    except Exception:
        return {}
    if downloaded.empty:
        return {}

    snapshots: dict[str, pd.DataFrame] = {}
    for symbol in tw_symbols:
        if isinstance(downloaded.columns, pd.MultiIndex) and symbol in downloaded.columns.get_level_values(0):
            raw_df = downloaded[symbol]
        elif len(tw_symbols) == 1:
            raw_df = downloaded
        else:
            continue
        snapshot_df = _tw_intraday_snapshot_from_minutes(symbol, raw_df)
        if not snapshot_df.empty:
            snapshots[symbol] = snapshot_df
    return snapshots


def _merge_price_frames(base_df: pd.DataFrame, update_df: pd.DataFrame) -> pd.DataFrame:
    if update_df.empty:
        return base_df
    if base_df.empty:
        return update_df.reset_index(drop=True)
    return (
        pd.concat([base_df, update_df], ignore_index=True)
        .drop_duplicates(subset=["Date"], keep="last")
        .sort_values("Date")
        .reset_index(drop=True)
    )
