from __future__ import annotations

import os
import time
from concurrent.futures import ThreadPoolExecutor

import pandas as pd
import yfinance as yf

from api.market_cache import (
    TARGET_PRICE_CACHE,
    _cached_price,
    _cache_ttl_seconds,
    _disk_cache_max_age_seconds,
    _disk_cache_path,
    _load_disk_cache,
    _store_price_cache,
)
from api.market_utils import _prepare_price_df, _symbol_key, resolve_price_params, trim_display_df
from api.tw_market_data import (
    _bulk_fetch_tw_intraday_daily_snapshots,
    _expected_latest_tw_daily_date,
    _fetch_tw_intraday_daily_snapshot,
    _fetch_tw_official_daily_price,
    _fetch_tw_realtime_quote_snapshot,
    _is_stale_tw_daily_price,
    _latest_price_date,
    _merge_intraday_realtime_quote,
    _merge_price_frames,
    _merge_tw_daily_realtime_price,
    _should_use_tw_intraday_daily_snapshot,
    _taipei_now,
    _tw_daily_price_needs_official_refresh,
)

def get_price_cache_ttl_seconds(interval: str) -> int:
    return _cache_ttl_seconds(interval)


def fetch_price(symbol: str, period: str = "3mo", interval: str = "1d", *, allow_stale_disk: bool = False) -> pd.DataFrame:
    now = time.time()
    cached = _cached_price(symbol, period, interval, now, allow_stale_disk=allow_stale_disk)
    stale_cached = cached if cached is not None and _is_stale_tw_daily_price(symbol, interval, cached) else None
    if cached is not None and stale_cached is None:
        return cached

    try:
        downloaded = yf.download(symbol, period=period, interval=interval, auto_adjust=False, progress=False, threads=False)
    except Exception:
        downloaded = pd.DataFrame()
    df = _prepare_price_df(symbol, downloaded, interval)
    if interval == "1d":
        df = _merge_tw_daily_realtime_price(symbol, period, df)
    elif interval.endswith("m"):
        df = _merge_intraday_realtime_quote(symbol, df)
    if df.empty:
        return stale_cached.copy() if allow_stale_disk and stale_cached is not None else pd.DataFrame()
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
    force_live_refresh: bool = False,
) -> dict[str, pd.DataFrame]:
    symbols = list(dict.fromkeys(s for s in stocks["symbol"].dropna().astype(str).tolist() if s))
    if not symbols:
        return {}

    if allow_live_fetch is None:
        allow_live_fetch = not _is_serverless_runtime() or len(symbols) <= max_live_symbols
    if force_live_refresh and symbols:
        # A forced refresh is issued by the browser after the quick stale render.
        # Even broad serverless pages should try a bounded live refresh instead of
        # returning only the prebuilt cache forever.  live_symbols below still caps
        # fan-out at max_live_symbols to avoid Vercel timeouts.
        allow_live_fetch = True

    now = time.time()
    price_map: dict[str, pd.DataFrame] = {}
    missing_symbols: list[str] = []
    # Normal dashboard loads may use stale disk data so users see the page quickly.
    # Browser refresh requests add force_live_refresh=True and bypass stale snapshots
    # for symbols that are behind the expected Taiwan trading date; that second
    # request updates the page in-place without relying on Vercel background threads
    # or writable cache files.  Broad serverless first renders still avoid network
    # fan-out; forced refreshes above enable only a bounded max_live_symbols pass.
    initial_allow_stale_disk = allow_stale_disk and (not allow_live_fetch or not force_live_refresh)
    for symbol in symbols:
        cached = _cached_price(symbol, period, interval, now, allow_stale_disk=initial_allow_stale_disk)
        force_refresh_cached = (
            cached is not None
            and allow_live_fetch
            and force_live_refresh
            and symbol.endswith((".TW", ".TWO"))
            and (interval.endswith("m") or _is_stale_tw_daily_price(symbol, interval, cached))
        )
        if cached is None or force_refresh_cached:
            missing_symbols.append(symbol)
        else:
            price_map[symbol] = cached

    live_symbols = missing_symbols[:max_live_symbols] if allow_live_fetch else []
    intraday_snapshot_map = _bulk_fetch_tw_intraday_daily_snapshots(live_symbols) if interval == "1d" else {}
    realtime_quote_map = (
        {symbol: _fetch_tw_realtime_quote_snapshot(symbol, interval) for symbol in live_symbols if symbol.endswith((".TW", ".TWO"))}
        if interval.endswith("m")
        else {}
    )
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
                if interval == "1d":
                    df = _merge_tw_daily_realtime_price(symbol, period, df, intraday_snapshot_map.get(symbol, pd.DataFrame()))
                elif interval.endswith("m"):
                    df = _merge_intraday_realtime_quote(symbol, df, realtime_quote_map.get(symbol, pd.DataFrame()))
                if not df.empty:
                    price_map[symbol] = _store_price_cache(symbol, period, interval, df, now).copy()

    still_missing = [symbol for symbol in live_symbols if symbol not in price_map]
    if allow_live_fetch and still_missing:
        max_workers = min(8, len(still_missing))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            results = executor.map(
                lambda sym: (sym, fetch_price(sym, period, interval, allow_stale_disk=False)),
                still_missing,
            )
            price_map.update({symbol: df for symbol, df in results})

    if allow_stale_disk:
        stale_fallback_symbols = [symbol for symbol in symbols if symbol not in price_map or price_map[symbol].empty]
        for symbol in stale_fallback_symbols:
            cached = _cached_price(symbol, period, interval, now, allow_stale_disk=True)
            if cached is not None:
                price_map[symbol] = cached

    return {symbol: price_map.get(symbol, pd.DataFrame()) for symbol in symbols}
