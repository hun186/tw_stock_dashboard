from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd

from api.main import APP_DIR, load_watchlist, load_twse_industry_map, fetch_price

OUT_DIR = APP_DIR / "prebuilt_cache"
DEFAULT_PERIODS = [("2y", "1d"), ("6mo", "1d"), ("2d", "1m")]


def file_path(symbol: str, period: str, interval: str) -> Path:
    safe_symbol = symbol.replace("/", "_").replace(".", "_")
    return OUT_DIR / f"{safe_symbol}__{period}__{interval}.pkl"


def build_one(symbol: str, period: str, interval: str) -> tuple[str, str, str, bool]:
    df = fetch_price(symbol, period, interval)
    if df.empty:
        return symbol, period, interval, False
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df.to_pickle(file_path(symbol, period, interval))
    return symbol, period, interval, True


def main() -> None:
    watch = load_watchlist(APP_DIR / "watchlist.csv")
    industry = load_twse_industry_map()

    symbols = sorted(set(
        watch["symbol"].dropna().astype(str).tolist()
        + industry["symbol"].dropna().astype(str).tolist()
    ))
    tasks = [(s, p, i) for s in symbols for p, i in DEFAULT_PERIODS]

    with ThreadPoolExecutor(max_workers=8) as ex:
        results = list(ex.map(lambda x: build_one(*x), tasks))

    ok = sum(1 for *_, success in results if success)
    print(f"built {ok}/{len(results)} cache files into {OUT_DIR}")


if __name__ == "__main__":
    main()
