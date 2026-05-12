from __future__ import annotations

import json
import unittest
from urllib.parse import urlencode
from unittest.mock import patch

import pandas as pd

from api import dashboard_app


class DashboardCategoryPoolTests(unittest.TestCase):
    def test_category_tab_all_industries_remains_available(self) -> None:
        file_watchlist = pd.DataFrame(columns=["symbol", "name", "group", "subgroup"])
        llm_watchlist = pd.DataFrame(columns=["symbol", "name", "group", "subgroup"])
        industry_df = pd.DataFrame([
            {"industry": "24", "industry_label": "24 - 半導體業", "symbol": "2330.TW", "name": "台積電", "group": "TWSE-24", "subgroup": ""},
            {"industry": "25", "industry_label": "25 - 電腦及週邊", "symbol": "2382.TW", "name": "廣達", "group": "TWSE-25", "subgroup": ""},
        ])
        captured_counts = []

        def fake_prefetch(stocks, *_args, **_kwargs):
            captured_counts.append(len(stocks))
            return {}

        with patch.object(dashboard_app, "load_watchlist", return_value=file_watchlist), \
            patch.object(dashboard_app, "load_gemini_agent_group_map", return_value=pd.DataFrame(columns=["symbol", "name", "group", "subgroup"])), \
            patch.object(dashboard_app, "load_llm_group_map", return_value=llm_watchlist), \
            patch.object(dashboard_app, "load_twse_industry_map", return_value=industry_df), \
            patch.object(dashboard_app, "prefetch_price_data", side_effect=fake_prefetch):
            response = b"".join(dashboard_app.app({"QUERY_STRING": "tab=category&industry=all"}, lambda *_args: None)).decode("utf-8")

        self.assertIn("<option value='all' selected>不限產業</option>", response)
        self.assertIn("<option value='24' >24 - 半導體業</option>", response)
        self.assertIn("符合股數</span><span class='summary-value'>2 檔", response)
        self.assertEqual(captured_counts, [2])

    def test_category_tab_all_industries_includes_llm_classification_pool(self) -> None:
        file_watchlist = pd.DataFrame(columns=["symbol", "name", "group", "subgroup"])
        llm_watchlist = pd.DataFrame([
            {"symbol": "2330.TW", "name": "台積電", "group": "AI晶片", "subgroup": "先進製程"},
            {"symbol": "4977.TWO", "name": "眾達-KY", "group": "AI光通訊", "subgroup": "光通訊模組"},
        ])
        industry_df = pd.DataFrame([
            {"industry": "24", "industry_label": "24 - 半導體業", "symbol": "2330.TW", "name": "台積電", "group": "TWSE-24", "subgroup": ""},
        ])
        captured_symbols = []

        def fake_prefetch(stocks, *_args, **_kwargs):
            captured_symbols.append(stocks["symbol"].tolist())
            return {}

        with patch.object(dashboard_app, "load_watchlist", return_value=file_watchlist), \
            patch.object(dashboard_app, "load_gemini_agent_group_map", return_value=pd.DataFrame(columns=["symbol", "name", "group", "subgroup"])), \
            patch.object(dashboard_app, "load_llm_group_map", return_value=llm_watchlist), \
            patch.object(dashboard_app, "load_twse_industry_map", return_value=industry_df), \
            patch.object(dashboard_app, "prefetch_price_data", side_effect=fake_prefetch):
            response = b"".join(dashboard_app.app({"QUERY_STRING": "tab=category&industry=all"}, lambda *_args: None)).decode("utf-8")

        self.assertIn("符合股數</span><span class='summary-value'>2 檔", response)
        self.assertIn("<option value='AI光通訊' >AI光通訊</option>", response)
        self.assertEqual(captured_symbols, [["2330.TW", "4977.TWO"]])

    def test_category_tab_merges_same_stock_with_wrong_tw_suffix_metadata(self) -> None:
        file_watchlist = pd.DataFrame([
            {"symbol": "8069.TWO", "name": "元太", "group": "電子消費", "subgroup": "電子紙面板"},
        ])
        gemini_watchlist = pd.DataFrame([
            {
                "symbol": "8069.TW",
                "name": "元太",
                "group": "電子科技與半導體",
                "subgroup": "電子紙 (ePaper)",
                "summary": "電子紙龍頭",
                "reference_url": "https://www.eink.com/investor-relations",
            },
        ])
        industry_df = pd.DataFrame([
            {
                "industry": "26",
                "industry_label": "26 - 光電業",
                "symbol": "8069.TWO",
                "name": "元太",
                "group": "上櫃-26",
                "subgroup": "",
            },
        ])
        captured_symbols = []

        def fake_prefetch(stocks, *_args, **_kwargs):
            captured_symbols.append(stocks["symbol"].tolist())
            return {}

        with patch.object(dashboard_app, "load_watchlist", return_value=file_watchlist), \
            patch.object(dashboard_app, "load_gemini_agent_group_map", return_value=gemini_watchlist), \
            patch.object(dashboard_app, "load_llm_group_map", return_value=pd.DataFrame(columns=["symbol", "name", "group", "subgroup"])), \
            patch.object(dashboard_app, "load_twse_industry_map", return_value=industry_df), \
            patch.object(dashboard_app, "prefetch_price_data", side_effect=fake_prefetch):
            response = b"".join(dashboard_app.app({"QUERY_STRING": "tab=category&industry=all"}, lambda *_args: None)).decode("utf-8")

        self.assertIn("符合股數</span><span class='summary-value'>1 檔", response)
        self.assertIn("<td class='symbol-cell'><button type='button' class='research-symbol-button is-compact' data-research-symbol='8069.TWO'", response)
        self.assertNotIn("data-research-symbol='8069.TW'", response)
        self.assertIn("電子紙龍頭", response)
        self.assertEqual(captured_symbols, [["8069.TWO"]])

    def test_category_tab_discards_suffix_only_symbols(self) -> None:
        file_watchlist = pd.DataFrame(columns=["symbol", "name", "group", "subgroup"])
        llm_watchlist = pd.DataFrame([
            {"symbol": ".TWO", "name": "元太", "group": "電子消費", "subgroup": "電子紙面板"},
        ])
        industry_df = pd.DataFrame([
            {"industry": "26", "industry_label": "26 - 光電業", "symbol": "8069.TWO", "name": "元太", "group": "上櫃-26", "subgroup": ""},
        ])
        captured_symbols = []

        def fake_prefetch(stocks, *_args, **_kwargs):
            captured_symbols.append(stocks["symbol"].tolist())
            return {}

        with patch.object(dashboard_app, "load_watchlist", return_value=file_watchlist), \
            patch.object(dashboard_app, "load_gemini_agent_group_map", return_value=pd.DataFrame(columns=["symbol", "name", "group", "subgroup"])), \
            patch.object(dashboard_app, "load_llm_group_map", return_value=llm_watchlist), \
            patch.object(dashboard_app, "load_twse_industry_map", return_value=industry_df), \
            patch.object(dashboard_app, "prefetch_price_data", side_effect=fake_prefetch):
            response = b"".join(dashboard_app.app({"QUERY_STRING": "tab=category&industry=all"}, lambda *_args: None)).decode("utf-8")

        self.assertIn("符合股數</span><span class='summary-value'>1 檔", response)
        self.assertNotIn("<td class='symbol-cell'>.TWO</td>", response)
        self.assertEqual(captured_symbols, [["8069.TWO"]])

    def test_category_tab_all_industries_explains_non_official_symbols(self) -> None:
        file_watchlist = pd.DataFrame(columns=["symbol", "name", "group", "subgroup"])
        llm_watchlist = pd.DataFrame([
            {"symbol": "2330.TW", "name": "台積電", "group": "AI晶片", "subgroup": "先進製程"},
            {"symbol": "9999.TW", "name": "測試股", "group": "測試題材", "subgroup": "非官方產業表"},
        ])
        industry_df = pd.DataFrame([
            {"industry": "24", "industry_label": "24 - 半導體業", "symbol": "2330.TW", "name": "台積電", "group": "TWSE-24", "subgroup": ""},
        ])

        with patch.object(dashboard_app, "load_watchlist", return_value=file_watchlist), \
            patch.object(dashboard_app, "load_gemini_agent_group_map", return_value=pd.DataFrame(columns=["symbol", "name", "group", "subgroup"])), \
            patch.object(dashboard_app, "load_llm_group_map", return_value=llm_watchlist), \
            patch.object(dashboard_app, "load_twse_industry_map", return_value=industry_df), \
            patch.object(dashboard_app, "prefetch_price_data", return_value={}):
            response = b"".join(dashboard_app.app({"QUERY_STRING": "tab=category&industry=all"}, lambda *_args: None)).decode("utf-8")

        self.assertIn("其中 1 檔目前不在本次載入的交易所／櫃買官方產業表", response)
        self.assertIn("這不等於停業", response)

    def test_category_tab_all_industries_explains_missing_official_table(self) -> None:
        file_watchlist = pd.DataFrame(columns=["symbol", "name", "group", "subgroup"])
        llm_watchlist = pd.DataFrame([
            {"symbol": "2330.TW", "name": "台積電", "group": "AI晶片", "subgroup": "先進製程"},
        ])
        industry_df = pd.DataFrame(columns=["industry", "industry_label", "symbol", "name", "group", "subgroup"])

        with patch.object(dashboard_app, "load_watchlist", return_value=file_watchlist), \
            patch.object(dashboard_app, "load_gemini_agent_group_map", return_value=pd.DataFrame(columns=["symbol", "name", "group", "subgroup"])), \
            patch.object(dashboard_app, "load_llm_group_map", return_value=llm_watchlist), \
            patch.object(dashboard_app, "load_twse_industry_map", return_value=industry_df), \
            patch.object(dashboard_app, "prefetch_price_data", return_value={}):
            response = b"".join(dashboard_app.app({"QUERY_STRING": "tab=category&industry=all"}, lambda *_args: None)).decode("utf-8")

        self.assertIn("本次未載入交易所／櫃買官方產業表", response)
        self.assertIn("這不等於標的停業", response)

    def test_category_tab_all_industries_can_be_narrowed_by_personal_filter(self) -> None:
        file_watchlist = pd.DataFrame(columns=["symbol", "name", "group", "subgroup"])
        llm_watchlist = pd.DataFrame(columns=["symbol", "name", "group", "subgroup"])
        industry_df = pd.DataFrame([
            {"industry": "24", "industry_label": "24 - 半導體業", "symbol": "2330.TW", "name": "台積電", "group": "TWSE-24", "subgroup": ""},
            {"industry": "25", "industry_label": "25 - 電腦及週邊", "symbol": "2382.TW", "name": "廣達", "group": "TWSE-25", "subgroup": ""},
        ])
        captured_symbols = []
        payload = {"2330.TW": {"action": "波段"}}

        def fake_prefetch(stocks, *_args, **_kwargs):
            captured_symbols.append(stocks["symbol"].tolist())
            return {}

        query = urlencode({
            "tab": "category",
            "industry": "all",
            "stock_meta_action": "波段",
            "stock_meta_payload": json.dumps(payload, ensure_ascii=False),
        })
        with patch.object(dashboard_app, "load_watchlist", return_value=file_watchlist), \
            patch.object(dashboard_app, "load_gemini_agent_group_map", return_value=pd.DataFrame(columns=["symbol", "name", "group", "subgroup"])), \
            patch.object(dashboard_app, "load_llm_group_map", return_value=llm_watchlist), \
            patch.object(dashboard_app, "load_twse_industry_map", return_value=industry_df), \
            patch.object(dashboard_app, "prefetch_price_data", side_effect=fake_prefetch):
            response = b"".join(dashboard_app.app({"QUERY_STRING": query}, lambda *_args: None)).decode("utf-8")

        self.assertIn("<option value='all' selected>不限產業</option>", response)
        self.assertIn("符合股數</span><span class='summary-value'>1 檔", response)
        self.assertEqual(captured_symbols, [["2330.TW"]])
