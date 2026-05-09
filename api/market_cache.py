from __future__ import annotations

import time
from pathlib import Path

import pandas as pd

from api.constants import STATIC_CACHE_DIR


PRICE_CACHE: dict[tuple[str, str, str], tuple[float, pd.DataFrame]] = {}
TARGET_PRICE_CACHE: dict[str, tuple[float, str]] = {}


def _cache_ttl_seconds(interval: str) -> int:
    if interval == "1m":
        return 60
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
