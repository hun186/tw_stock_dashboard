from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from api.constants import DAILY_THEME_REPORT_FILE

REPORT_DOWNLOAD_PATH = "/api/theme-report/download"
REPORT_STATUS_PATH = "/api/theme-report/status"
_TITLE_DATE_RE = re.compile(r"^#\s+台股每日題材快報（([^）]+)）", re.MULTILINE)


def _report_path() -> Path:
    return DAILY_THEME_REPORT_FILE


def theme_report_status_payload(report_path: Path | None = None) -> dict:
    path = report_path or _report_path()
    if not path.exists() or not path.is_file():
        return {
            "exists": False,
            "message": "尚未找到預建每日題材報告；請等待 GitHub Action 收盤後產生並部署。",
            "download_url": REPORT_DOWNLOAD_PATH,
        }

    content = ""
    try:
        content = path.read_text(encoding="utf-8", errors="ignore")[:4096]
    except OSError:
        content = ""
    title_match = _TITLE_DATE_RE.search(content)
    generated_at = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat()
    return {
        "exists": True,
        "as_of": title_match.group(1) if title_match else "",
        "generated_at": generated_at,
        "size_bytes": path.stat().st_size,
        "download_url": REPORT_DOWNLOAD_PATH,
        "message": "已找到 GitHub Action / 本機預建的每日題材報告，可直接下載。",
    }


def json_response(payload: dict, start_response, *, status: str = "200 OK"):
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    start_response(status, [("Content-Type", "application/json; charset=utf-8"), ("Content-Length", str(len(data)))])
    return [data]


def download_report_response(start_response, report_path: Path | None = None):
    path = report_path or _report_path()
    if not path.exists() or not path.is_file():
        return json_response(theme_report_status_payload(path), start_response, status="404 Not Found")
    data = path.read_bytes()
    headers = [
        ("Content-Type", "text/markdown; charset=utf-8"),
        ("Content-Length", str(len(data))),
        ("Content-Disposition", 'attachment; filename="daily_theme_report.md"'),
        ("Cache-Control", "public, max-age=300"),
    ]
    start_response("200 OK", headers)
    return [data]


__all__ = [
    "REPORT_DOWNLOAD_PATH",
    "REPORT_STATUS_PATH",
    "download_report_response",
    "json_response",
    "theme_report_status_payload",
]
