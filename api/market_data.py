from __future__ import annotations

import os
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd
import yfinance as yf

from api.constants import STATIC_CACHE_DIR


PRICE_CACHE: dict[tuple[str, str, str], tuple[float, pd.DataFrame]] = {}
TARGET_PRICE_CACHE: dict[str, tuple[float, str]] = {}


def get_price_cache_ttl_seconds(interval: str) -> int:
    return _cache_ttl_seconds(interval)


def _symbol_key(symbol: str) -> str:
    s = str(symbol).strip().upper()
    if s.endswith(".TW"):
        return s[:-3]
    if s.endswith(".TWO"):
        return s[:-4]
    return s


def _cache_ttl_seconds(interval: str) -> int:
    if interval == "1m":
        return 20
    if interval.endswith("m"):
        return 60
    return 300


def _disk_cache_max_age_seconds(interval: str) -> int:
    if interval.endswith("m"):
        return _cache_ttl_seconds(interval)
    return 60 * 60 * 24 * 7


def _disk_cache_path(symbol: str, period: str, interval: str) -> Path:
    safe_symbol = symbol.replace("/", "_").replace(".", "_")
    return STATIC_CACHE_DIR / f"{safe_symbol}__{period}__{interval}.pkl"


def _load_disk_cache(symbol: str, period: str, interval: str, ttl_seconds: int | None) -> pd.DataFrame | None:
    path = _disk_cache_path(symbol, period, interval)
    try:
        if not path.exists():
            return None
        if ttl_seconds is not None:
            age = time.time() - path.stat().st_mtime
            if age >= ttl_seconds:
                return None
        df = pd.read_pickle(path)
        return df if isinstance(df, pd.DataFrame) else None
    except Exception:
        return None


def _cached_price(symbol: str, period: str, interval: str, now: float, *, allow_stale_disk: bool = False) -> pd.DataFrame | None:
    cache_key = (symbol, period, interval)
    cached = PRICE_CACHE.get(cache_key)
    if cached and now - cached[0] < _cache_ttl_seconds(interval):
        return cached[1].copy()

    disk_cached = _load_disk_cache(
        symbol,
        period,
        interval,
        None if allow_stale_disk else _disk_cache_max_age_seconds(interval),
    )
    if disk_cached is not None:
        PRICE_CACHE[cache_key] = (now, disk_cached.copy())
        return disk_cached.copy()
    return None


def _store_price_cache(symbol: str, period: str, interval: str, df: pd.DataFrame, now: float | None = None) -> pd.DataFrame:
    PRICE_CACHE[(symbol, period, interval)] = (now or time.time(), df.copy())
    return df


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


def fetch_price(symbol: str, period: str = "3mo", interval: str = "1d", *, allow_stale_disk: bool = False) -> pd.DataFrame:
    now = time.time()
    cached = _cached_price(symbol, period, interval, now, allow_stale_disk=allow_stale_disk)
    if cached is not None:
        return cached

    downloaded = yf.download(symbol, period=period, interval=interval, auto_adjust=False, progress=False, threads=False)
    df = _prepare_price_df(symbol, downloaded, interval)
    if df.empty:
        return pd.DataFrame()
    return _store_price_cache(symbol, period, interval, df, now)


def fetch_target_price(symbol: str) -> str:
    now = time.time()
    cache_ttl = 60 * 60 * 6
    cached = TARGET_PRICE_CACHE.get(symbol)
    if cached and now - cached[0] < cache_ttl:
        return cached[1]
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.get_info()
    except Exception:
        info = {}
    target_keys = ("targetMeanPrice", "targetMedianPrice", "targetHighPrice", "targetLowPrice")
    for key in target_keys:
        value = info.get(key) if isinstance(info, dict) else None
        if value is not None and not pd.isna(value):
            text = f"{float(value):.2f}"
            TARGET_PRICE_CACHE[symbol] = (now, text)
            return text
    TARGET_PRICE_CACHE[symbol] = (now, "-")
    return "-"




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


def _is_serverless_runtime() -> bool:
    return os.environ.get("VERCEL") == "1" or bool(os.environ.get("AWS_LAMBDA_FUNCTION_NAME"))


def prefetch_price_data(
    stocks: pd.DataFrame,
    period: str,
    interval: str,
    *,
    allow_live_fetch: bool | None = None,
    allow_stale_disk: bool = False,
    max_live_symbols: int = 80,
) -> dict[str, pd.DataFrame]:
    symbols = list(dict.fromkeys(s for s in stocks["symbol"].dropna().astype(str).tolist() if s))
    if not symbols:
        return {}

    if allow_live_fetch is None:
        allow_live_fetch = not _is_serverless_runtime() or len(symbols) <= max_live_symbols

    now = time.time()
    price_map: dict[str, pd.DataFrame] = {}
    missing_symbols: list[str] = []
    for symbol in symbols:
        cached = _cached_price(symbol, period, interval, now, allow_stale_disk=allow_stale_disk)
        if cached is None:
            missing_symbols.append(symbol)
        else:
            price_map[symbol] = cached

    live_symbols = missing_symbols[:max_live_symbols] if allow_live_fetch else []
    if live_symbols:
        try:
            downloaded = yf.download(
                live_symbols,
                period=period,
                interval=interval,
                auto_adjust=False,
                progress=False,
                threads=True,
                group_by="ticker",
            )
        except Exception:
            downloaded = pd.DataFrame()

        if not downloaded.empty:
            for symbol in live_symbols[:]:
                if isinstance(downloaded.columns, pd.MultiIndex) and symbol in downloaded.columns.get_level_values(0):
                    raw_df = downloaded[symbol]
                elif len(live_symbols) == 1:
                    raw_df = downloaded
                else:
                    continue
                df = _prepare_price_df(symbol, raw_df, interval)
                if not df.empty:
                    price_map[symbol] = _store_price_cache(symbol, period, interval, df, now).copy()

    still_missing = [symbol for symbol in live_symbols if symbol not in price_map]
    if allow_live_fetch and still_missing:
        max_workers = min(8, len(still_missing))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            results = executor.map(
                lambda sym: (sym, fetch_price(sym, period, interval, allow_stale_disk=allow_stale_disk)),
                still_missing,
            )
            price_map.update({symbol: df for symbol, df in results})

    return {symbol: price_map.get(symbol, pd.DataFrame()) for symbol in symbols}

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


