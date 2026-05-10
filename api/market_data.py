from __future__ import annotations

from api.market_cache import (
    PRICE_CACHE,
    TARGET_PRICE_CACHE,
    _cache_ttl_seconds,
    _cached_price,
    _disk_cache_max_age_seconds,
    _disk_cache_path,
    _load_disk_cache,
    _store_price_cache,
)
import requests
import yfinance as yf

from api import price_service as _price_service
from api import tw_market_data as _tw_market_data
from api import tw_market_history as _tw_market_history
from api import tw_market_merge as _tw_market_merge
from api import tw_market_realtime as _tw_market_realtime
from api import tw_market_time as _tw_market_time
from api.market_utils import _prepare_price_df, _symbol_key, resolve_price_params, trim_display_df
from api.price_service import get_price_cache_ttl_seconds
from api.tw_market_data import (
    _bulk_fetch_tw_intraday_daily_snapshots,
    _clean_market_number,
    _expected_latest_tw_daily_date,
    _extract_market_table,
    _fetch_tw_intraday_daily_snapshot,
    _fetch_tw_official_daily_price,
    _fetch_tw_realtime_quote_snapshot,
    _is_stale_tw_daily_price,
    _latest_price_date,
    _market_history_requests,
    _merge_intraday_realtime_quote,
    _merge_price_frames,
    _merge_tw_daily_realtime_price,
    _month_starts,
    _parse_tw_market_date,
    _parse_tw_quote_datetime,
    _period_start_date,
    _should_use_tw_intraday_daily_snapshot,
    _taipei_now,
    _tw_daily_price_needs_official_refresh,
    _tw_intraday_snapshot_from_minutes,
    _tw_realtime_quote_request,
)


def _sync_compat_dependencies() -> None:
    # Keep legacy monkeypatches against api.market_data working after the split.
    _tw_market_data._expected_latest_tw_daily_date = _expected_latest_tw_daily_date
    _tw_market_data._should_use_tw_intraday_daily_snapshot = _should_use_tw_intraday_daily_snapshot
    _tw_market_data._fetch_tw_official_daily_price = _fetch_tw_official_daily_price
    _tw_market_time._expected_latest_tw_daily_date = _expected_latest_tw_daily_date
    _tw_market_time._should_use_tw_intraday_daily_snapshot = _should_use_tw_intraday_daily_snapshot
    _tw_market_realtime._expected_latest_tw_daily_date = _expected_latest_tw_daily_date
    _tw_market_realtime._should_use_tw_intraday_daily_snapshot = _should_use_tw_intraday_daily_snapshot
    _tw_market_merge._expected_latest_tw_daily_date = _expected_latest_tw_daily_date
    _tw_market_merge._should_use_tw_intraday_daily_snapshot = _should_use_tw_intraday_daily_snapshot
    _tw_market_merge._fetch_tw_official_daily_price = _fetch_tw_official_daily_price
    _tw_market_history._period_start_date = _period_start_date
    _tw_market_history._month_starts = _month_starts
    _price_service._cached_price = _cached_price
    _price_service._store_price_cache = _store_price_cache
    _price_service._is_stale_tw_daily_price = _is_stale_tw_daily_price
    _price_service._merge_tw_daily_realtime_price = _merge_tw_daily_realtime_price
    _price_service._merge_intraday_realtime_quote = _merge_intraday_realtime_quote
    _price_service._bulk_fetch_tw_intraday_daily_snapshots = _bulk_fetch_tw_intraday_daily_snapshots
    _price_service._fetch_tw_realtime_quote_snapshot = _fetch_tw_realtime_quote_snapshot


def fetch_price(symbol: str, period: str = "3mo", interval: str = "1d", *, allow_stale_disk: bool = False):
    _sync_compat_dependencies()
    return _price_service.fetch_price(symbol, period, interval, allow_stale_disk=allow_stale_disk)


def fetch_target_price(symbol: str) -> str:
    return _price_service.fetch_target_price(symbol)


def prefetch_price_data(*args, **kwargs):
    _sync_compat_dependencies()
    return _price_service.prefetch_price_data(*args, **kwargs)


def _fetch_tw_realtime_quote_snapshot(symbol: str, interval: str):
    _sync_compat_dependencies()
    return _tw_market_data._fetch_tw_realtime_quote_snapshot(symbol, interval)


__all__ = [
    "PRICE_CACHE",
    "TARGET_PRICE_CACHE",
    "_bulk_fetch_tw_intraday_daily_snapshots",
    "_cache_ttl_seconds",
    "_cached_price",
    "_clean_market_number",
    "_disk_cache_max_age_seconds",
    "_disk_cache_path",
    "_expected_latest_tw_daily_date",
    "_extract_market_table",
    "_fetch_tw_intraday_daily_snapshot",
    "_fetch_tw_official_daily_price",
    "_fetch_tw_realtime_quote_snapshot",
    "_is_stale_tw_daily_price",
    "_latest_price_date",
    "_load_disk_cache",
    "_market_history_requests",
    "_merge_intraday_realtime_quote",
    "_merge_price_frames",
    "_merge_tw_daily_realtime_price",
    "_month_starts",
    "_parse_tw_market_date",
    "_parse_tw_quote_datetime",
    "_period_start_date",
    "_prepare_price_df",
    "_should_use_tw_intraday_daily_snapshot",
    "_store_price_cache",
    "_symbol_key",
    "_taipei_now",
    "_tw_daily_price_needs_official_refresh",
    "_tw_intraday_snapshot_from_minutes",
    "_tw_realtime_quote_request",
    "fetch_price",
    "fetch_target_price",
    "get_price_cache_ttl_seconds",
    "prefetch_price_data",
    "resolve_price_params",
    "trim_display_df",
]
