from __future__ import annotations

import os
import subprocess
import sys
from collections import namedtuple
from pathlib import Path

import pandas as pd

import api.theme_daily_report as theme_daily_report
from api.theme_daily_report import (
    PRICE_MISSING_TEXT,
    SUMMARY_MISSING_TEXT,
    DailyReportConfig,
    _price_volume_chart_svg,
    analyze_stock_pool_for_report,
    dated_daily_theme_report_path,
    render_daily_theme_report,
    short_summary,
)

StockRow = namedtuple("StockRow", ["symbol", "name", "group", "subgroup", "summary", "reference_url"])


def _item(
    symbol: str,
    name: str,
    group: str,
    subgroup: str,
    *,
    bucket: str,
    code: str,
    status: str,
    score: float,
    change_pct: float,
    summary: str = "Gemini 摘要指出此公司受惠 AI 伺服器與高速傳輸升級，後續觀察訂單能見度。",
    reference_url: str = "https://example.com/report",
    close_text: str = "100.00",
    has_price: bool = True,
) -> dict:
    return {
        "row": StockRow(symbol, name, group, subgroup, summary, reference_url),
        "df": pd.DataFrame({"Close": [100.0]}) if has_price else pd.DataFrame(),
        "signal": {"code": code, "message": status, "score": score, "bucket": bucket},
        "status": status,
        "bucket": bucket,
        "close_text": close_text if has_price else "-",
        "sort_metrics": {
            "symbol": symbol,
            "close": 100.0 if has_price else -1.0,
            "volume": 1000.0 if has_price else -1.0,
            "change_pct": change_pct,
            "signal_score": score,
            "volume_ratio": 2.0,
        },
    }


def test_dated_daily_theme_report_path_uses_as_of_to_preserve_history(tmp_path: Path) -> None:
    assert (
        dated_daily_theme_report_path("2026-05-12", reports_dir=tmp_path)
        == tmp_path / "daily_theme_report_2026-05-12.md"
    )


def test_generate_daily_theme_report_defaults_to_dated_history_file(tmp_path: Path, monkeypatch) -> None:
    stocks = pd.DataFrame([
        {
            "symbol": "2330.TW",
            "name": "台積電",
            "group": "AI晶片",
            "subgroup": "先進製程",
            "summary": "摘要",
            "reference_url": "https://example.com",
        },
    ])
    item = _item(
        "2330.TW",
        "台積電",
        "AI晶片",
        "先進製程",
        bucket="bull",
        code="BREAKOUT_STRONG",
        status="🔴 強突破",
        score=92,
        change_pct=4.2,
    )
    monkeypatch.setattr(theme_daily_report, "REPORTS_DIR", tmp_path)
    monkeypatch.setattr(theme_daily_report, "load_report_stock_pool", lambda: stocks)
    monkeypatch.setattr(theme_daily_report, "analyze_stock_pool_for_report", lambda stocks_arg, **kwargs: [item])

    output = theme_daily_report.generate_daily_theme_report(as_of="2026-05-12")

    assert output == tmp_path / "daily_theme_report_2026-05-12.md"
    assert output.exists()
    assert "# 台股每日題材快報（2026-05-12）" in output.read_text(encoding="utf-8")

def test_render_daily_theme_report_includes_phase5_sections_and_stock_context() -> None:
    analyzed = [
        _item("2330.TW", "台積電", "AI晶片", "先進製程", bucket="bull", code="BREAKOUT_STRONG", status="🔴 強突破", score=92, change_pct=4.2),
        _item("3443.TW", "創意", "AI晶片", "先進製程", bucket="warn", code="OVERHEATED", status="🟠 過熱", score=-20, change_pct=1.5),
        _item("2382.TW", "廣達", "AI伺服器", "組裝", bucket="bear", code="BREAK_MA20", status="🟢 跌破 MA20", score=-70, change_pct=-3.1),
    ]

    report = render_daily_theme_report(analyzed, config=DailyReportConfig(as_of="2026-05-12", top_n=2))

    assert "# 台股每日題材快報（2026-05-12）" in report
    assert "## 最強題材 Top N" in report
    assert "題材內強勢股" in report
    assert "題材內風險股" in report
    assert "## 新突破股" in report
    assert "## 過熱股" in report
    assert "## 跌破 MA20 股" in report
    assert "**2330.TW 台積電**" in report
    assert "Gemini 摘要" in report
    assert "reference_url：https://example.com/report" in report
    assert "熱度分數" in report


