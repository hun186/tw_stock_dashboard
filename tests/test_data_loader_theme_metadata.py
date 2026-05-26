from __future__ import annotations

import unittest
from unittest.mock import patch

import pandas as pd

from api import data_loader


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


    def test_normalize_group_map_prefers_official_name_when_symbol_conflicts(self) -> None:
        df = pd.DataFrame([
            {"symbol": "6990.TWO", "name": "華鉬", "group": "半導體", "subgroup": "材料"},
            {"symbol": "6990.TWO", "name": "台特化", "group": "半導體", "subgroup": "特氣"},
        ])

        with patch.object(data_loader, "load_twse_industry_map", return_value=pd.DataFrame([
            {"symbol": "6990.TWO", "name": "華鉬"}
        ])):
            normalized = data_loader._normalize_group_map(df)

        self.assertEqual(len(normalized), 1)
        self.assertEqual(normalized.loc[0, "symbol"], "6990.TWO")
        self.assertEqual(normalized.loc[0, "name"], "華鉬")

    def test_normalize_group_map_conflict_without_official_name_keeps_last(self) -> None:
        df = pd.DataFrame([
            {"symbol": "6990.TWO", "name": "華鉬", "group": "半導體", "subgroup": "材料"},
            {"symbol": "6990.TWO", "name": "台特化", "group": "半導體", "subgroup": "特氣"},
        ])

        with patch.object(data_loader, "load_twse_industry_map", return_value=pd.DataFrame([
            {"symbol": "2330.TW", "name": "台積電"}
        ])):
            normalized = data_loader._normalize_group_map(df)

        self.assertEqual(len(normalized), 1)
        self.assertEqual(normalized.loc[0, "name"], "台特化")


    def test_normalize_group_map_records_conflict_warning(self) -> None:
        df = pd.DataFrame([
            {"symbol": "6990.TWO", "name": "華鉬", "group": "半導體", "subgroup": "材料"},
            {"symbol": "6990.TWO", "name": "台特化", "group": "半導體", "subgroup": "特氣"},
        ])
        with patch.object(data_loader, "load_twse_industry_map", return_value=pd.DataFrame([
            {"symbol": "6990.TWO", "name": "華鉬"}
        ])):
            data_loader._normalize_group_map(df)

        warnings = data_loader.get_last_group_map_warnings()
        assert warnings
        assert "6990.TWO" in warnings[0]
