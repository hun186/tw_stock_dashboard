from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from api import dashboard_app
from api.theme_report_endpoint import theme_report_status_payload


def _call_app(path: str):
    captured = []

    def start_response(status, headers):
        captured.append((status, dict(headers)))

    body = b"".join(dashboard_app.app({"PATH_INFO": path, "QUERY_STRING": ""}, start_response))
    return captured[0][0], captured[0][1], body


def test_theme_report_status_payload_reads_prebuilt_report_metadata(tmp_path: Path) -> None:
    report = tmp_path / "daily_theme_report.md"
    report.write_text("# 台股每日題材快報（2026-05-12）\n\n內容", encoding="utf-8")

    payload = theme_report_status_payload(report)

    assert payload["exists"] is True
    assert payload["as_of"] == "2026-05-12"
    assert payload["size_bytes"] > 0
    assert payload["download_url"] == "/api/theme-report/download"


def test_dashboard_app_serves_theme_report_status_and_download(tmp_path: Path) -> None:
    report = tmp_path / "daily_theme_report.md"
    report.write_text("# 台股每日題材快報（2026-05-12）\n\n- 測試報告", encoding="utf-8")

    with patch("api.theme_report_endpoint.DAILY_THEME_REPORT_FILE", report):
        status, headers, body = _call_app("/api/theme-report/status")
        payload = json.loads(body.decode("utf-8"))
        assert status == "200 OK"
        assert headers["Content-Type"] == "application/json; charset=utf-8"
        assert payload["exists"] is True
        assert payload["as_of"] == "2026-05-12"

        status, headers, body = _call_app("/api/theme-report/download")
        assert status == "200 OK"
        assert headers["Content-Type"] == "text/markdown; charset=utf-8"
        assert "daily_theme_report.md" in headers["Content-Disposition"]
        assert "測試報告" in body.decode("utf-8")


def test_dashboard_app_reports_missing_theme_report(tmp_path: Path) -> None:
    missing = tmp_path / "missing.md"

    with patch("api.theme_report_endpoint.DAILY_THEME_REPORT_FILE", missing):
        status, headers, body = _call_app("/api/theme-report/download")
        payload = json.loads(body.decode("utf-8"))

    assert status == "404 Not Found"
    assert headers["Content-Type"] == "application/json; charset=utf-8"
    assert payload["exists"] is False
    assert "尚未找到" in payload["message"]
