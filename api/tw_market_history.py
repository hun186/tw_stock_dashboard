from __future__ import annotations

import pandas as pd
import requests

from api.market_utils import _symbol_key
from api.tw_market_time import _month_starts, _period_start_date


def _clean_market_number(value) -> float | None:
    if value is None:
        return None
    text = str(value).strip().replace(",", "")
    if text in {"", "--", "-", "X", "除權息"}:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _parse_tw_market_date(value) -> pd.Timestamp | None:
    text = str(value).strip()
    parts = text.split("/")
    if len(parts) != 3:
        return pd.to_datetime(text, errors="coerce")
    try:
        year = int(parts[0])
        if year < 1911:
            year += 1911
        return pd.Timestamp(year=year, month=int(parts[1]), day=int(parts[2]))
    except ValueError:
        return None


def _extract_market_table(payload: dict) -> tuple[list[str], list[list]]:
    fields = payload.get("fields") if isinstance(payload.get("fields"), list) else []
    data = payload.get("data") or payload.get("aaData") or []
    if fields and isinstance(data, list):
        return fields, data
    for table in payload.get("tables", []) if isinstance(payload.get("tables"), list) else []:
        fields = table.get("fields") if isinstance(table, dict) else []
        data = table.get("data") if isinstance(table, dict) else []
        if fields and isinstance(data, list):
            return fields, data
    return [], []


def _market_history_requests(symbol: str, month_start: pd.Timestamp) -> list[tuple[str, dict[str, str]]]:
    symbol_key = _symbol_key(symbol)
    if symbol.endswith(".TW"):
        return [("https://www.twse.com.tw/exchangeReport/STOCK_DAY", {
            "response": "json",
            "date": month_start.strftime("%Y%m%d"),
            "stockNo": symbol_key,
        })]
    if symbol.endswith(".TWO"):
        return [
            ("https://www.tpex.org.tw/www/zh-tw/afterTrading/tradingStock", {
                "response": "json",
                "date": month_start.strftime("%Y/%m/%d"),
                "code": symbol_key,
            }),
            ("https://www.tpex.org.tw/web/stock/aftertrading/daily_trading_info/st43_result.php", {
                "response": "json",
                "date": month_start.strftime("%Y%m%d"),
                "stockNo": symbol_key,
            }),
        ]
    return []


def _fetch_tw_official_daily_price(symbol: str, period: str) -> pd.DataFrame:
    if not symbol.endswith((".TW", ".TWO")):
        return pd.DataFrame()

    today = pd.Timestamp.now(tz="Asia/Taipei").tz_localize(None).normalize()
    start = _period_start_date(period, today)
    rows: list[dict] = []
    session = requests.Session()
    headers = {"User-Agent": "Mozilla/5.0 tw-stock-dashboard/1.0"}

    for month_start in _month_starts(start, today):
        request_infos = _market_history_requests(symbol, month_start)
        if not request_infos:
            return pd.DataFrame()

        fields: list[str] = []
        data: list[list] = []
        for url, params in request_infos:
            try:
                resp = session.get(url, params=params, headers=headers, timeout=10)
                resp.raise_for_status()
                payload = resp.json()
            except Exception:
                continue
            fields, data = _extract_market_table(payload)
            if fields and data:
                break
        if not fields or not data:
            continue
        field_index = {str(name): idx for idx, name in enumerate(fields)}
        aliases = {
            "date": ("日期",),
            "open": ("開盤價", "開盤"),
            "high": ("最高價", "最高"),
            "low": ("最低價", "最低"),
            "close": ("收盤價", "收盤"),
            "volume": ("成交股數", "成交仟股", "成交股"),
        }

        def value_at(row: list, names: tuple[str, ...]):
            for name in names:
                idx = field_index.get(name)
                if idx is not None and idx < len(row):
                    return row[idx]
            return None

        for raw_row in data:
            row = [raw_row.get(field) for field in fields] if isinstance(raw_row, dict) else list(raw_row)
            trade_date = _parse_tw_market_date(value_at(row, aliases["date"]))
            open_value = _clean_market_number(value_at(row, aliases["open"]))
            high_value = _clean_market_number(value_at(row, aliases["high"]))
            low_value = _clean_market_number(value_at(row, aliases["low"]))
            close_value = _clean_market_number(value_at(row, aliases["close"]))
            volume_value = _clean_market_number(value_at(row, aliases["volume"]))
            if trade_date is None or any(v is None for v in (open_value, high_value, low_value, close_value)):
                continue
            if symbol.endswith(".TWO") and volume_value is not None:
                volume_value *= 1000
            rows.append({
                "Date": trade_date,
                "Open": open_value,
                "High": high_value,
                "Low": low_value,
                "Close": close_value,
                "Volume": volume_value or 0.0,
            })

    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows).drop_duplicates(subset=["Date"]).sort_values("Date")
    if start is not None:
        df = df[df["Date"] >= start]
    return df.reset_index(drop=True)
