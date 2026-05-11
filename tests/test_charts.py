from __future__ import annotations

import unittest

import pandas as pd

from api.charts import _volume_in_lots, make_chart_html


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
    def test_hiding_price_candlestick_removes_price_panel_but_keeps_volume_panel(self) -> None:
        html = make_chart_html(chart_df(), "測試", show_volume=True, show_ma=True, show_price=False)

        self.assertNotIn("candlestick", html)
        self.assertNotIn("價格", html)
        self.assertNotIn("\\u50f9\\u683c", html)
        self.assertNotIn('"name":"MA5"', html)
        self.assertIn("\\u91cfK\\u7dda\\uff08\\u5f35\\uff09", html)
        self.assertIn("\\u6210\\u4ea4\\u91cf\\uff08\\u5f35\\uff09", html)
        self.assertIn("VMA5\\uff08\\u5f35\\uff09", html)

    def test_volume_values_are_converted_from_shares_to_lots(self) -> None:
        lots = _volume_in_lots(chart_df()["Volume"])

        self.assertEqual(lots.tolist(), [1.0, 1.2, 1.3])

    def test_hiding_price_and_volume_returns_no_chart(self) -> None:
        html = make_chart_html(chart_df(), "測試", show_volume=False, show_ma=True, show_price=False)

        self.assertEqual(html, "")


if __name__ == "__main__":
    unittest.main()
