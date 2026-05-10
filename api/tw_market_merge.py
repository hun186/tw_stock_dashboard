from __future__ import annotations

import pandas as pd

from api.tw_market_history import _fetch_tw_official_daily_price
from api.tw_market_realtime import _fetch_tw_intraday_daily_snapshot, _merge_price_frames
from api.tw_market_time import (
    _expected_latest_tw_daily_date,
    _latest_price_date,
    _should_use_tw_intraday_daily_snapshot,
    _tw_daily_price_needs_official_refresh,
)


def _merge_tw_daily_realtime_price(symbol: str, period: str, df: pd.DataFrame, intraday_snapshot: pd.DataFrame | None = None) -> pd.DataFrame:
    if not symbol.endswith((".TW", ".TWO")):
        return df

    if _tw_daily_price_needs_official_refresh(df):
        df = _merge_price_frames(df, _fetch_tw_official_daily_price(symbol, period))

    if _should_use_tw_intraday_daily_snapshot():
        snapshot_df = intraday_snapshot if intraday_snapshot is not None else _fetch_tw_intraday_daily_snapshot(symbol)
        if _latest_price_date(snapshot_df) == _expected_latest_tw_daily_date():
            df = _merge_price_frames(df, snapshot_df)

    return df
