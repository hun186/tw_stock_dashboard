from __future__ import annotations

import unittest
from urllib.parse import urlencode
from unittest.mock import patch

import pandas as pd

from api import dashboard_app
from api.dashboard_theme_selector import filter_analyzed_stocks, filter_stocks_by_summary_keyword


class DashboardThemeSelectorTests(unittest.TestCase):
    def test_summary_keyword_filter_is_applied_before_analysis_and_keeps_url_value(self) -> None:
        file_watchlist = pd.DataFrame([
            {"symbol": "2330.TW", "name": "台積電", "group": "AI晶片", "subgroup": "先進製程", "summary": "CPO 與先進封裝供應鏈"},
            {"symbol": "2382.TW", "name": "廣達", "group": "AI伺服器", "subgroup": "系統組裝", "summary": "AI 伺服器組裝"},
        ])
        llm_watchlist = pd.DataFrame(columns=["symbol", "name", "group", "subgroup", "summary", "reference_url"])
        industry_df = pd.DataFrame(columns=["industry", "industry_label", "symbol", "name", "group", "subgroup", "summary", "reference_url"])
        captured_symbols = []

        def fake_prefetch(stocks, *_args, **_kwargs):
            captured_symbols.append(stocks["symbol"].tolist())
            return {}

        query = urlencode({"theme_summary": "CPO"})
        with patch.object(dashboard_app, "load_watchlist", return_value=file_watchlist), \
            patch.object(dashboard_app, "load_gemini_agent_group_map", return_value=pd.DataFrame(columns=["symbol", "name", "group", "subgroup", "summary", "reference_url"])), \
            patch.object(dashboard_app, "load_llm_group_map", return_value=llm_watchlist), \
            patch.object(dashboard_app, "load_twse_industry_map", return_value=industry_df), \
            patch.object(dashboard_app, "prefetch_price_data", side_effect=fake_prefetch):
            response = b"".join(dashboard_app.app({"QUERY_STRING": query}, lambda *_args: None)).decode("utf-8")

        self.assertIn("題材型選股器", response)
        self.assertIn("name='theme_summary' value='CPO'", response)
        self.assertIn("name='theme_signal_code'", response)
        self.assertIn("name='theme_signal_bucket'", response)
        self.assertIn("name='theme_volume_ratio'", response)
        self.assertIn("符合股數</span><span class='summary-value'>1 檔", response)
        self.assertEqual(captured_symbols, [["2330.TW"]])

    def test_signal_code_bucket_and_volume_filters_are_shareable_and_do_not_break_meta_filters(self) -> None:
        file_watchlist = pd.DataFrame([
            {"symbol": "2330.TW", "name": "台積電", "group": "AI晶片", "subgroup": "先進製程", "summary": "CPO 高速傳輸"},
            {"symbol": "2382.TW", "name": "廣達", "group": "AI伺服器", "subgroup": "系統組裝", "summary": "AI 伺服器"},
            {"symbol": "4977.TW", "name": "眾達-KY", "group": "AI光通訊", "subgroup": "光通訊模組", "summary": "CPO 光通訊"},
        ])
        llm_watchlist = pd.DataFrame(columns=["symbol", "name", "group", "subgroup", "summary", "reference_url"])
        industry_df = pd.DataFrame(columns=["industry", "industry_label", "symbol", "name", "group", "subgroup", "summary", "reference_url"])
        meta_payload = {"2330.TW": {"action": "波段"}, "4977.TW": {"action": "波段"}}

        def fake_analysis(symbol, *_args, **_kwargs):
            is_winner = symbol == "2330.TW"
            ratio = 2.2 if is_winner else 1.2
            code = "BREAKOUT_STRONG" if is_winner else "MA20_SUPPORT"
            bucket = "bull" if is_winner else "observe"
            df = pd.DataFrame()
            return {
                "df": df,
                "signal": {"bucket": bucket, "message": bucket, "score": 80 if is_winner else 40, "code": code, "label": "強突破" if is_winner else "回測 MA20 不破"},
                "bucket": bucket,
                "status": bucket,
                "close_text": "-",
                "sort_metrics": {"symbol": symbol, "close": -1.0, "volume": -1.0, "change_pct": 0.0, "target_ratio": -1.0, "signal_score": 80 if is_winner else 40, "volume_ratio": ratio},
                "target_price_text": "-",
                "target_ratio_text": "-",
            }

        query = urlencode({
            "theme_signal_code": "BREAKOUT_STRONG",
            "theme_signal_bucket": "bull",
            "theme_volume_ratio": "2",
            "stock_meta_action": "波段",
            "stock_meta_payload": __import__("json").dumps(meta_payload, ensure_ascii=False),
        })
        with patch.object(dashboard_app, "load_watchlist", return_value=file_watchlist), \
            patch.object(dashboard_app, "load_gemini_agent_group_map", return_value=pd.DataFrame(columns=["symbol", "name", "group", "subgroup", "summary", "reference_url"])), \
            patch.object(dashboard_app, "load_llm_group_map", return_value=llm_watchlist), \
            patch.object(dashboard_app, "load_twse_industry_map", return_value=industry_df), \
            patch.object(dashboard_app, "prefetch_price_data", return_value={}), \
            patch.object(dashboard_app, "_build_stock_analysis", side_effect=fake_analysis):
            response = b"".join(dashboard_app.app({"QUERY_STRING": query}, lambda *_args: None)).decode("utf-8")

        self.assertIn("<option value='bull' selected>偏多</option>", response)
        self.assertIn("<option value='BREAKOUT_STRONG' selected>強突破 (BREAKOUT_STRONG)</option>", response)
        self.assertIn("<option value='2' selected>成交量 ≥ 20日均量 2x</option>", response)
        self.assertIn("<option value='波段' selected></option>", response)
        self.assertIn("data-symbol='2330.TW'", response)
        self.assertNotIn("data-symbol='2382.TW'", response)
        self.assertNotIn("data-symbol='4977.TW'", response)
        self.assertIn("符合股數</span><span class='summary-value'>1 檔", response)

    def test_pure_theme_selector_filters_are_composable(self) -> None:
        stocks = pd.DataFrame([
            {"symbol": "2330.TW", "summary": "CPO 與先進封裝"},
            {"symbol": "2382.TW", "summary": "AI 伺服器"},
        ])
        self.assertEqual(filter_stocks_by_summary_keyword(stocks, "cpo")["symbol"].tolist(), ["2330.TW"])

        items = [
            {"symbol": "2330.TW", "bucket": "bull", "signal": {"code": "BREAKOUT_STRONG"}, "sort_metrics": {"volume_ratio": 2.1}},
            {"symbol": "2382.TW", "bucket": "bull", "signal": {"code": "VOLUME_UP"}, "sort_metrics": {"volume_ratio": 1.6}},
        ]
        filtered = filter_analyzed_stocks(
            items,
            status_filter="all",
            signal_bucket_filter="bull",
            signal_code_filter="BREAKOUT_STRONG",
            volume_ratio_filter="2",
        )
        self.assertEqual([item["symbol"] for item in filtered], ["2330.TW"])


if __name__ == "__main__":
    unittest.main()
