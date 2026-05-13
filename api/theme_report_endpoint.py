from __future__ import annotations

import json
import re
from datetime import date, datetime, time, timezone
from pathlib import Path
from urllib.parse import parse_qs
from zoneinfo import ZoneInfo

from api.constants import DAILY_THEME_REPORT_FILE, REPORTS_DIR

REPORT_DOWNLOAD_PATH = "/api/theme-report/download"
REPORT_STATUS_PATH = "/api/theme-report/status"
REPORT_LIST_PATH = "/api/theme-report/list"
REPORT_CONTENT_PATH = "/api/theme-report/content"
_TITLE_DATE_RE = re.compile(r"^#\s+台股每日題材快報（([^）]+)）", re.MULTILINE)
_TITLE_RE = re.compile(r"^#\s+(.+)$", re.MULTILINE)
_TAIPEI_TZ = ZoneInfo("Asia/Taipei")


def _parse_as_of_date(value: str) -> date | None:
    text = (value or "").strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def _report_generated_metadata(path: Path, as_of: str) -> tuple[str, str, str]:
    stat = path.stat()
    mtime_utc = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
    mtime_taipei = mtime_utc.astimezone(_TAIPEI_TZ)
    as_of_date = _parse_as_of_date(as_of)
    if as_of_date and mtime_taipei.date() < as_of_date:
        report_datetime = datetime.combine(as_of_date, time.min, tzinfo=_TAIPEI_TZ)
        return report_datetime.isoformat(), f"{as_of}（依報告日期）", "report_date"
    return mtime_utc.isoformat(), mtime_taipei.strftime("%Y-%m-%d %H:%M:%S"), "file_mtime"


def _report_path() -> Path:
    return DAILY_THEME_REPORT_FILE


def _reports_dir() -> Path:
    return REPORTS_DIR


def _report_name_from_environ(environ: dict | None) -> str:
    if not environ:
        return ""
    params = parse_qs(environ.get("QUERY_STRING", ""), keep_blank_values=True)
    return (params.get("name") or params.get("file") or [""])[0]


def _safe_report_path(name: str | None = None, *, default_to_latest: bool = True) -> Path | None:
    raw_name = (name or "").strip()
    if not raw_name:
        if not default_to_latest:
            return None
        return latest_report_path() or _report_path()
    candidate = Path(raw_name)
    if candidate.name != raw_name or candidate.suffix.lower() != ".md":
        return None
    reports_dir = _reports_dir().resolve()
    path = (reports_dir / candidate.name).resolve()
    if reports_dir != path.parent:
        return None
    return path


def _read_report_head(path: Path, limit: int = 4096) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")[:limit]
    except OSError:
        return ""


def _report_metadata(path: Path) -> dict:
    content = _read_report_head(path)
    title_match = _TITLE_RE.search(content)
    title_date_match = _TITLE_DATE_RE.search(content)
    stat = path.stat()
    as_of = title_date_match.group(1).strip() if title_date_match else ""
    generated_at, updated_label, generated_at_source = _report_generated_metadata(path, as_of)
    return {
        "name": path.name,
        "title": title_match.group(1).strip() if title_match else path.stem,
        "as_of": as_of,
        "generated_at": generated_at,
        "updated_label": updated_label,
        "generated_at_source": generated_at_source,
        "size_bytes": stat.st_size,
        "download_url": f"{REPORT_DOWNLOAD_PATH}?name={path.name}",
        "content_url": f"{REPORT_CONTENT_PATH}?name={path.name}",
    }


def list_report_files(report_dir: Path | None = None) -> list[Path]:
    directory = report_dir or _reports_dir()
    if not directory.exists() or not directory.is_dir():
        return []
    reports = [path for path in directory.glob("*.md") if path.is_file()]

    def sort_key(path: Path) -> tuple[str, float, str]:
        content = _read_report_head(path)
        title_date_match = _TITLE_DATE_RE.search(content)
        as_of = title_date_match.group(1).strip() if title_date_match else ""
        return (as_of, path.stat().st_mtime, path.name)

    return sorted(reports, key=sort_key, reverse=True)


def latest_report_path(report_dir: Path | None = None) -> Path | None:
    reports = list_report_files(report_dir)
    if reports:
        return reports[0]
    path = _report_path()
    return path if path.exists() and path.is_file() else None


def theme_report_list_payload(report_dir: Path | None = None) -> dict:
    reports = [_report_metadata(path) for path in list_report_files(report_dir)]
    return {
        "exists": bool(reports),
        "count": len(reports),
        "reports": reports,
        "latest": reports[0] if reports else None,
        "message": "已找到歷史題材報告，可線上檢視或下載 Markdown。" if reports else "尚未找到任何預建題材報告；請等待 GitHub Action 收盤後產生並部署。",
    }


def theme_report_status_payload(report_path: Path | None = None) -> dict:
    path = report_path or latest_report_path() or _report_path()
    if not path.exists() or not path.is_file():
        return {
            "exists": False,
            "message": "尚未找到預建每日題材報告；請等待 GitHub Action 收盤後產生並部署。",
            "download_url": REPORT_DOWNLOAD_PATH,
        }

    payload = _report_metadata(path)
    payload.update(
        {
            "exists": True,
            "message": "已找到 GitHub Action / 本機預建的題材報告，可線上檢視或下載 Markdown。",
        }
    )
    return payload


def theme_report_content_payload(environ: dict | None = None, report_path: Path | None = None) -> tuple[dict, str]:
    path = report_path or _safe_report_path(_report_name_from_environ(environ))
    if path is None:
        return {"exists": False, "message": "報告檔名不合法。"}, "404 Not Found"
    if not path.exists() or not path.is_file():
        return {"exists": False, "message": "找不到指定的題材報告。"}, "404 Not Found"
    metadata = _report_metadata(path)
    content = path.read_text(encoding="utf-8", errors="ignore")
    return {"exists": True, "report": metadata, "content": content}, "200 OK"


def json_response(payload: dict, start_response, *, status: str = "200 OK"):
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    start_response(status, [("Content-Type", "application/json; charset=utf-8"), ("Content-Length", str(len(data)))])
    return [data]


def download_report_response(start_response, report_path: Path | None = None, environ: dict | None = None):
    path = report_path or _safe_report_path(_report_name_from_environ(environ))
    if path is None:
        return json_response({"exists": False, "message": "報告檔名不合法。"}, start_response, status="404 Not Found")
    if not path.exists() or not path.is_file():
        return json_response(theme_report_status_payload(path), start_response, status="404 Not Found")
    data = path.read_bytes()
    headers = [
        ("Content-Type", "text/markdown; charset=utf-8"),
        ("Content-Length", str(len(data))),
        ("Content-Disposition", f'attachment; filename="{path.name}"'),
        ("Cache-Control", "public, max-age=300"),
    ]
    start_response("200 OK", headers)
    return [data]


__all__ = [
    "REPORT_CONTENT_PATH",
    "REPORT_DOWNLOAD_PATH",
    "REPORT_LIST_PATH",
    "REPORT_STATUS_PATH",
    "download_report_response",
    "json_response",
    "list_report_files",
    "theme_report_content_payload",
    "theme_report_list_payload",
    "theme_report_status_payload",
]
