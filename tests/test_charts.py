from __future__ import annotations

import unittest

import pandas as pd

from api.charts import make_chart_html


def chart_df() -> pd.DataFrame:
    return pd.DataFrame({
        "Date": pd.date_range("2026-05-01", periods=3),
        "Open": [100.0, 101.0, 102.0],
        "High": [102.0, 103.0, 104.0],
        "Low": [99.0, 100.0, 101.0],
        "Close": [101.0, 102.0, 103.0],
        "Volume": [1000, 1200, 1300],
        "MA5": [100.5, 101.5, 102.5],
        "MA20": [100.0, 101.0, 102.0],
        "MA60": [99.5, 100.5, 101.5],
        "VMA5": [1000, 1100, 1200],
        "VMA20": [900, 1000, 1100],
        "VMA60": [800, 900, 1000],
    })


class ChartVisibilityTests(unittest.TestCase):
    def test_can_hide_price_candlestick_while_keeping_ma_lines(self) -> None:
        html = make_chart_html(chart_df(), "測試", show_volume=False, show_ma=True, show_price=False)

        self.assertNotIn("candlestick", html)
        self.assertIn("MA5", html)


if __name__ == "__main__":
    unittest.main()
