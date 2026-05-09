from __future__ import annotations

import unittest
from unittest.mock import patch

import pandas as pd

from api import dashboard_app


class DashboardThemeMetadataTests(unittest.TestCase):
    def test_gemini_summary_and_reference_render_and_search_metadata(self) -> None:
        file_watchlist = pd.DataFrame([
            {"symbol": "2330.TW", "name": "台積電", "group": "手動題材", "subgroup": "手動次題材"},
        ])
        gemini_watchlist = pd.DataFrame([
            {
                "symbol": "2330.TW",
                "name": "台積電",
                "group": "AI晶片",
                "subgroup": "先進製程",
                "summary": "CoWoS 先進封裝受惠 AI 加速器需求",
                "reference_url": "https://example.com/tsmc-ai",
            },
        ])
        llm_watchlist = pd.DataFrame(columns=["symbol", "name", "group", "subgroup"])
        industry_df = pd.DataFrame(columns=["industry", "industry_label", "symbol", "name", "group", "subgroup"])

        price_df = pd.DataFrame({
            "Date": pd.date_range("2026-05-01", periods=3),
            "Open": [100.0, 101.0, 102.0],
            "High": [102.0, 103.0, 104.0],
            "Low": [99.0, 100.0, 101.0],
            "Close": [101.0, 102.0, 103.0],
            "Volume": [1000, 1200, 1300],
        })

        with patch.object(dashboard_app, "load_watchlist", return_value=file_watchlist), \
            patch.object(dashboard_app, "load_gemini_agent_group_map", return_value=gemini_watchlist), \
            patch.object(dashboard_app, "load_llm_group_map", return_value=llm_watchlist), \
            patch.object(dashboard_app, "load_twse_industry_map", return_value=industry_df), \
            patch.object(dashboard_app, "prefetch_price_data", return_value={"2330.TW": price_df}):
            response = b"".join(dashboard_app.app({"QUERY_STRING": "stock_meta_stock=CoWoS"}, lambda *_args: None)).decode("utf-8")

        self.assertIn("題材摘要", response)
        self.assertIn("來源", response)
        self.assertIn("CoWoS 先進封裝受惠 AI 加速器需求", response)
        self.assertIn("https://example.com/tsmc-ai", response)
        self.assertIn("來源連結", response)
        self.assertIn(".theme-summary-cell{display:none;white-space:normal", response)
        self.assertIn("border-left:1px solid #e2e8f0", response)
        self.assertIn(".show-table-theme-meta .theme-summary-cell,.show-table-theme-meta .source-cell{display:table-cell}", response)
        self.assertIn(".show-card-theme-meta .theme-card-meta{display:block}", response)
        self.assertNotIn("theme-title-trigger", response)
        self.assertIn("data-summary='CoWoS 先進封裝受惠 AI 加速器需求'", response)
        self.assertIn('"summary": "CoWoS 先進封裝受惠 AI 加速器需求"', response)
        self.assertIn("stock.symbol, stock.name, stock.group, stock.subgroup, stock.summary", response)
        self.assertIn("summary.includes(token)", response)
        self.assertIn("符合股數</span><span class='summary-value'>1 檔", response)

    def test_legacy_metadata_without_summary_renders_dash(self) -> None:
        file_watchlist = pd.DataFrame([
            {"symbol": "2317.TW", "name": "鴻海", "group": "AI伺服器", "subgroup": "組裝"},
        ])
        llm_watchlist = pd.DataFrame(columns=["symbol", "name", "group", "subgroup"])
        industry_df = pd.DataFrame(columns=["industry", "industry_label", "symbol", "name", "group", "subgroup"])

        with patch.object(dashboard_app, "load_watchlist", return_value=file_watchlist), \
            patch.object(dashboard_app, "load_gemini_agent_group_map", return_value=pd.DataFrame(columns=["symbol", "name", "group", "subgroup"])), \
            patch.object(dashboard_app, "load_llm_group_map", return_value=llm_watchlist), \
            patch.object(dashboard_app, "load_twse_industry_map", return_value=industry_df), \
            patch.object(dashboard_app, "prefetch_price_data", return_value={}):
            response = b"".join(dashboard_app.app({"QUERY_STRING": ""}, lambda *_args: None)).decode("utf-8")

        self.assertIn("<th>名稱</th><th>形勢判斷</th><th>收盤</th><th>目標價</th><th>目標價/現價</th><th>題材</th>", response)
        self.assertIn("<th>備註</th><th class='theme-summary-cell'>題材摘要</th><th class='source-cell'>來源</th>", response)
        self.assertIn("<td class='theme-summary-cell'>-</td><td class='source-cell'>-</td>", response)
