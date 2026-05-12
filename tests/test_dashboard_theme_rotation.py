from __future__ import annotations

import unittest
from collections import namedtuple
from unittest.mock import patch

import pandas as pd

from api import dashboard_app
from api.dashboard_theme_rotation import build_theme_rotation_rows, render_theme_rotation_radar


StockRow = namedtuple("StockRow", ["symbol", "name", "group", "subgroup"])
MinimalRow = namedtuple("MinimalRow", ["symbol", "name"])


class DashboardThemeRotationTests(unittest.TestCase):
    def test_build_theme_rotation_rows_aggregates_signal_buckets_and_scores(self) -> None:
        rows = build_theme_rotation_rows([
            {
                "row": StockRow("2330.TW", "台積電", "AI晶片", "先進製程"),
                "bucket": "bull",
                "sort_metrics": {"change_pct": 4.0, "signal_score": 90},
            },
            {
                "row": StockRow("3443.TW", "創意", "AI晶片", "先進製程"),
                "bucket": "observe",
                "sort_metrics": {"change_pct": 2.0, "signal_score": 40},
            },
            {
                "row": StockRow("2382.TW", "廣達", "AI伺服器", "組裝"),
                "bucket": "warn",
                "sort_metrics": {"change_pct": -1.0, "signal_score": -20},
            },
            {
                "row": StockRow("2317.TW", "鴻海", "AI伺服器", "組裝"),
                "bucket": "bear",
                "sort_metrics": {"change_pct": -3.0, "signal_score": -70},
            },
            {
                "row": StockRow("2356.TW", "英業達", "AI伺服器", "組裝"),
                "bucket": "neutral",
                "sort_metrics": {"change_pct": 0.0, "signal_score": 0},
            },
        ])

        ai_chip = next(row for row in rows if row.group == "AI晶片")
        self.assertEqual(ai_chip.stock_count, 2)
        self.assertEqual(ai_chip.bull_count, 1)
        self.assertEqual(ai_chip.observe_count, 1)
        self.assertEqual(ai_chip.warn_count, 0)
        self.assertEqual(ai_chip.bear_count, 0)
        self.assertEqual(ai_chip.neutral_count, 0)
        self.assertEqual(ai_chip.avg_change_pct, 3.0)
        self.assertEqual(ai_chip.avg_signal_score, 65.0)
        self.assertGreater(ai_chip.heat_score, 0)

        server = next(row for row in rows if row.group == "AI伺服器")
        self.assertEqual(server.stock_count, 3)
        self.assertEqual(server.warn_count, 1)
        self.assertEqual(server.bear_count, 1)
        self.assertEqual(server.neutral_count, 1)

    def test_theme_rotation_rows_are_safe_for_empty_and_missing_fields(self) -> None:
        self.assertEqual(build_theme_rotation_rows([]), [])

        rows = build_theme_rotation_rows([
            {"row": MinimalRow("0000.TW", "缺欄位"), "bucket": "unknown", "sort_metrics": {}},
            {"row": None, "sort_metrics": {"change_pct": "bad", "signal_score": None}},
        ])

        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row.group, "")
        self.assertEqual(row.subgroup, "")
        self.assertEqual(row.stock_count, 2)
        self.assertEqual(row.neutral_count, 2)
        self.assertEqual(row.avg_change_pct, 0.0)
        self.assertEqual(row.avg_signal_score, 0.0)

        html = render_theme_rotation_radar([])
        self.assertIn("尚無符合目前篩選的已分析股票可聚合題材輪動", html)
        self.assertIn("data-collapsible-section='themeRadar'", html)
        self.assertIn("data-collapse-target='themeRadarBody'", html)

    def test_dashboard_renders_theme_heat_ranking_and_click_filter_controls(self) -> None:
        file_watchlist = pd.DataFrame([
            {"symbol": "2330.TW", "name": "台積電", "group": "AI晶片", "subgroup": "先進製程"},
            {"symbol": "2382.TW", "name": "廣達", "group": "AI伺服器", "subgroup": "組裝"},
        ])
        llm_watchlist = pd.DataFrame(columns=["symbol", "name", "group", "subgroup"])
        industry_df = pd.DataFrame(columns=["industry", "industry_label", "symbol", "name", "group", "subgroup"])
        price_df = pd.DataFrame({
            "Date": pd.date_range("2026-05-01", periods=25),
            "Open": [100.0] * 25,
            "High": [102.0] * 25,
            "Low": [99.0] * 25,
            "Close": [100.0 + i for i in range(25)],
            "Volume": [1000 + i * 10 for i in range(25)],
        })

        with patch.object(dashboard_app, "load_watchlist", return_value=file_watchlist), \
            patch.object(dashboard_app, "load_gemini_agent_group_map", return_value=pd.DataFrame(columns=["symbol", "name", "group", "subgroup"])), \
            patch.object(dashboard_app, "load_llm_group_map", return_value=llm_watchlist), \
            patch.object(dashboard_app, "load_twse_industry_map", return_value=industry_df), \
            patch.object(dashboard_app, "prefetch_price_data", return_value={"2330.TW": price_df, "2382.TW": price_df}):
            response = b"".join(dashboard_app.app({"QUERY_STRING": ""}, lambda *_args: None)).decode("utf-8")

        self.assertIn("題材熱度榜", response)
        self.assertIn("平均漲跌", response)
        self.assertIn("平均訊號", response)
        self.assertIn("熱度", response)
        self.assertIn("偏多", response)
        self.assertIn("觀察", response)
        self.assertIn("警示", response)
        self.assertIn("轉弱", response)
        self.assertIn("中性", response)
        self.assertIn("AI晶片", response)
        self.assertIn("AI伺服器", response)
        self.assertIn("applyThemeRadarFilter", response)
        self.assertIn("submitConfig(overrides)", response)
        self.assertIn("onclick='applyThemeRadarFilter(&quot;AI晶片&quot;, &quot;先進製程&quot;)'", response)
        self.assertIn("data-collapsible-section='controlPanel'", response)
        self.assertIn("上方控制區", response)
        self.assertIn("data-collapsible-section='overview'", response)
        self.assertIn("data-collapsible-section='charts'", response)
        self.assertIn("initCollapsibleSections()", response)


if __name__ == "__main__":
    unittest.main()
