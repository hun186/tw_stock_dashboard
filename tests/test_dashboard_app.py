from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
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
        self.assertIn("CZJ-mob-101T-202605261747.json", response)
        self.assertIn("tw-dashboard-backup.json", response)
        self.assertIn("class='primary-actions' data-title='主要操作'", response)
        self.assertIn("class='utility-actions' data-title='設定與備份'", response)
        self.assertRegex(
            response,
            r"<legend>股池與分類</legend>[\s\S]*class='primary-actions' data-title='主要操作'[\s\S]*<legend>K 線與顯示</legend>[\s\S]*<legend>篩選與分頁</legend>[\s\S]*<legend>個人標籤篩選</legend>",
        )
        self.assertIn(".filter-grid{display:grid;grid-template-columns:repeat(3,minmax(220px,1fr))", response)
        self.assertIn("@media (max-width: 900px){.filter-grid{grid-template-columns:repeat(2,minmax(180px,1fr))}}", response)
        self.assertNotIn("@media (max-width: 1180px){.filter-grid{grid-template-columns:repeat(2", response)
        self.assertRegex(
            response,
            r"儲存目前設定[\s\S]*讀取本機設定[\s\S]*匯出完整備份檔[\s\S]*匯入備份檔[\s\S]*推薦設定檔[\s\S]*讀取推薦設定",
        )
        self.assertIn(".primary-actions{grid-template-columns:1fr}", response)
        self.assertIn("initServerConfigPicker();", response)
        self.assertIn(".watchlist-batch-item .batch-stock-check", response)
        self.assertIn('class="batch-stock-label"', response)
        self.assertIn("顯示價K線", response)
        self.assertIn("const autoRefreshMs = 60000;", response)
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

        self.assertIn("id='pipelineProgress'", response)
        self.assertIn("目前處理進度", response)
        self.assertIn("name='compact_progress'", response)
        self.assertIn("class='pipeline-progress is-compact'", response)
        self.assertIn("精簡進度", response)
        self.assertIn("行情資料", response)
        self.assertIn("技術分析", response)
        self.assertIn("不再用跳動提示假裝後端進度", response)
        self.assertIn("可用「精簡進度」開關縮成單列顯示", response)
        self.assertIn("showLoadingProgress('更新儀表板')", response)
        self.assertIn("if(typeof form.requestSubmit === 'function') form.requestSubmit();", response)
        self.assertIn("buildLoadingMessage(form, reason)", response)
        self.assertIn("const pipelineProgressSteps =", response)
        self.assertIn("等待後端回應：0%", response)
        self.assertIn("const dashboardRenderItems = Object.freeze", response)
        self.assertIn("applyStatusFilterInPlace", response)
        self.assertIn("未重新下載行情", response)
        self.assertIn("已恢復顯示全部形勢判斷", response)
        self.assertIn("仍使用目前載入的完整股池", response)
        self.assertIn("const AUTO_SUBMIT_FIELDS = new Set", response)
        self.assertIn("'compact_progress'", response)
        self.assertIn("'tab','industry','period','interval','limit','group_filter','subgroup_filter'", response)
        self.assertIn("document.getElementById('cfgForm')?.addEventListener('change'", response)
        self.assertIn("if(AUTO_SUBMIT_FIELDS.has(event.target?.name)) autoSubmitConfig(event)", response)
        self.assertIn('document.querySelector(\'[name="status_filter"]\')?.addEventListener(\'change\', applyStatusFilterInPlace)', response)
        self.assertNotIn("'limit','status_filter','group_filter'", response)

    def test_rendered_dashboard_script_is_valid_javascript(self) -> None:
        if not shutil.which("node"):
            self.skipTest("node is required to syntax-check rendered dashboard JavaScript")

        file_watchlist = pd.DataFrame([
            {"symbol": "2330.TW", "name": "台積電", "group": "AI晶片", "subgroup": "先進製程"},
        ])
        llm_watchlist = pd.DataFrame(columns=["symbol", "name", "group", "subgroup"])
        industry_df = pd.DataFrame(columns=["industry", "industry_label", "symbol", "name", "group", "subgroup"])

        with patch.object(dashboard_app, "load_watchlist", return_value=file_watchlist), \
            patch.object(dashboard_app, "load_llm_group_map", return_value=llm_watchlist), \
            patch.object(dashboard_app, "load_twse_industry_map", return_value=industry_df), \
            patch.object(dashboard_app, "prefetch_price_data", return_value={}):
            response = b"".join(dashboard_app.app({"QUERY_STRING": ""}, lambda *_args: None)).decode("utf-8")

        scripts = re.findall(r"<script>(.*?)</script>", response, flags=re.S)
        self.assertTrue(scripts)
        self.assertIn("function escapeHtmlAttr", response)
        self.assertIn("${escapeHtmlAttr(item.symbol)}", response)
        self.assertIn("fieldName === 'show_price'", response)
        with tempfile.NamedTemporaryFile("w", suffix=".js", encoding="utf-8") as script_file:
            script_file.write("\n".join(scripts))
            script_file.flush()
            result = subprocess.run(["node", "--check", script_file.name], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

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
        self.assertIn("<th>風險與觀察</th><th>備註</th></tr>", response)
        self.assertIn("class='row-action-cell'><button type='button' class='watchlist-action is-icon is-remove'", response)
        self.assertIn(">−</button>", response)
        self.assertNotIn("<th>互動</th>", response)
        self.assertIn("name='stock_meta_note' value='法說'", response)
        self.assertIn("stockMetaNoteFilter?.addEventListener('input', applyStockMetaFilters)", response)
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