def test_render_daily_theme_report_embeds_three_month_price_volume_chart() -> None:
    dates = pd.date_range("2026-02-01", periods=70, freq="B")
    price_df = pd.DataFrame({
        "Date": dates,
        "Open": [100.0 + i * 0.4 for i in range(70)],
        "High": [102.0 + i * 0.4 for i in range(70)],
        "Low": [99.0 + i * 0.4 for i in range(70)],
        "Close": [101.0 + i * 0.4 for i in range(70)],
        "Volume": [1_000_000.0 + i * 10_000 for i in range(70)],
    })
    item = _item(
        "2330.TW",
        "台積電",
        "AI晶片",
        "先進製程",
        bucket="bull",
        code="BREAKOUT_STRONG",
        status="🔴 強突破",
        score=92,
        change_pct=4.2,
    )
    item["df"] = price_df

    report = render_daily_theme_report([item], config=DailyReportConfig(as_of="2026-05-12", top_n=1))

    assert "近三個月價量K線圖" in report
    assert "data:image/svg+xml;base64," in report


def test_report_price_volume_chart_uses_lots_axis_and_refclose_colors() -> None:
    price_df = pd.DataFrame({
        "Date": pd.date_range("2026-05-11", periods=2, freq="B"),
        "Open": [100.0, 95.0],
        "High": [102.0, 102.0],
        "Low": [99.0, 94.0],
        "Close": [101.0, 99.0],
        "RefClose": [100.0, 100.0],
        "Volume": [1_000_000.0, 2_500_000.0],
    })
    item = _item(
        "2330.TW",
        "台積電",
        "AI晶片",
        "先進製程",
        bucket="bull",
        code="BREAKOUT_STRONG",
        status="🔴 強突破",
        score=92,
        change_pct=4.2,
    )
    item["df"] = price_df

    svg = _price_volume_chart_svg(item)

    assert "成交量（張）" in svg
    assert "2,500張" in svg
    assert "1,250張" in svg
    assert "2,500,000" not in svg
    assert 'fill="#16a34a" opacity="0.55"' in svg


def test_render_daily_theme_report_marks_missing_price_summary_and_reference() -> None:
    analyzed = [
        _item(
            "0000.TW",
            "缺資料股",
            "未分類題材",
            "未分類次題材",
            bucket="bear",
            code="BREAK_MA20",
            status="⚪ 抓不到資料",
            score=-999,
            change_pct=-999,
            summary="",
            reference_url="",
            has_price=False,
        )
    ]

    report = render_daily_theme_report(analyzed, config=DailyReportConfig(as_of="2026-05-12"))

    assert "缺價格資料：1 檔" in report
    assert "缺 Gemini summary：1 檔" in report
    assert PRICE_MISSING_TEXT in report
    assert SUMMARY_MISSING_TEXT in report
    assert "⚠️ 缺 reference_url" in report
    assert "收盤 -，漲跌 -" in report


def test_render_daily_theme_report_falls_back_to_metadata_themes_without_prices() -> None:
    analyzed = [
        _item(
            "1111.TW",
            "甲公司",
            "AI供應鏈",
            "散熱",
            bucket="watch",
            code="",
            status="⚪ 抓不到資料",
            score=-999,
            change_pct=-999,
            has_price=False,
        ),
        _item(
            "2222.TW",
            "乙公司",
            "AI供應鏈",
            "散熱",
            bucket="watch",
            code="",
            status="⚪ 抓不到資料",
            score=-999,
            change_pct=-999,
            has_price=False,
        ),
        _item(
            "3333.TW",
            "丙公司",
            "車用電子",
            "連接器",
            bucket="watch",
            code="",
            status="⚪ 抓不到資料",
            score=-999,
            change_pct=-999,
            has_price=False,
        ),
    ]

    report = render_daily_theme_report(analyzed, config=DailyReportConfig(as_of="2026-05-12", top_n=1))

    assert "本次沒有可用價格資料" in report
    assert "### 1. AI供應鏈 / 散熱" in report
    assert "題材代表股" in report
    assert "**2222.TW 乙公司**" in report
    assert PRICE_MISSING_TEXT in report
    assert "價格資料不足，無法偵測技術訊號" in report


