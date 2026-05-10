from __future__ import annotations

import pandas as pd
from pandas.tseries.offsets import BDay


def _period_start_date(period: str, today: pd.Timestamp | None = None) -> pd.Timestamp | None:
    today = (today or pd.Timestamp.today()).normalize()
    if period in {"max", "ytd"}:
        return None if period == "max" else pd.Timestamp(year=today.year, month=1, day=1)
    if period.endswith("mo"):
        try:
            months = int(period[:-2])
        except ValueError:
            return today - pd.DateOffset(months=3)
        return today - pd.DateOffset(months=months)
    if period.endswith("y"):
        try:
            years = int(period[:-1])
        except ValueError:
            return today - pd.DateOffset(years=1)
        return today - pd.DateOffset(years=years)
    if period.endswith("d"):
        try:
            days = int(period[:-1])
        except ValueError:
            return today - pd.Timedelta(days=7)
        return today - pd.Timedelta(days=days)
    return today - pd.DateOffset(months=3)


def _month_starts(start: pd.Timestamp | None, end: pd.Timestamp) -> list[pd.Timestamp]:
    if start is None:
        # Keep fallback traffic bounded; Yahoo remains the primary source for max history.
        start = end - pd.DateOffset(years=5)
    current = pd.Timestamp(year=start.year, month=start.month, day=1)
    last = pd.Timestamp(year=end.year, month=end.month, day=1)
    months: list[pd.Timestamp] = []
    while current <= last:
        months.append(current)
        current = current + pd.DateOffset(months=1)
    return months


def _taipei_now(now: pd.Timestamp | None = None) -> pd.Timestamp:
    current = now or pd.Timestamp.now(tz="Asia/Taipei")
    if current.tzinfo is not None:
        current = current.tz_convert("Asia/Taipei").tz_localize(None)
    return pd.Timestamp(current)


def _expected_latest_tw_daily_date(now: pd.Timestamp | None = None) -> pd.Timestamp:
    current = _taipei_now(now)
    today = current.normalize()
    market_has_opened = current.time() >= pd.Timestamp("09:00").time()
    if today.weekday() < 5 and market_has_opened:
        return today
    return (today - BDay(1)).normalize()


def _should_use_tw_intraday_daily_snapshot(now: pd.Timestamp | None = None) -> bool:
    current = _taipei_now(now)
    if current.weekday() >= 5:
        return False
    return pd.Timestamp("09:00").time() <= current.time() < pd.Timestamp("15:00").time()


def _latest_price_date(df: pd.DataFrame) -> pd.Timestamp | None:
    if df.empty or "Date" not in df.columns:
        return None
    dates = pd.to_datetime(df["Date"], errors="coerce").dropna()
    if dates.empty:
        return None
    return pd.Timestamp(dates.max()).normalize()


def _tw_daily_price_needs_official_refresh(df: pd.DataFrame) -> bool:
    latest_date = _latest_price_date(df)
    return latest_date is None or latest_date < _expected_latest_tw_daily_date()


def _is_stale_tw_daily_price(symbol: str, interval: str, df: pd.DataFrame) -> bool:
    return interval == "1d" and symbol.endswith((".TW", ".TWO")) and _tw_daily_price_needs_official_refresh(df)
