from __future__ import annotations

from api import dashboard_controller
from api.dashboard_analysis import build_stock_analysis as _build_stock_analysis
from api.dashboard_pipeline import (
    DEFAULT_LIVE_FETCH_THRESHOLD,
    resolve_live_fetch_controls as _resolve_live_fetch_controls,
)
from api.dashboard_request import parse_dashboard_request, positive_int_param as _positive_int_param
from api.dashboard_stock_pool import (
    ensure_stock_group_columns as _ensure_stock_group_columns,
    merge_stock_group_sources as _merge_stock_group_sources,
    sort_stocks_by_symbol as _sort_stocks_by_symbol,
    stock_code_sort_value as _stock_code_sort_value,
    stock_group_frame as _stock_group_frame,
)
from api.data_loader import (
    load_gemini_agent_group_map,
    load_llm_group_map,
    load_twse_industry_map,
    load_watchlist,
)
from api.market_data import prefetch_price_data
from api.theme_report_endpoint import (
    REPORT_CONTENT_PATH,
    REPORT_DOWNLOAD_PATH,
    REPORT_LIST_PATH,
    REPORT_STATUS_PATH,
    download_report_response,
    json_response,
    theme_report_content_payload,
    theme_report_list_payload,
    theme_report_status_payload,
)


__all__ = [
    "DEFAULT_LIVE_FETCH_THRESHOLD",
    "_ensure_stock_group_columns",
    "_merge_stock_group_sources",
    "_positive_int_param",
    "_resolve_live_fetch_controls",
    "_sort_stocks_by_symbol",
    "_stock_code_sort_value",
    "_stock_group_frame",
    "app",
]


def _sync_controller_dependencies() -> None:
    dashboard_controller.load_watchlist = load_watchlist
    dashboard_controller.load_gemini_agent_group_map = load_gemini_agent_group_map
    dashboard_controller.load_llm_group_map = load_llm_group_map
    dashboard_controller.load_twse_industry_map = load_twse_industry_map
    dashboard_controller.prefetch_price_data = prefetch_price_data
    dashboard_controller._build_stock_analysis = _build_stock_analysis


def app(environ, start_response):
    path = environ.get("PATH_INFO", "") or "/"
    if path == REPORT_STATUS_PATH:
        return json_response(theme_report_status_payload(), start_response)
    if path == REPORT_LIST_PATH:
        return json_response(theme_report_list_payload(), start_response)
    if path == REPORT_CONTENT_PATH:
        payload, status = theme_report_content_payload(environ)
        return json_response(payload, start_response, status=status)
    if path == REPORT_DOWNLOAD_PATH:
        return download_report_response(start_response, environ=environ)

    _sync_controller_dependencies()
    request = parse_dashboard_request(environ)
    body = dashboard_controller.render_dashboard_response(request)
    data = body.encode("utf-8")
    start_response("200 OK", [("Content-Type", "text/html; charset=utf-8"), ("Content-Length", str(len(data)))])
    return [data]


if __name__ == "__main__":
    from api.dashboard_server import run_dev_server

    run_dev_server(app)
