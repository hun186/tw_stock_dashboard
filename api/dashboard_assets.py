"""Static dashboard CSS and JavaScript assets."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

_ASSET_DIR = Path(__file__).with_name("static")
_JS_ASSETS = (
    "js/core.js",
    "js/dashboard_render.js",
    "js/browser_config.js",
    "js/watchlist.js",
    "js/stock_picker_core.js",
    "js/batch_watchlist_picker.js",
    "js/stock_filter_picker.js",
    "js/stock_meta.js",
    "js/stock_research_card.js",
    "js/dashboard_init.js",
    "js/intraday_refresh.js",
)


@lru_cache(maxsize=None)
def _read_dashboard_asset(relative_path: str) -> str:
    return (_ASSET_DIR / relative_path).read_text(encoding="utf-8")


DASHBOARD_CSS = _read_dashboard_asset("dashboard.css")
DASHBOARD_JS = "".join(_read_dashboard_asset(path) for path in _JS_ASSETS)
