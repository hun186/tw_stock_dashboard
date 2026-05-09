from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd

from api import dashboard_app


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
        self.assertIn(".filter-grid{display:grid;grid-template-columns:repeat(9,minmax(0,1fr))", response)
        self.assertIn(".filter-grid > .pool-settings{grid-column:span 3}", response)
        self.assertIn(".filter-grid > .primary-actions{grid-column:span 2}", response)
        self.assertIn(".filter-grid > .kline-settings{grid-column:span 4}", response)
        self.assertIn("@media (max-width: 920px){.filter-grid{grid-template-columns:repeat(2", response)
        self.assertRegex(
            response,
            r"儲存目前設定[\s\S]*讀取本機設定[\s\S]*匯出完整備份檔[\s\S]*匯入備份檔[\s\S]*推薦設定檔[\s\S]*讀取推薦設定",
        )
        self.assertIn(".primary-actions{grid-template-columns:1fr}", response)
        self.assertIn("initServerConfigPicker();", response)
        self.assertIn(".watchlist-batch-item .batch-stock-check", response)
        self.assertIn('class="batch-stock-label"', response)
        self.assertIn("顯示價K線", response)
        self.assertIn("總表摘要／來源", response)
        self.assertIn(".note-cell{width:calc(190px + 3em);min-width:calc(190px + 3em);max-width:calc(190px + 3em)}", response)
        self.assertIn(".note-editor .stock-note-input{width:calc(170px + 3em);min-width:calc(120px + 3em);padding:4px 6px;min-height:30px}", response)
        self.assertIn("table th:nth-child(14), table td:nth-child(14){width:calc(190px + 3em);min-width:calc(190px + 3em);max-width:calc(190px + 3em)}", response)
        self.assertIn(".name-cell,.table-wrap th:nth-child(4),.table-wrap td:nth-child(4){width:calc(5em + 18px);min-width:calc(5em + 18px);max-width:calc(5em + 18px);white-space:normal;line-height:1.35}", response)
        self.assertIn(".name-cell .stock-jump{display:inline-block;max-width:5em;overflow:visible;text-overflow:clip;white-space:normal;overflow-wrap:anywhere;word-break:break-word;line-height:1.35;text-align:left}", response)
        self.assertIn(".table-wrap th:nth-child(5),.table-wrap td:nth-child(5){left:calc(202px + 5em)}", response)
        self.assertIn(".table-wrap th:nth-child(-n+5),.table-wrap td:nth-child(-n+5){position:sticky", response)
        self.assertIn(".theme-chip-main{color:#1e3a8a;background:#dbeafe}", response)
        self.assertIn("K線摘要／來源", response)
        self.assertIn("name='table_theme_meta'", response)
        self.assertIn("name='card_theme_meta'", response)
        self.assertIn("setTableThemeMetaVisibility(event.target.value)", response)
        self.assertIn("setCardThemeMetaVisibility(event.target.value)", response)
        self.assertIn("let dashboardShowTableThemeMeta = false;", response)
        self.assertIn("let dashboardShowCardThemeMeta = false;", response)
        self.assertIn("股名／代號篩選", response)
        self.assertIn("openStockFilterDialog()", response)
        self.assertIn("可勾選的來源僅限目前自選股清單", response)
        self.assertIn("renderStockPickerResults", response)
        self.assertIn("syncVisibleStockPickerSelections", response)
        self.assertIn("id='stockMetaFilter-stock' name='stock_meta_stock'", response)
        self.assertNotIn("stockFilterSummary", response)
        self.assertNotIn("stock-filter-summary", response)
        self.assertIn("const stockFilterStocks = [{\"symbol\": \"2330.TW\"", response)
        self.assertIn("const autoRefreshMs = 60000;", response)
        self.assertIn("intradayRefreshUrl", response)
        self.assertIn("_intraday_refresh", response)
        self.assertIn("refreshIntradayAfterResume", response)
        self.assertIn("visibilitychange", response)
        self.assertIn("window.addEventListener('focus'", response)
        self.assertEqual(captured_counts, [2])

    def test_stock_picker_menus_are_sorted_by_symbol_code(self) -> None:
        file_watchlist = pd.DataFrame([
            {"symbol": "2330.TW", "name": "台積電", "group": "AI晶片", "subgroup": "先進製程"},
            {"symbol": "0050.TW", "name": "元大台灣50", "group": "ETF", "subgroup": "台股ETF"},
            {"symbol": "1101.TW", "name": "台泥", "group": "水泥", "subgroup": "水泥工業"},
        ])
        gemini_watchlist = pd.DataFrame(columns=["symbol", "name", "group", "subgroup"])
        llm_watchlist = pd.DataFrame([
            {"symbol": "4977.TW", "name": "眾達-KY", "group": "AI光通訊", "subgroup": "光通訊模組"},
        ])
        industry_df = pd.DataFrame([
            {"industry": "24", "industry_label": "24 - 半導體業", "symbol": "2382.TW", "name": "廣達", "group": "TWSE-24", "subgroup": ""},
        ])

        with patch.object(dashboard_app, "load_watchlist", return_value=file_watchlist), \
            patch.object(dashboard_app, "load_gemini_agent_group_map", return_value=gemini_watchlist), \
            patch.object(dashboard_app, "load_llm_group_map", return_value=llm_watchlist), \
            patch.object(dashboard_app, "load_twse_industry_map", return_value=industry_df), \
            patch.object(dashboard_app, "prefetch_price_data", return_value={}):
            response = b"".join(dashboard_app.app({"QUERY_STRING": ""}, lambda *_args: None)).decode("utf-8")

        all_stocks_json = re.search(r"const allStocks = (.*?);", response).group(1)
        stock_filter_json = re.search(r"const stockFilterStocks = (.*?);", response).group(1)
        all_stock_symbols = [stock["symbol"] for stock in json.loads(all_stocks_json)]
        stock_filter_symbols = [stock["symbol"] for stock in json.loads(stock_filter_json)]

        self.assertEqual(all_stock_symbols, ["0050.TW", "1101.TW", "2330.TW", "2382.TW", "4977.TW"])
        self.assertEqual(stock_filter_symbols, ["0050.TW", "1101.TW", "2330.TW"])

    def test_gemini_agent_metadata_priority_sits_between_watchlist_and_llm(self) -> None:
        file_watchlist = pd.DataFrame([
            {"symbol": "2330.TW", "name": "台積電", "group": "手動題材", "subgroup": "手動次題材"},
        ])
        gemini_watchlist = pd.DataFrame([
            {"symbol": "2330.TW", "name": "台積電", "group": "Gemini題材", "subgroup": "Gemini次題材"},
            {"symbol": "4772.TWO", "name": "台特化", "group": "半導體材料", "subgroup": "電子特氣 / 矽烷前驅物"},
        ])
        llm_watchlist = pd.DataFrame([
            {"symbol": "2330.TW", "name": "台積電", "group": "LLM題材", "subgroup": "LLM次題材"},
            {"symbol": "4772.TWO", "name": "台特化", "group": "傳產", "subgroup": "化學工業"},
        ])
        industry_df = pd.DataFrame([
            {"industry": "21", "industry_label": "21 - 化學工業", "symbol": "4772.TWO", "name": "台特化", "group": "上櫃-21", "subgroup": ""},
        ])

        query = "custom_watchlist=2330.TW,4772.TWO"
        with patch.object(dashboard_app, "load_watchlist", return_value=file_watchlist), \
            patch.object(dashboard_app, "load_gemini_agent_group_map", return_value=gemini_watchlist), \
            patch.object(dashboard_app, "load_llm_group_map", return_value=llm_watchlist), \
            patch.object(dashboard_app, "load_twse_industry_map", return_value=industry_df), \
            patch.object(dashboard_app, "prefetch_price_data", return_value={}):
            response = b"".join(dashboard_app.app({"QUERY_STRING": query}, lambda *_args: None)).decode("utf-8")

        self.assertIn("手動題材", response)
        self.assertIn("手動次題材", response)
        self.assertIn("半導體材料", response)
        self.assertIn("電子特氣 / 矽烷前驅物", response)
        self.assertNotIn("Gemini題材", response)
        self.assertNotIn("LLM題材", response)
        self.assertNotIn(">傳產</td>", response)

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
