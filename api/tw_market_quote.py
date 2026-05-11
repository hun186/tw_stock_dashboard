from __future__ import annotations

import pandas as pd
import requests

from api.market_utils import _symbol_key
from api.tw_market_history import _clean_market_number
from api.tw_market_time import _expected_latest_tw_daily_date, _should_use_tw_intraday_daily_snapshot


def _tw_realtime_quote_request(symbol: str) -> tuple[str, dict[str, str]] | None:
    if symbol.endswith(".TW"):
        exchange = "tse"
    elif symbol.endswith(".TWO"):
        exchange = "otc"
    else:
        return None
    symbol_key = _symbol_key(symbol)
    return (
        "https://mis.twse.com.tw/stock/api/getStockInfo.jsp",
        {"ex_ch": f"{exchange}_{symbol_key}.tw", "json": "1", "delay": "0"},
    )


def _parse_tw_quote_datetime(item: dict) -> pd.Timestamp | None:
    tlong = item.get("tlong")
    try:
        if tlong not in {None, "", "-"}:
            parsed = pd.to_datetime(int(tlong), unit="ms", utc=True).tz_convert("Asia/Taipei").tz_localize(None)
            return pd.Timestamp(parsed)
    except (TypeError, ValueError, OverflowError):
        pass

    trade_date = str(item.get("d") or "").strip()
    trade_time = str(item.get("t") or item.get("%") or "").strip()
    if len(trade_date) == 8 and trade_time:
        parsed = pd.to_datetime(f"{trade_date} {trade_time}", format="%Y%m%d %H:%M:%S", errors="coerce")
        if not pd.isna(parsed):
            return pd.Timestamp(parsed)
    return None


def _fetch_tw_realtime_quote_snapshot(symbol: str, interval: str) -> pd.DataFrame:
    request_info = _tw_realtime_quote_request(symbol)
    if request_info is None or not _should_use_tw_intraday_daily_snapshot():
        return pd.DataFrame()

    url, params = request_info
    try:
        session = requests.Session()
        resp = session.get(
            url,
            params=params,
            headers={
                "User-Agent": "Mozilla/5.0 tw-stock-dashboard/1.0",
                "Referer": "https://mis.twse.com.tw/stock/fibest.jsp",
            },
            timeout=5,
        )
        resp.raise_for_status()
        payload = resp.json()
    except Exception:
        return pd.DataFrame()

    items = payload.get("msgArray") if isinstance(payload, dict) else None
    item = items[0] if isinstance(items, list) and items and isinstance(items[0], dict) else {}
    quote_time = _parse_tw_quote_datetime(item)
    if quote_time is None or quote_time.normalize() != _expected_latest_tw_daily_date():
        return pd.DataFrame()

    close_value = _clean_market_number(item.get("z")) or _clean_market_number(item.get("pz"))
    open_value = _clean_market_number(item.get("o")) or close_value
    high_value = _clean_market_number(item.get("h")) or close_value
    low_value = _clean_market_number(item.get("l")) or close_value
    volume_value = _clean_market_number(item.get("v"))
    if close_value is None or any(v is None for v in (open_value, high_value, low_value)):
        return pd.DataFrame()

    if interval.endswith("m"):
        quote_date = quote_time.floor("min")
        row = {
            "Date": quote_date,
            "Open": close_value,
            "High": close_value,
            "Low": close_value,
            "Close": close_value,
            "Volume": 0.0,
        }
    else:
        quote_date = quote_time.normalize()
        row = {
            "Date": quote_date,
            "Open": open_value,
            "High": high_value,
            "Low": low_value,
            "Close": close_value,
            "Volume": (volume_value or 0.0) * 1000,
        }
    return pd.DataFrame([row])
