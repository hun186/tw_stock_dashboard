from __future__ import annotations

import unittest
from unittest.mock import patch

import pandas as pd

from api import dashboard_analysis


def price_df(date: str, close: float) -> pd.DataFrame:
    return pd.DataFrame({
        "Date": [pd.Timestamp(date)],
        "Open": [close],
        "High": [close],
        "Low": [close],
        "Close": [close],
        "Volume": [1000],
    })


class DashboardAnalysisCacheTests(unittest.TestCase):
    def setUp(self) -> None:
        dashboard_analysis.STOCK_ANALYSIS_CACHE.clear()

    def test_analysis_cache_refreshes_when_latest_price_frame_changes(self) -> None:
        stale = price_df("2026-05-29", 100.0)
        live = price_df("2026-06-01", 101.0)

        with patch.object(dashboard_analysis, "add_indicators", side_effect=lambda df: df), \
             patch.object(dashboard_analysis, "analyze_stock_signal", return_value={"bucket": "neutral", "message": "⚪ 中性", "score": 0}):
            first = dashboard_analysis.build_stock_analysis(
                "2330.TW", "6mo", "6mo", "1d", "6mo", stale, pd.DataFrame(), False
            )
            second = dashboard_analysis.build_stock_analysis(
                "2330.TW", "6mo", "6mo", "1d", "6mo", live, pd.DataFrame(), False
            )

        self.assertEqual(first["df"].iloc[-1]["Date"], pd.Timestamp("2026-05-29"))
        self.assertEqual(second["df"].iloc[-1]["Date"], pd.Timestamp("2026-06-01"))
        self.assertEqual(second["close_text"], "101.00")


if __name__ == "__main__":
    unittest.main()
