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

from api import dashboard_app, data_loader
from api.dashboard_app import DEFAULT_LIVE_FETCH_THRESHOLD, _resolve_live_fetch_controls


class DataLoaderThemeMetadataTests(unittest.TestCase):
    def test_normalize_group_map_preserves_summary_and_reference_aliases(self) -> None:
        df = pd.DataFrame([
            {
                "股票代號": "2330.TW",
                "股票名稱": "台積電",
                "題材": "AI晶片",
                "次題材": "先進製程",
                "題材摘要": "先進封裝與 AI 加速器需求受惠",
                "資料來源": "https://example.com/tsmc",
            }
        ])

        normalized = data_loader._normalize_group_map(df)

        self.assertEqual(normalized.loc[0, "summary"], "先進封裝與 AI 加速器需求受惠")
        self.assertEqual(normalized.loc[0, "reference_url"], "https://example.com/tsmc")

    def test_normalize_group_map_backfills_missing_summary_columns(self) -> None:
        df = pd.DataFrame([
            {"symbol": "2317.TW", "name": "鴻海", "group": "AI伺服器", "subgroup": "組裝"}
        ])

        normalized = data_loader._normalize_group_map(df)

        self.assertIn("summary", normalized.columns)
        self.assertIn("reference_url", normalized.columns)
        self.assertEqual(normalized.loc[0, "summary"], "")
        self.assertEqual(normalized.loc[0, "reference_url"], "")


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
        self.assertIn("<th>名稱</th><th>形勢判斷</th><th>收盤</th><th>目標價</th><th>目標價/現價</th><th>題材</th>", response)
        self.assertIn("<th>風險與觀察</th><th>備註</th><th class='theme-summary-cell'>題材摘要</th><th class='source-cell'>來源</th></tr>", response)
        self.assertIn("class='row-action-cell'><button type='button' class='watchlist-action is-icon is-remove'", response)
        self.assertIn(">−</button>", response)
        self.assertNotIn("<th>互動</th>", response)
        self.assertIn("name='stock_meta_note' value='法說'", response)
        self.assertIn("document.getElementById('stockMetaFilter-note')", response)
        self.assertIn("filter.addEventListener('input', applyStockMetaFilters)", response)
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


if __name__ == "__main__":
    unittest.main()
