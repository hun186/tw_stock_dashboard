from __future__ import annotations

import os
import unittest
from unittest.mock import patch

import pandas as pd

from api.dashboard_pipeline import run_dashboard_analysis


class DashboardPipelineLimitTests(unittest.TestCase):
    def _stocks(self, count: int) -> pd.DataFrame:
        return pd.DataFrame([
            {
                "symbol": f"{idx:04d}.TW",
                "name": f"ETF{idx}",
                "group": "ETF與基金",
                "subgroup": "債券ETF" if idx % 2 else "台股寬基ETF",
                "summary": "",
                "reference_url": "",
            }
            for idx in range(count)
        ])

    def _prefetch(self, stocks, *_args, **_kwargs):
        self.prefetch_counts.append(len(stocks))
        return {}

    def _analysis(self, symbol, *_args):
        return {
            "df": pd.DataFrame(),
            "signal": "-",
            "status": "中性",
            "bucket": "neutral",
            "close_text": "-",
            "sort_metrics": {"symbol": symbol, "change_pct": 0.0, "signal_score": 0.0},
            "target_price_text": "-",
            "target_ratio_text": "-",
        }

    def test_serverless_topic_requests_can_analyze_complete_etf_subtheme_pool(self) -> None:
        self.prefetch_counts = []

        with patch.dict(os.environ, {"VERCEL": "1"}, clear=False):
            result = run_dashboard_analysis(
                stocks=self._stocks(281),
                period="daily",
                fetch_period="6mo",
                fetch_interval="1d",
                display_period="6mo",
                show_target_price=False,
                card_sort="symbol",
                status_filter="all",
                tab="category",
                industry="all",
                custom_watchlist_raw="",
                group_filter="ETF與基金",
                subgroup_filter="all",
                prefetch_price_data=self._prefetch,
                build_stock_analysis=self._analysis,
            )

        self.assertFalse(result.is_limited_analysis)
        self.assertEqual(result.candidate_count, 281)
        self.assertEqual(len(result.analyzed_stocks), 281)
        self.assertEqual(self.prefetch_counts, [281])

    def test_serverless_broad_requests_keep_conservative_limit(self) -> None:
        self.prefetch_counts = []

        with patch.dict(os.environ, {"VERCEL": "1"}, clear=False):
            result = run_dashboard_analysis(
                stocks=self._stocks(281),
                period="daily",
                fetch_period="6mo",
                fetch_interval="1d",
                display_period="6mo",
                show_target_price=False,
                card_sort="symbol",
                status_filter="all",
                tab="category",
                industry="all",
                custom_watchlist_raw="",
                group_filter="all",
                subgroup_filter="all",
                prefetch_price_data=self._prefetch,
                build_stock_analysis=self._analysis,
            )

        self.assertTrue(result.is_limited_analysis)
        self.assertEqual(result.candidate_count, 281)
        self.assertEqual(len(result.analyzed_stocks), 240)
        self.assertEqual(result.max_serverless_analysis_stocks, 240)
        self.assertEqual(self.prefetch_counts, [240])


if __name__ == "__main__":
    unittest.main()