def test_short_summary_truncates_without_network_or_llm_calls() -> None:
    long_text = "甲" * 120
    result = short_summary(long_text, max_chars=20)

    assert result == "甲" * 19 + "…"
    assert short_summary("") == SUMMARY_MISSING_TEXT


def test_analyze_stock_pool_for_report_uses_injected_loader_to_avoid_network() -> None:
    stocks = pd.DataFrame([
        {
            "symbol": "2330.TW",
            "name": "台積電",
            "group": "AI晶片",
            "subgroup": "先進製程",
            "summary": "摘要",
            "reference_url": "https://example.com",
        },
    ])
    price_df = pd.DataFrame({
        "Date": pd.date_range("2026-04-01", periods=30),
        "Open": [100.0] * 30,
        "High": [102.0 + i for i in range(30)],
        "Low": [99.0] * 30,
        "Close": [100.0 + i for i in range(30)],
        "Volume": [1000.0 + i * 100 for i in range(30)],
    })
    calls = []

    def fake_loader(stocks_arg, period, interval, **kwargs):
        calls.append((period, interval, kwargs))
        return {"2330.TW": price_df}

    analyzed = analyze_stock_pool_for_report(stocks, price_data_loader=fake_loader)

    assert len(analyzed) == 1
    assert analyzed[0]["row"].symbol == "2330.TW"
    assert analyzed[0]["close_text"] != "-"
    assert calls == [("6mo", "1d", {"allow_live_fetch": False, "allow_stale_disk": True, "max_live_symbols": 0})]


def test_analyze_stock_pool_for_report_falls_back_to_broader_disk_cache_period() -> None:
    stocks = pd.DataFrame([
        {
            "symbol": "2330.TW",
            "name": "台積電",
            "group": "AI晶片",
            "subgroup": "先進製程",
            "summary": "摘要",
            "reference_url": "https://example.com",
        },
    ])
    fallback_df = pd.DataFrame({
        "Date": pd.date_range("2026-01-01", periods=35),
        "Open": [100.0] * 35,
        "High": [102.0 + i for i in range(35)],
        "Low": [99.0] * 35,
        "Close": [100.0 + i for i in range(35)],
        "Volume": [1000.0 + i * 100 for i in range(35)],
    })
    calls = []

    def fake_loader(stocks_arg, period, interval, **kwargs):
        calls.append((stocks_arg["symbol"].tolist(), period, interval, kwargs))
        return {"2330.TW": fallback_df} if period == "2y" else {"2330.TW": pd.DataFrame()}

    analyzed = analyze_stock_pool_for_report(stocks, price_data_loader=fake_loader)

    assert analyzed[0]["close_text"] != "-"
    assert calls == [
        (["2330.TW"], "6mo", "1d", {"allow_live_fetch": False, "allow_stale_disk": True, "max_live_symbols": 0}),
        (["2330.TW"], "2y", "1d", {"allow_live_fetch": False, "allow_stale_disk": True, "max_live_symbols": 0}),
    ]


def test_daily_report_script_imports_when_launched_by_file_path(tmp_path: Path) -> None:
    script = Path(__file__).resolve().parents[1] / "scripts" / "generate_theme_daily_report.py"
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import runpy, sys; runpy.run_path(sys.argv[1], run_name='daily_report_import_test')",
            str(script),
        ],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr


def test_api_main_starts_dev_server_when_launched_as_script(monkeypatch) -> None:
    import runpy

    import api.dashboard_server as dashboard_server

    calls = []

    def fake_run_dev_server(app):
        calls.append(app)

    monkeypatch.setattr(dashboard_server, "run_dev_server", fake_run_dev_server)

    runpy.run_module("api.main", run_name="__main__")

    assert len(calls) == 1
    assert callable(calls[0])
