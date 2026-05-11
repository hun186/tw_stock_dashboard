from __future__ import annotations

import json
import unittest
from urllib.parse import urlencode
from unittest.mock import patch

import pandas as pd

from api import dashboard_app


class DashboardPersonalFilterTests(unittest.TestCase):
    def test_personal_note_filter_narrows_stocks_and_keeps_note_header(self) -> None:
        file_watchlist = pd.DataFrame([
            {"symbol": "2330.TW", "name": "台積電", "group": "AI晶片", "subgroup": "先進製程"},
            {"symbol": "4977.TW", "name": "眾達-KY", "group": "AI光通訊", "subgroup": "光通訊模組"},
        ])
        llm_watchlist = pd.DataFrame(columns=["symbol", "name", "group", "subgroup"])
        industry_df = pd.DataFrame(columns=["industry", "industry_label", "symbol", "name", "group", "subgroup"])
        captured_symbols = []
        payload = {
            "2330.TW": {"note": "法說後續追蹤"},
            "4977.TW": {"note": "短線觀察"},
        }

        def fake_prefetch(stocks, *_args, **_kwargs):
            captured_symbols.append(stocks["symbol"].tolist())
            return {}

        query = urlencode({
            "stock_meta_note": "法說",
            "stock_meta_payload": json.dumps(payload, ensure_ascii=False),
        })
        with patch.object(dashboard_app, "load_watchlist", return_value=file_watchlist), \
            patch.object(dashboard_app, "load_llm_group_map", return_value=llm_watchlist), \
            patch.object(dashboard_app, "load_twse_industry_map", return_value=industry_df), \
            patch.object(dashboard_app, "prefetch_price_data", side_effect=fake_prefetch):
            response = b"".join(dashboard_app.app({"QUERY_STRING": query}, lambda *_args: None)).decode("utf-8")

        self.assertIn("<tr><th>移除</th><th>狀態</th>", response)
        self.assertIn("<th>名稱</th><th>形勢判斷</th><th>收盤</th><th>目標價</th><th>目標價/現價</th><th>題材</th>", response)
        self.assertIn("<th>風險與觀察</th><th>備註</th><th class='theme-summary-cell'>題材摘要</th><th class='source-cell'>來源</th></tr>", response)
        self.assertIn("class='row-action-cell'><button type='button' class='watchlist-action is-icon is-remove'", response)
        self.assertIn(">−</button>", response)
        self.assertNotIn("<th>互動</th>", response)
        self.assertIn("name='stock_meta_note' value='法說'", response)
        self.assertIn("document.getElementById('stockMetaFilter-note')", response)
        self.assertIn("filter.addEventListener('input', applyStockMetaFilters)", response)
        self.assertIn("function currentStockMetaFilterAvailability()", response)
        self.assertIn("refreshStockMetaFilterOptions();\n  applyStockMetaFilters();", response)
        self.assertIn("符合股數</span><span class='summary-value'>1 檔", response)
        self.assertEqual(captured_symbols, [["2330.TW"]])

    def test_personal_stock_filter_matches_symbol_name_and_pasted_list(self) -> None:
        file_watchlist = pd.DataFrame([
            {"symbol": "2330.TW", "name": "台積電", "group": "AI晶片", "subgroup": "先進製程"},
            {"symbol": "2382.TW", "name": "廣達", "group": "AI伺服器", "subgroup": "系統組裝"},
            {"symbol": "4977.TW", "name": "眾達-KY", "group": "AI光通訊", "subgroup": "光通訊模組"},
        ])
        llm_watchlist = pd.DataFrame(columns=["symbol", "name", "group", "subgroup"])
        industry_df = pd.DataFrame(columns=["industry", "industry_label", "symbol", "name", "group", "subgroup"])
        captured_symbols = []

        def fake_prefetch(stocks, *_args, **_kwargs):
            captured_symbols.append(stocks["symbol"].tolist())
            return {}

        query = urlencode({"stock_meta_stock": "2330, 廣達"})
        with patch.object(dashboard_app, "load_watchlist", return_value=file_watchlist), \
            patch.object(dashboard_app, "load_llm_group_map", return_value=llm_watchlist), \
            patch.object(dashboard_app, "load_twse_industry_map", return_value=industry_df), \
            patch.object(dashboard_app, "prefetch_price_data", side_effect=fake_prefetch):
            response = b"".join(dashboard_app.app({"QUERY_STRING": query}, lambda *_args: None)).decode("utf-8")

        self.assertIn("id='stockMetaFilter-stock' name='stock_meta_stock' value='2330, 廣達'", response)
        self.assertIn("已選 2 筆條件", response)
        self.assertIn("seedStockFilterSelectionsFromInput", response)
        self.assertIn("data-name='台積電'", response)
        self.assertIn("filters.stockTokens", response)
        self.assertIn("符合股數</span><span class='summary-value'>2 檔", response)
        self.assertEqual(captured_symbols, [["2330.TW", "2382.TW"]])

    def test_theme_and_subtheme_filters_still_narrow_compact_theme_table(self) -> None:
        file_watchlist = pd.DataFrame([
            {"symbol": "2330.TW", "name": "台積電", "group": "AI晶片", "subgroup": "先進製程"},
            {"symbol": "2382.TW", "name": "廣達", "group": "AI伺服器", "subgroup": "系統組裝"},
            {"symbol": "4977.TW", "name": "眾達-KY", "group": "AI光通訊", "subgroup": "光通訊模組"},
        ])
        llm_watchlist = pd.DataFrame(columns=["symbol", "name", "group", "subgroup"])
        industry_df = pd.DataFrame(columns=["industry", "industry_label", "symbol", "name", "group", "subgroup"])
        captured_symbols = []

        def fake_prefetch(stocks, *_args, **_kwargs):
            captured_symbols.append(stocks["symbol"].tolist())
            return {}

        query = urlencode({"group_filter": "AI伺服器", "subgroup_filter": "系統組裝"})
        with patch.object(dashboard_app, "load_watchlist", return_value=file_watchlist), \
            patch.object(dashboard_app, "load_llm_group_map", return_value=llm_watchlist), \
            patch.object(dashboard_app, "load_twse_industry_map", return_value=industry_df), \
            patch.object(dashboard_app, "prefetch_price_data", side_effect=fake_prefetch):
            response = b"".join(dashboard_app.app({"QUERY_STRING": query}, lambda *_args: None)).decode("utf-8")

        self.assertIn("<option value='AI伺服器' selected>AI伺服器</option>", response)
        self.assertIn("<option value='系統組裝' selected>系統組裝</option>", response)
        self.assertIn("<th>名稱</th><th>形勢判斷</th><th>收盤</th><th>目標價</th><th>目標價/現價</th><th>題材</th>", response)
        self.assertIn("<td class='theme-cell'><div class='theme-compact' title='主題分類：AI伺服器；次題材：系統組裝'>", response)
        self.assertIn("<span class='theme-chip theme-chip-main'>AI伺服器</span>", response)
        self.assertIn("<span class='theme-chip theme-chip-sub'>系統組裝</span>", response)
        self.assertIn("符合股數</span><span class='summary-value'>1 檔", response)
        self.assertEqual(captured_symbols, [["2382.TW"]])
        self.assertNotIn("data-symbol='2330.TW'", response)
        self.assertNotIn("data-symbol='4977.TW'", response)

    def test_status_and_personal_filter_options_only_include_available_values(self) -> None:
        file_watchlist = pd.DataFrame([
            {"symbol": "2330.TW", "name": "台積電", "group": "AI晶片", "subgroup": "先進製程"},
            {"symbol": "4977.TW", "name": "眾達-KY", "group": "AI光通訊", "subgroup": "光通訊模組"},
        ])
        llm_watchlist = pd.DataFrame(columns=["symbol", "name", "group", "subgroup"])
        industry_df = pd.DataFrame(columns=["industry", "industry_label", "symbol", "name", "group", "subgroup"])
        payload = {"2330.TW": {"action": "波段"}}

        def fake_analysis(symbol, *_args, **_kwargs):
            bucket = "bull" if symbol == "2330.TW" else "watch"
            return {
                "df": pd.DataFrame(),
                "signal": {"bucket": bucket, "message": bucket, "score": 0},
                "bucket": bucket,
                "status": bucket,
                "close_text": "-",
                "sort_metrics": {
                    "symbol": symbol,
                    "close": -1.0,
                    "volume": -1.0,
                    "change_pct": -999.0,
                    "target_ratio": -1.0,
                    "signal_score": 0.0,
                },
                "target_price_text": "-",
                "target_ratio_text": "-",
            }

        query = urlencode({"stock_meta_payload": json.dumps(payload, ensure_ascii=False)})
        with patch.object(dashboard_app, "load_watchlist", return_value=file_watchlist), \
            patch.object(dashboard_app, "load_llm_group_map", return_value=llm_watchlist), \
            patch.object(dashboard_app, "load_twse_industry_map", return_value=industry_df), \
            patch.object(dashboard_app, "prefetch_price_data", return_value={}), \
            patch.object(dashboard_app, "_build_stock_analysis", side_effect=fake_analysis):
            response = b"".join(dashboard_app.app({"QUERY_STRING": query}, lambda *_args: None)).decode("utf-8")

        self.assertIn("<option value='watch' >⚪ 資料不足</option>", response)
        self.assertIn("<option value='bull' >🔴 偏多</option>", response)
        self.assertNotIn("<option value='bear' ", response)
        self.assertIn('const stockMetaFilterOptions = {"action": ["波段"]', response)
        self.assertIn('const stockMetaFilterHasEmpty = {"action": true', response)
