from __future__ import annotations

import unittest
from unittest.mock import patch

import pandas as pd

from api import price_service


def price_df(date: str, close: float = 100.0) -> pd.DataFrame:
    return pd.DataFrame({
        "Date": [pd.Timestamp(date)],
        "Open": [close],
        "High": [close],
        "Low": [close],
        "Close": [close],
        "Volume": [1000],
    })


class PriceServiceLiveRefreshTests(unittest.TestCase):
    def test_prefetch_refreshes_stale_daily_cache_without_forced_live_refresh(self) -> None:
        stocks = pd.DataFrame({"symbol": ["2330.TW"]})
        stale = price_df("2026-05-29", 100.0)
        live = price_df("2026-06-01", 101.0).set_index("Date")

        with patch.object(price_service, "_cached_price", return_value=stale), \
             patch.object(price_service, "_is_stale_tw_daily_price", return_value=True), \
             patch.object(price_service.yf, "download", return_value=live), \
             patch.object(price_service, "_merge_tw_daily_realtime_price", side_effect=lambda _symbol, _period, df, _snapshot=None: df):
            result = price_service.prefetch_price_data(
                stocks,
                "6mo",
                "1d",
                allow_live_fetch=True,
                allow_stale_disk=True,
                max_live_symbols=80,
            )

        self.assertEqual(result["2330.TW"]["Date"].max(), pd.Timestamp("2026-06-01"))
        self.assertEqual(float(result["2330.TW"].iloc[-1]["Close"]), 101.0)

    def test_prefetch_refreshes_stale_cache_synchronously_when_forced(self) -> None:
        stocks = pd.DataFrame({"symbol": ["2330.TW"]})
        stale = price_df("2026-05-29", 100.0)
        live = price_df("2026-06-01", 101.0).set_index("Date")

        with patch.object(price_service, "_cached_price", return_value=stale), \
             patch.object(price_service, "_is_stale_tw_daily_price", return_value=True), \
             patch.object(price_service.yf, "download", return_value=live), \
             patch.object(price_service, "_merge_tw_daily_realtime_price", side_effect=lambda _symbol, _period, df, _snapshot=None: df):
            result = price_service.prefetch_price_data(
                stocks,
                "6mo",
                "1d",
                allow_live_fetch=True,
                allow_stale_disk=True,
                max_live_symbols=80,
                force_live_refresh=True,
            )

        self.assertEqual(result["2330.TW"]["Date"].max(), pd.Timestamp("2026-06-01"))
        self.assertEqual(float(result["2330.TW"].iloc[-1]["Close"]), 101.0)

    def test_prefetch_keeps_stale_daily_cache_when_live_fetch_is_disabled(self) -> None:
        stocks = pd.DataFrame({"symbol": ["2330.TW"]})
        stale = price_df("2026-05-29", 100.0)

        with patch.object(price_service, "_cached_price", return_value=stale), \
             patch.object(price_service, "_is_stale_tw_daily_price", return_value=True), \
             patch.object(price_service.yf, "download") as download_mock:
            result = price_service.prefetch_price_data(
                stocks,
                "6mo",
                "1d",
                allow_live_fetch=False,
                allow_stale_disk=True,
                max_live_symbols=80,
            )

        self.assertEqual(result["2330.TW"]["Date"].max(), pd.Timestamp("2026-05-29"))
        download_mock.assert_not_called()

    def test_forced_refresh_updates_intraday_cache_even_when_memory_cache_is_fresh(self) -> None:
        stocks = pd.DataFrame({"symbol": ["2330.TW"]})
        stale = price_df("2026-05-29 13:30", 100.0)
        live = price_df("2026-06-01 09:01", 101.0).set_index("Date")

        with patch.object(price_service, "_cached_price", return_value=stale), \
             patch.object(price_service.yf, "download", return_value=live), \
             patch.object(price_service, "_fetch_tw_realtime_quote_snapshot", return_value=pd.DataFrame()):
            result = price_service.prefetch_price_data(
                stocks,
                "1d",
                "1m",
                allow_live_fetch=True,
                allow_stale_disk=True,
                max_live_symbols=80,
                force_live_refresh=True,
            )

        self.assertEqual(result["2330.TW"]["Date"].max(), pd.Timestamp("2026-06-01 09:01"))
        self.assertEqual(float(result["2330.TW"].iloc[-1]["Close"]), 101.0)

    def test_forced_refresh_attempts_bounded_live_fetch_even_when_normal_live_fetch_is_disabled(self) -> None:
        stocks = pd.DataFrame({"symbol": ["2330.TW"]})
        live = price_df("2026-06-01", 101.0).set_index("Date")

        with patch.object(price_service, "_cached_price", return_value=None), \
             patch.object(price_service.yf, "download", return_value=live), \
             patch.object(price_service, "_merge_tw_daily_realtime_price", side_effect=lambda _symbol, _period, df, _snapshot=None: df):
            result = price_service.prefetch_price_data(
                stocks,
                "6mo",
                "1d",
                allow_live_fetch=False,
                allow_stale_disk=True,
                max_live_symbols=80,
                force_live_refresh=True,
            )

        self.assertEqual(result["2330.TW"]["Date"].max(), pd.Timestamp("2026-06-01"))
        self.assertEqual(float(result["2330.TW"].iloc[-1]["Close"]), 101.0)


if __name__ == "__main__":
    unittest.main()
