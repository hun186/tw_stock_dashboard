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


class PriceServiceStaleWhileRefreshTests(unittest.TestCase):
    def test_prefetch_returns_stale_cache_immediately_and_schedules_refresh(self) -> None:
        stocks = pd.DataFrame({"symbol": ["2330.TW"]})
        stale = price_df("2026-05-05", 100.0)

        with patch.object(price_service, "_cached_price", side_effect=[stale, stale]), \
             patch.object(price_service, "_is_stale_tw_daily_price", return_value=True), \
             patch.object(price_service, "_refresh_symbols_in_background") as refresh_mock:
            result = price_service.prefetch_price_data(
                stocks,
                "6mo",
                "1d",
                allow_live_fetch=True,
                allow_stale_disk=True,
                max_live_symbols=80,
            )

        self.assertEqual(result["2330.TW"]["Date"].max(), pd.Timestamp("2026-05-05"))
        refresh_mock.assert_called_once_with(["2330.TW"], "6mo", "1d")


if __name__ == "__main__":
    unittest.main()
