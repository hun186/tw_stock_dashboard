from __future__ import annotations

import json
import os
import unittest
from urllib.parse import urlencode
from unittest.mock import patch

import pandas as pd

from api import dashboard_app
from api.dashboard_app import DEFAULT_LIVE_FETCH_THRESHOLD, _resolve_live_fetch_controls


class DashboardLiveFetchControlsTests(unittest.TestCase):
    def test_single_industry_category_allows_live_fetch_above_default_threshold(self) -> None:
        allow_live_fetch, max_live_symbols = _resolve_live_fetch_controls(
            is_serverless_runtime=True,
            stock_count=94,
            is_custom_watchlist=False,
            tab="category",
            industry="24",
        )

        self.assertTrue(allow_live_fetch)
        self.assertGreaterEqual(max_live_symbols, 114)

    def test_broad_serverless_category_stays_on_default_live_limit(self) -> None:
        allow_live_fetch, max_live_symbols = _resolve_live_fetch_controls(
            is_serverless_runtime=True,
            stock_count=94,
            is_custom_watchlist=False,
            tab="category",
            industry="all",
        )

        self.assertFalse(allow_live_fetch)
        self.assertEqual(max_live_symbols, DEFAULT_LIVE_FETCH_THRESHOLD)

    def test_custom_watchlist_allows_all_symbols(self) -> None:
        allow_live_fetch, max_live_symbols = _resolve_live_fetch_controls(
            is_serverless_runtime=True,
            stock_count=94,
            is_custom_watchlist=True,
            tab="watchlist",
            industry="all",
        )

        self.assertTrue(allow_live_fetch)
        self.assertEqual(max_live_symbols, 94)


class DashboardInitialWatchlistTests(unittest.TestCase):
    def test_default_watchlist_uses_file_watchlist_not_entire_llm_metadata(self) -> None:
        file_watchlist = pd.DataFrame([
            {"symbol": "2330.TW", "name": "台積電", "group": "AI晶片", "subgroup": "先進製程"},
            {"symbol": "4977.TW", "name": "眾達-KY", "group": "AI光通訊", "subgroup": "光通訊模組"},
        ])
        llm_watchlist = pd.DataFrame([
            {"symbol": f"{1000 + idx}.TW", "name": f"LLM{idx}", "group": "全市場", "subgroup": ""}
            for idx in range(300)
        ])
        industry_df = pd.DataFrame(columns=["industry", "industry_label", "symbol", "name", "group", "subgroup"])
        captured_counts = []

        def fake_prefetch(stocks, *_args, **_kwargs):
            captured_counts.append(len(stocks))
            return {}

        status_headers = []

        def start_response(status, headers):
            status_headers.append((status, headers))

        with patch.dict(os.environ, {"VERCEL": "1"}, clear=False), \
            patch.object(dashboard_app, "load_watchlist", return_value=file_watchlist), \
            patch.object(dashboard_app, "load_llm_group_map", return_value=llm_watchlist), \
            patch.object(dashboard_app, "load_twse_industry_map", return_value=industry_df), \
            patch.object(dashboard_app, "prefetch_price_data", side_effect=fake_prefetch):
            response = b"".join(dashboard_app.app({"QUERY_STRING": ""}, start_response)).decode("utf-8")

        self.assertEqual(status_headers[0][0], "200 OK")
        self.assertNotIn("目前候選股共有 300 檔", response)
        self.assertIn("符合股數</span><span class='summary-value'>2 檔", response)
        self.assertIn("restoreBrowserWatchlistIfAvailable({submit: true})", response)
        self.assertIn(".watchlist-batch-item .batch-stock-check", response)
        self.assertIn('class="batch-stock-label"', response)
        self.assertEqual(captured_counts, [2])

    def test_dashboard_renders_loading_progress_for_slow_category_requests(self) -> None:
        file_watchlist = pd.DataFrame(columns=["symbol", "name", "group", "subgroup"])
        llm_watchlist = pd.DataFrame(columns=["symbol", "name", "group", "subgroup"])
        industry_df = pd.DataFrame([
            {"industry": "24", "industry_label": "24 - 半導體業", "symbol": "2330.TW", "name": "台積電", "group": "TWSE-24", "subgroup": ""},
        ])

        with patch.object(dashboard_app, "load_watchlist", return_value=file_watchlist), \
            patch.object(dashboard_app, "load_llm_group_map", return_value=llm_watchlist), \
            patch.object(dashboard_app, "load_twse_industry_map", return_value=industry_df), \
            patch.object(dashboard_app, "prefetch_price_data", return_value={}):
            response = b"".join(dashboard_app.app({"QUERY_STRING": "tab=category&industry=24"}, lambda *_args: None)).decode("utf-8")

        self.assertIn("id='loadingOverlay'", response)
        self.assertIn("讀取快取；必要時下載行情資料", response)
        self.assertIn("分類股池檔數較多時可能需要約 1 分鐘", response)
        self.assertIn("showLoadingProgress('更新儀表板')", response)
        self.assertIn("buildLoadingMessage(form, reason)", response)
        self.assertIn("const dashboardRenderItems = Object.freeze", response)
        self.assertIn("applyStatusFilterInPlace", response)
        self.assertIn("未重新下載行情", response)
        self.assertIn("已恢復顯示全部形勢判斷", response)
        self.assertIn("仍使用目前載入的完整股池", response)
        self.assertIn('document.querySelector(\'[name="status_filter"]\')?.addEventListener(\'change\', applyStatusFilterInPlace)', response)
        self.assertNotIn("'limit','status_filter','group_filter'", response)

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
            patch.object(dashboard_app, "load_llm_group_map", return_value=llm_watchlist), \
            patch.object(dashboard_app, "load_twse_industry_map", return_value=industry_df), \
            patch.object(dashboard_app, "prefetch_price_data", side_effect=fake_prefetch):
            response = b"".join(dashboard_app.app({"QUERY_STRING": "tab=category&industry=all"}, lambda *_args: None)).decode("utf-8")

        self.assertIn("<option value='all' selected>不限產業</option>", response)
        self.assertIn("<option value='24' >24 - 半導體業</option>", response)
        self.assertIn("符合股數</span><span class='summary-value'>2 檔", response)
        self.assertEqual(captured_counts, [2])

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
            patch.object(dashboard_app, "load_llm_group_map", return_value=llm_watchlist), \
            patch.object(dashboard_app, "load_twse_industry_map", return_value=industry_df), \
            patch.object(dashboard_app, "prefetch_price_data", side_effect=fake_prefetch):
            response = b"".join(dashboard_app.app({"QUERY_STRING": query}, lambda *_args: None)).decode("utf-8")

        self.assertIn("<option value='all' selected>不限產業</option>", response)
        self.assertIn("符合股數</span><span class='summary-value'>1 檔", response)
        self.assertEqual(captured_symbols, [["2330.TW"]])

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


if __name__ == "__main__":
    unittest.main()
