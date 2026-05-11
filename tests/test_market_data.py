from __future__ import annotations

import unittest
from unittest.mock import patch

import pandas as pd

from api import market_data


def price_df(date: str, close: float = 100.0) -> pd.DataFrame:
    return pd.DataFrame({
        "Date": [pd.Timestamp(date)],
        "Open": [close],
        "High": [close],
        "Low": [close],
        "Close": [close],
        "Volume": [1000],
    })


def minute_df() -> pd.DataFrame:
    idx = pd.to_datetime([
        "2026-05-07 09:00",
        "2026-05-07 10:30",
        "2026-05-07 12:00",
    ]).tz_localize("Asia/Taipei")
    return pd.DataFrame({
        "Open": [101.0, 102.0, 104.0],
        "High": [102.0, 104.0, 106.0],
        "Low": [100.0, 101.0, 103.0],
        "Close": [102.0, 104.0, 105.0],
        "Volume": [1000, 2000, 3000],
    }, index=idx.rename("Date"))


class MarketDataFreshnessTests(unittest.TestCase):
    def setUp(self) -> None:
        market_data.PRICE_CACHE.clear()

    def test_one_minute_interval_cache_ttl_is_one_minute(self) -> None:
        self.assertEqual(market_data.get_price_cache_ttl_seconds("1m"), 60)

    def test_expected_latest_tw_daily_date_uses_previous_business_day_before_market_opens(self) -> None:
        latest = market_data._expected_latest_tw_daily_date(pd.Timestamp("2026-05-07 00:12", tz="Asia/Taipei"))

        self.assertEqual(latest, pd.Timestamp("2026-05-06"))

    def test_expected_latest_tw_daily_date_uses_today_after_market_opens(self) -> None:
        latest = market_data._expected_latest_tw_daily_date(pd.Timestamp("2026-05-07 12:00", tz="Asia/Taipei"))

        self.assertEqual(latest, pd.Timestamp("2026-05-07"))

    def test_fetch_price_appends_intraday_snapshot_as_provisional_daily_close(self) -> None:
        stale = price_df("2026-05-06", 100.0)
        daily = price_df("2026-05-06", 100.0).set_index("Date")

        with patch.object(market_data, "_expected_latest_tw_daily_date", return_value=pd.Timestamp("2026-05-07")), \
             patch.object(market_data, "_should_use_tw_intraday_daily_snapshot", return_value=True), \
             patch.object(market_data, "_cached_price", return_value=stale), \
             patch.object(market_data, "_fetch_tw_official_daily_price", return_value=pd.DataFrame()), \
             patch.object(market_data, "_fetch_tw_realtime_quote_snapshot", return_value=pd.DataFrame()), \
             patch.object(market_data.yf, "download", side_effect=[daily, minute_df()]):
            result = market_data.fetch_price("2330.TW", "6mo", "1d", allow_stale_disk=True)

        self.assertEqual(result["Date"].max(), pd.Timestamp("2026-05-07"))
        self.assertEqual(float(result.iloc[-1]["Open"]), 101.0)
        self.assertEqual(float(result.iloc[-1]["High"]), 106.0)
        self.assertEqual(float(result.iloc[-1]["Low"]), 100.0)
        self.assertEqual(float(result.iloc[-1]["Close"]), 105.0)
        self.assertEqual(float(result.iloc[-1]["Volume"]), 6000.0)

    def test_intraday_daily_snapshot_prefers_official_quote_volume(self) -> None:
        quote = pd.DataFrame([{
            "Date": pd.Timestamp("2026-05-07"),
            "Open": 101.0,
            "High": 108.0,
            "Low": 100.0,
            "Close": 107.0,
            "Volume": 123000.0,
        }])

        with patch.object(market_data._tw_market_realtime, "_expected_latest_tw_daily_date", return_value=pd.Timestamp("2026-05-07")), \
             patch.object(market_data._tw_market_realtime, "_fetch_tw_realtime_quote_snapshot", return_value=quote):
            result = market_data._tw_intraday_snapshot_from_minutes("2330.TW", minute_df())

        self.assertEqual(result.iloc[0]["Date"], pd.Timestamp("2026-05-07"))
        self.assertEqual(float(result.iloc[0]["Close"]), 107.0)
        self.assertEqual(float(result.iloc[0]["High"]), 108.0)
        self.assertEqual(float(result.iloc[0]["Volume"]), 123000.0)

    def test_intraday_realtime_quote_appends_newer_current_bar(self) -> None:
        base = minute_df().reset_index()
        quote = pd.DataFrame([{
            "Date": pd.Timestamp("2026-05-07 12:50"),
            "Open": 107.0,
            "High": 107.0,
            "Low": 107.0,
            "Close": 107.0,
            "Volume": 0.0,
        }])

        result = market_data._merge_intraday_realtime_quote("2330.TW", base, quote)

        self.assertEqual(result["Date"].max(), pd.Timestamp("2026-05-07 12:50"))
        self.assertEqual(float(result.iloc[-1]["Close"]), 107.0)

    def test_fetch_tw_realtime_quote_snapshot_parses_twse_mis_payload(self) -> None:
        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {
                    "msgArray": [{
                        "tlong": str(int(pd.Timestamp("2026-05-07 12:50", tz="Asia/Taipei").timestamp() * 1000)),
                        "z": "107.00",
                        "o": "101.00",
                        "h": "108.00",
                        "l": "100.00",
                        "v": "123",
                    }]
                }

        with patch.object(market_data, "_expected_latest_tw_daily_date", return_value=pd.Timestamp("2026-05-07")), \
             patch.object(market_data, "_should_use_tw_intraday_daily_snapshot", return_value=True), \
             patch.object(market_data.requests.Session, "get", return_value=FakeResponse()):
            result = market_data._fetch_tw_realtime_quote_snapshot("2330.TW", "1d")

        self.assertEqual(result.iloc[0]["Date"], pd.Timestamp("2026-05-07"))
        self.assertEqual(float(result.iloc[0]["Close"]), 107.0)
        self.assertEqual(float(result.iloc[0]["Volume"]), 123000.0)

    def test_prefetch_refreshes_stale_daily_cache_when_live_fetch_is_allowed(self) -> None:
        stocks = pd.DataFrame({"symbol": ["2330.TW"]})
        stale = price_df("2026-05-05", 100.0)
        live = price_df("2026-05-06", 101.0).set_index("Date")

        with patch.object(market_data, "_expected_latest_tw_daily_date", return_value=pd.Timestamp("2026-05-06")), \
             patch.object(market_data, "_should_use_tw_intraday_daily_snapshot", return_value=False), \
             patch.object(market_data, "_cached_price", return_value=stale), \
             patch.object(market_data.yf, "download", return_value=live), \
             patch.object(market_data, "_fetch_tw_official_daily_price", return_value=pd.DataFrame()):
            result = market_data.prefetch_price_data(
                stocks,
                "6mo",
                "1d",
                allow_live_fetch=True,
                allow_stale_disk=True,
                max_live_symbols=80,
            )

        self.assertEqual(result["2330.TW"]["Date"].max(), pd.Timestamp("2026-05-06"))
        self.assertEqual(float(result["2330.TW"].iloc[-1]["Close"]), 101.0)

    def test_fetch_price_uses_stale_cache_only_after_live_refresh_fails(self) -> None:
        stale = price_df("2026-05-05", 100.0)

        with patch.object(market_data, "_expected_latest_tw_daily_date", return_value=pd.Timestamp("2026-05-06")), \
             patch.object(market_data, "_should_use_tw_intraday_daily_snapshot", return_value=False), \
             patch.object(market_data, "_cached_price", return_value=stale), \
             patch.object(market_data.yf, "download", return_value=pd.DataFrame()), \
             patch.object(market_data, "_fetch_tw_official_daily_price", return_value=pd.DataFrame()):
            result = market_data.fetch_price("2330.TW", "6mo", "1d", allow_stale_disk=True)

        self.assertEqual(result["Date"].max(), pd.Timestamp("2026-05-05"))


if __name__ == "__main__":
    unittest.main()
