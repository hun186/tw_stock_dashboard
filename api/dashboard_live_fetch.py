from __future__ import annotations

DEFAULT_LIVE_FETCH_THRESHOLD = 80
SINGLE_CATEGORY_LIVE_FETCH_BUFFER = 20


def resolve_live_fetch_controls(
    *,
    is_serverless_runtime: bool,
    stock_count: int,
    is_custom_watchlist: bool,
    tab: str,
    industry: str,
) -> tuple[bool, int]:
    is_single_industry_category = tab == "category" and industry != "all"
    if is_single_industry_category:
        max_live_symbols = max(DEFAULT_LIVE_FETCH_THRESHOLD, stock_count + SINGLE_CATEGORY_LIVE_FETCH_BUFFER)
    elif is_custom_watchlist or not is_serverless_runtime:
        max_live_symbols = max(DEFAULT_LIVE_FETCH_THRESHOLD, stock_count)
    else:
        max_live_symbols = DEFAULT_LIVE_FETCH_THRESHOLD

    allow_live_fetch = (
        (not is_serverless_runtime)
        or stock_count <= DEFAULT_LIVE_FETCH_THRESHOLD
        or is_custom_watchlist
        or is_single_industry_category
    )
    return allow_live_fetch, max_live_symbols
