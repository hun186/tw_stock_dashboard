from __future__ import annotations

import unittest

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


if __name__ == "__main__":
    unittest.main()
