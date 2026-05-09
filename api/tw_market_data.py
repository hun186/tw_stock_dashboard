from __future__ import annotations

import pandas as pd
from pandas.tseries.offsets import BDay
import requests
import yfinance as yf

from api.market_utils import _prepare_price_df, _symbol_key


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


def _tw_intraday_snapshot_from_minutes(symbol: str, minute_df: pd.DataFrame | None) -> pd.DataFrame:
    intraday_df = _prepare_price_df(symbol, minute_df, "1m")
    if intraday_df.empty:
        return pd.DataFrame()
    intraday_df = _merge_intraday_realtime_quote(symbol, intraday_df)

    expected_date = _expected_latest_tw_daily_date()
    intraday_df = intraday_df[pd.to_datetime(intraday_df["Date"], errors="coerce").dt.normalize() == expected_date]
    if intraday_df.empty:
        return pd.DataFrame()

    return pd.DataFrame([{
        "Date": expected_date,
        "Open": float(intraday_df.iloc[0]["Open"]),
        "High": float(intraday_df["High"].max()),
        "Low": float(intraday_df["Low"].min()),
        "Close": float(intraday_df.iloc[-1]["Close"]),
        "Volume": float(intraday_df["Volume"].fillna(0).sum()),
    }])



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
