from __future__ import annotations

import argparse
import base64
import html
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Callable, Iterable, Sequence

import pandas as pd

from api.charts import _volume_in_lots
from api.constants import (
    DAILY_THEME_REPORT_FILE,
    GEMINI_AGENT_GROUP_FILE,
    LLM_GROUP_FILE,
    LLM_GROUP_SHEET,
    REPORTS_DIR,
    WATCHLIST_FILE,
)
from api.dashboard_analysis import build_stock_analysis
from api.dashboard_theme_rotation import ThemeRotationRow, build_theme_rotation_rows
from api.data_loader import load_gemini_agent_group_map, load_llm_group_map, load_watchlist
from api.market_data import prefetch_price_data

BREAKOUT_CODES = {"BREAKOUT_EXPLOSIVE", "BREAKOUT_STRONG", "BREAKOUT_MINOR"}
OVERHEAT_CODES = {"OVERHEATED", "STRONG_OVERHEAT_EDGE", "STRONG_OVERHEAT_HIGH"}
MA20_BREAK_CODES = {"BREAK_MA20"}
PRICE_MISSING_TEXT = "⚠️ 缺價格資料：無法計算技術訊號與收盤價。"
CHART_MISSING_TEXT = "⚠️ 近三個月價量K線圖：價格欄位不足，暫無法繪製。"
SUMMARY_MISSING_TEXT = "⚠️ 缺 Gemini summary：請補齊 summary 欄位。"
URL_MISSING_TEXT = "⚠️ 缺 reference_url：請補齊 reference_url 欄位。"


@dataclass(frozen=True, slots=True)
class DailyReportConfig:
    as_of: str
    top_n: int = 5
    theme_stock_limit: int = 5
    highlight_limit: int = 10


def _clean_text(value: object) -> str:
    return str(value or "").strip()


def dated_daily_theme_report_path(as_of: str | None = None, *, reports_dir: Path | None = None) -> Path:
    reports_dir = reports_dir or REPORTS_DIR
    report_date = _clean_text(as_of) or date.today().isoformat()
    try:
        report_date = date.fromisoformat(report_date[:10]).isoformat()
    except ValueError:
        report_date = date.today().isoformat()
    return reports_dir / f"daily_theme_report_{report_date}.md"


def short_summary(summary: object, *, max_chars: int = 90) -> str:
    text = " ".join(_clean_text(summary).split())
    if not text:
        return SUMMARY_MISSING_TEXT
    return text if len(text) <= max_chars else f"{text[: max_chars - 1]}…"


def stock_reference_text(reference_url: object) -> str:
    url = _clean_text(reference_url)
    return url if url else URL_MISSING_TEXT


def signal_code(item: dict) -> str:
    signal = item.get("signal", {})
    return _clean_text(signal.get("code")) if isinstance(signal, dict) else ""


def row_value(item: dict, field: str) -> str:
    row = item.get("row")
    return _clean_text(getattr(row, field, ""))


def has_price_data(item: dict) -> bool:
    df = item.get("df")
    return isinstance(df, pd.DataFrame) and not df.empty and item.get("close_text") not in {None, "", "-"}


def _sort_by_signal_then_change(items: Iterable[dict], *, reverse: bool = True) -> list[dict]:
    return sorted(
        list(items or []),
        key=lambda item: (
            float(item.get("sort_metrics", {}).get("signal_score", -999) or -999),
            float(item.get("sort_metrics", {}).get("change_pct", -999) or -999),
        ),
        reverse=reverse,
    )


def _stock_line(item: dict) -> str:
    symbol = row_value(item, "symbol") or "未知代號"
    name = row_value(item, "name") or "未知名稱"
    group = row_value(item, "group") or "未分類"
    subgroup = row_value(item, "subgroup") or "未分類"
    signal = item.get("status") or "⚪ 無形勢判斷"
    close = item.get("close_text") or "-"
    sort_metrics = item.get("sort_metrics", {}) if isinstance(item.get("sort_metrics"), dict) else {}
    change = sort_metrics.get("change_pct")
    change_text = "-" if (not has_price_data(item) or change in {None, ""}) else f"{float(change):+.2f}%"
    summary = short_summary(row_value(item, "summary"))
    reference = stock_reference_text(row_value(item, "reference_url"))
    price_note = "" if has_price_data(item) else f" — {PRICE_MISSING_TEXT}"
    return (
        f"- **{symbol} {name}**（{group} / {subgroup}）：{signal}，"
        f"收盤 {close}，漲跌 {change_text}{price_note}\n"
        f"  - Gemini 摘要：{summary}\n"
        f"  - reference_url：{reference}\n"
        f"{_stock_chart_markdown(item)}"
    )


def _scale_value(value: float, min_value: float, max_value: float, top: float, height: float) -> float:
    if max_value <= min_value:
        return top + height / 2
    return top + (max_value - value) / (max_value - min_value) * height


def _chart_source_df(item: dict, *, max_points: int = 66) -> pd.DataFrame:
    df = item.get("df")
    required = ["Date", "Open", "High", "Low", "Close", "Volume"]
    if not isinstance(df, pd.DataFrame) or df.empty or not set(required).issubset(df.columns):
        return pd.DataFrame(columns=required)
    columns = required + (["RefClose"] if "RefClose" in df.columns else [])
    chart_df = df[columns].copy()
    for column in ["Open", "High", "Low", "Close", "Volume", "RefClose"]:
        if column in chart_df.columns:
            chart_df[column] = pd.to_numeric(chart_df[column], errors="coerce")
    chart_df["Date"] = pd.to_datetime(chart_df["Date"], errors="coerce")
    chart_df = chart_df.dropna(subset=required).tail(max_points).reset_index(drop=True)
    return chart_df


def _price_volume_chart_svg(item: dict, *, width: int = 760, height: int = 320) -> str:
    chart_df = _chart_source_df(item)
    if chart_df.empty:
        return ""

    symbol = row_value(item, "symbol") or "未知代號"
    name = row_value(item, "name") or "未知名稱"
    title = f"{symbol} {name}｜近三個月價K / 量K線圖"
    margin_left, margin_right, margin_top, margin_bottom = 72, 18, 34, 26
    gap = 16
    price_height = 170
    volume_height = height - margin_top - margin_bottom - gap - price_height
    plot_width = width - margin_left - margin_right
    price_top = margin_top
    volume_top = price_top + price_height + gap
    count = len(chart_df)
    step = plot_width / max(count, 1)
    candle_width = max(2.0, min(8.0, step * 0.58))

    price_min = float(chart_df["Low"].min())
    price_max = float(chart_df["High"].max())
    pad = max((price_max - price_min) * 0.08, price_max * 0.01, 0.01)
    price_min -= pad
    price_max += pad
    chart_df["VolumeLots"] = _volume_in_lots(chart_df["Volume"])
    volume_max = max(float(chart_df["VolumeLots"].max()), 1.0)
    up_color = "#ef4444"
    down_color = "#16a34a"
    grid_color = "#e2e8f0"
    text_color = "#334155"
    muted_color = "#64748b"

    elements = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{html.escape(title)}">',
        '<rect width="100%" height="100%" rx="16" fill="#ffffff"/>',
        f'<text x="{margin_left}" y="22" fill="{text_color}" font-size="15" font-family="Arial, sans-serif" font-weight="700">{html.escape(title)}</text>',
    ]

    for ratio in [0, 0.25, 0.5, 0.75, 1.0]:
        y = price_top + ratio * price_height
        value = price_max - ratio * (price_max - price_min)
        elements.append(f'<line x1="{margin_left}" x2="{width - margin_right}" y1="{y:.1f}" y2="{y:.1f}" stroke="{grid_color}" stroke-width="1"/>')
        elements.append(f'<text x="{margin_left - 8}" y="{y + 4:.1f}" text-anchor="end" fill="{muted_color}" font-size="10" font-family="Arial, sans-serif">{value:.1f}</text>')
    for ratio in [0, 0.5, 1.0]:
        y = volume_top + ratio * volume_height
        value = volume_max * (1 - ratio)
        elements.append(f'<line x1="{margin_left}" x2="{width - margin_right}" y1="{y:.1f}" y2="{y:.1f}" stroke="{grid_color}" stroke-width="1"/>')
        elements.append(f'<text x="{margin_left - 8}" y="{y + 4:.1f}" text-anchor="end" fill="{muted_color}" font-size="10" font-family="Arial, sans-serif">{value:,.0f}張</text>')
    elements.append(f'<text x="{margin_left}" y="{volume_top - 5:.1f}" fill="{muted_color}" font-size="10" font-family="Arial, sans-serif">成交量（張）</text>')

    for idx, row in chart_df.iterrows():
        x = margin_left + idx * step + step / 2
        open_price = float(row["Open"])
        high = float(row["High"])
        low = float(row["Low"])
        close = float(row["Close"])
        volume = float(row["VolumeLots"])
        ref_close = float(row["RefClose"]) if "RefClose" in chart_df.columns and not pd.isna(row.get("RefClose")) else open_price
        color = up_color if close >= ref_close else down_color
        y_high = _scale_value(high, price_min, price_max, price_top, price_height)
        y_low = _scale_value(low, price_min, price_max, price_top, price_height)
        y_open = _scale_value(open_price, price_min, price_max, price_top, price_height)
        y_close = _scale_value(close, price_min, price_max, price_top, price_height)
        body_top = min(y_open, y_close)
        body_height = max(abs(y_close - y_open), 1.4)
        volume_bar_height = volume / volume_max * volume_height
        elements.append(f'<line x1="{x:.1f}" x2="{x:.1f}" y1="{y_high:.1f}" y2="{y_low:.1f}" stroke="{color}" stroke-width="1.3"/>')
        elements.append(f'<rect x="{x - candle_width / 2:.1f}" y="{body_top:.1f}" width="{candle_width:.1f}" height="{body_height:.1f}" fill="{color}" opacity="0.9"/>')
        elements.append(f'<rect x="{x - candle_width / 2:.1f}" y="{volume_top + volume_height - volume_bar_height:.1f}" width="{candle_width:.1f}" height="{volume_bar_height:.1f}" fill="{color}" opacity="0.55"/>')

    first_date = chart_df.iloc[0]["Date"].strftime("%Y-%m-%d")
    last_date = chart_df.iloc[-1]["Date"].strftime("%Y-%m-%d")
    elements.extend([
        f'<text x="{margin_left}" y="{height - 8}" fill="{muted_color}" font-size="10" font-family="Arial, sans-serif">{first_date}</text>',
        f'<text x="{width - margin_right}" y="{height - 8}" text-anchor="end" fill="{muted_color}" font-size="10" font-family="Arial, sans-serif">{last_date}</text>',
        '</svg>',
    ])
    return "".join(elements)


def _stock_chart_markdown(item: dict) -> str:
    svg = _price_volume_chart_svg(item)
    if not svg:
        return f"  - {CHART_MISSING_TEXT}"
    encoded = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    symbol = row_value(item, "symbol") or "stock"
    name = row_value(item, "name") or ""
    alt = f"{symbol} {name} 近三個月價量K線圖".strip()
    return f"![{alt}](data:image/svg+xml;base64,{encoded})"


def _build_metadata_theme_rows(analyzed_stocks: Iterable[dict]) -> list[ThemeRotationRow]:
    groups: dict[tuple[str, str], dict[str, float]] = {}
    for item in analyzed_stocks or []:
        group = row_value(item, "group")
        subgroup = row_value(item, "subgroup")
        if not group and not subgroup:
            continue
        key = (group, subgroup)
        entry = groups.setdefault(key, {"stock_count": 0.0, "summary_count": 0.0, "reference_count": 0.0})
        entry["stock_count"] += 1
        if row_value(item, "summary"):
            entry["summary_count"] += 1
        if row_value(item, "reference_url"):
            entry["reference_count"] += 1

    rows: list[ThemeRotationRow] = []
    for (group, subgroup), entry in groups.items():
        stock_count = int(entry["stock_count"])
        if stock_count <= 0:
            continue
        summary_ratio = entry["summary_count"] / stock_count
        reference_ratio = entry["reference_count"] / stock_count
        metadata_score = min(stock_count, 50) + summary_ratio * 10.0 + reference_ratio * 5.0
        rows.append(
            ThemeRotationRow(
                group=group,
                subgroup=subgroup,
                stock_count=stock_count,
                bull_count=0,
                observe_count=0,
                warn_count=0,
                bear_count=0,
                neutral_count=stock_count,
                avg_change_pct=0.0,
                avg_signal_score=0.0,
                heat_score=round(metadata_score, 1),
            )
        )

    rows.sort(key=lambda row: (row.heat_score, row.stock_count, row.group_label, row.subgroup_label), reverse=True)
    return rows


def _theme_stock_sections(
    theme: ThemeRotationRow,
    analyzed_stocks: list[dict],
    *,
    limit: int,
    metadata_only: bool = False,
) -> str:
    theme_items = [
        item
        for item in analyzed_stocks
        if row_value(item, "group") == theme.group and row_value(item, "subgroup") == theme.subgroup
    ]
    strong = _sort_by_signal_then_change([item for item in theme_items if item.get("bucket") == "bull"])[:limit]
    risk = _sort_by_signal_then_change([item for item in theme_items if item.get("bucket") in {"warn", "bear"}], reverse=False)[:limit]

    def render_list(items: list[dict], empty_text: str) -> str:
        if not items:
            return f"- {empty_text}"
        return "\n".join(_stock_line(item) for item in items)

    if metadata_only:
        representative = sorted(
            theme_items,
            key=lambda item: (
                bool(row_value(item, "summary")),
                bool(row_value(item, "reference_url")),
                row_value(item, "symbol"),
            ),
            reverse=True,
        )[:limit]
        return (
            "**題材代表股（缺價格時先依股池資料列示）**\n"
            f"{render_list(representative, '本題材目前沒有可列示的代表股。')}"
        )

    return (
        "**題材內強勢股**\n"
        f"{render_list(strong, '本題材目前沒有偏多強勢股。')}\n\n"
        "**題材內風險股**\n"
        f"{render_list(risk, '本題材目前沒有警示或轉弱風險股。')}"
    )


def _render_stock_collection(title: str, items: Iterable[dict], *, empty_text: str, limit: int) -> str:
    selected = list(items or [])[:limit]
    if not selected:
        return f"## {title}\n\n- {empty_text}"
    return f"## {title}\n\n" + "\n".join(_stock_line(item) for item in selected)


def render_daily_theme_report(
    analyzed_stocks: list[dict],
    *,
    config: DailyReportConfig | None = None,
) -> str:
    config = config or DailyReportConfig(as_of=date.today().isoformat())
    analyzed_stocks = list(analyzed_stocks or [])
    price_ready_stocks = [item for item in analyzed_stocks if has_price_data(item)]
    metadata_only_themes = not price_ready_stocks and bool(analyzed_stocks)
    theme_rows = (
        _build_metadata_theme_rows(analyzed_stocks)
        if metadata_only_themes
        else build_theme_rotation_rows(price_ready_stocks)
    )[: config.top_n]
    price_missing_count = sum(1 for item in analyzed_stocks if not has_price_data(item))
    summary_missing_count = sum(1 for item in analyzed_stocks if not row_value(item, "summary"))
    reference_missing_count = sum(1 for item in analyzed_stocks if not row_value(item, "reference_url"))

    parts = [
        f"# 台股每日題材快報（{config.as_of}）",
        "",
        "## 資料品質提示",
        f"- 已分析股票：{len(analyzed_stocks)} 檔",
        f"- 缺價格資料：{price_missing_count} 檔（報告會以 `{PRICE_MISSING_TEXT}` 標示）",
        f"- 缺 Gemini summary：{summary_missing_count} 檔（報告會以 `{SUMMARY_MISSING_TEXT}` 標示）",
        f"- 缺 reference_url：{reference_missing_count} 檔（報告會以 `{URL_MISSING_TEXT}` 標示）",
    ]

    parts.extend(["", "## 最強題材 Top N"])
    if metadata_only_themes:
        parts.append("- ⚠️ 本次沒有可用價格資料；以下先依股池題材檔數與摘要完整度排序，技術訊號待補價格後更新。")
    if not theme_rows:
        parts.append("- 尚無可聚合的題材資料；請確認價格資料或股池來源是否可用。")
    else:
        for index, theme in enumerate(theme_rows, start=1):
            parts.extend([
                "",
                f"### {index}. {theme.group_label} / {theme.subgroup_label}",
                f"- 熱度分數：{theme.heat_score:.1f}",
                f"- 股票數：{theme.stock_count}；偏多 {theme.bull_count}、觀察 {theme.observe_count}、警示 {theme.warn_count}、轉弱 {theme.bear_count}、中性 {theme.neutral_count}",
                f"- 平均漲跌：{theme.avg_change_pct:+.2f}%；平均訊號分數：{theme.avg_signal_score:.1f}",
                "",
                _theme_stock_sections(
                    theme,
                    analyzed_stocks,
                    limit=config.theme_stock_limit,
                    metadata_only=metadata_only_themes,
                ),
            ])

    breakout = _sort_by_signal_then_change([item for item in analyzed_stocks if signal_code(item) in BREAKOUT_CODES])
    overheated = _sort_by_signal_then_change([item for item in analyzed_stocks if signal_code(item) in OVERHEAT_CODES], reverse=False)
    ma20_break = _sort_by_signal_then_change([item for item in analyzed_stocks if signal_code(item) in MA20_BREAK_CODES], reverse=False)

    no_price_empty_text = "價格資料不足，無法偵測技術訊號；請先更新 prebuilt_cache 或加上 --allow-live-fetch。"
    parts.extend([
        "",
        _render_stock_collection(
            "新突破股",
            breakout,
            empty_text=no_price_empty_text if metadata_only_themes else "今日沒有偵測到 20 日新高突破股。",
            limit=config.highlight_limit,
        ),
        "",
        _render_stock_collection(
            "過熱股",
            overheated,
            empty_text=no_price_empty_text if metadata_only_themes else "今日沒有偵測到過熱股。",
            limit=config.highlight_limit,
        ),
        "",
        _render_stock_collection(
            "跌破 MA20 股",
            ma20_break,
            empty_text=no_price_empty_text if metadata_only_themes else "今日沒有偵測到跌破 MA20 股。",
            limit=config.highlight_limit,
        ),
        "",
    ])
    return "\n".join(parts)


def load_report_stock_pool(
    *,
    gemini_path: Path = GEMINI_AGENT_GROUP_FILE,
    llm_path: Path = LLM_GROUP_FILE,
    watchlist_path: Path = WATCHLIST_FILE,
) -> pd.DataFrame:
    frames = [
        load_gemini_agent_group_map(gemini_path),
        load_llm_group_map(llm_path, LLM_GROUP_SHEET),
        load_watchlist(watchlist_path),
    ]
    non_empty = [df for df in frames if not df.empty]
    if not non_empty:
        return pd.DataFrame(columns=["symbol", "name", "group", "subgroup", "summary", "reference_url"])
    stocks = pd.concat(non_empty, ignore_index=True)
    for col in ["symbol", "name", "group", "subgroup", "summary", "reference_url"]:
        if col not in stocks.columns:
            stocks[col] = ""
        stocks[col] = stocks[col].fillna("").astype(str).str.strip()
    return stocks[stocks["symbol"] != ""].drop_duplicates(subset=["symbol"], keep="first").copy()


def _merge_fallback_price_data(
    stocks: pd.DataFrame,
    price_data_map: dict[str, pd.DataFrame],
    *,
    fetch_interval: str,
    fallback_fetch_periods: Sequence[str],
    loader: Callable,
) -> dict[str, pd.DataFrame]:
    """Fill missing report prices from older prebuilt cache periods without live fetch.

    The report normally uses 6mo/1d prices, but deployed or manually copied
    cache directories can contain only a broader period such as 2y/1d.  Falling
    back to those local disk caches keeps the report useful while preserving the
    no-network default.
    """
    price_data_map = dict(price_data_map or {})
    missing_symbols = [
        symbol
        for symbol in stocks["symbol"].dropna().astype(str).tolist()
        if price_data_map.get(symbol, pd.DataFrame()).empty
    ]
    for fallback_period in fallback_fetch_periods:
        if not missing_symbols:
            break
        fallback_stocks = stocks[stocks["symbol"].isin(missing_symbols)].copy()
        fallback_map = loader(
            fallback_stocks,
            fallback_period,
            fetch_interval,
            allow_live_fetch=False,
            allow_stale_disk=True,
            max_live_symbols=0,
        )
        for symbol in missing_symbols[:]:
            fallback_df = fallback_map.get(symbol, pd.DataFrame())
            if isinstance(fallback_df, pd.DataFrame) and not fallback_df.empty:
                price_data_map[symbol] = fallback_df
                missing_symbols.remove(symbol)
    return price_data_map


def analyze_stock_pool_for_report(
    stocks: pd.DataFrame,
    *,
    fetch_period: str = "6mo",
    fetch_interval: str = "1d",
    display_period: str = "3mo",
    allow_live_fetch: bool = False,
    price_data_loader: Callable | None = None,
    fallback_fetch_periods: Sequence[str] = ("2y",),
) -> list[dict]:
    if stocks.empty:
        return []
    loader = price_data_loader or prefetch_price_data
    price_data_map = loader(
        stocks,
        fetch_period,
        fetch_interval,
        allow_live_fetch=allow_live_fetch,
        allow_stale_disk=True,
        max_live_symbols=len(stocks) if allow_live_fetch else 0,
    )
    fallback_fetch_periods = tuple(period for period in fallback_fetch_periods if period != fetch_period)
    if fallback_fetch_periods:
        price_data_map = _merge_fallback_price_data(
            stocks,
            price_data_map,
            fetch_interval=fetch_interval,
            fallback_fetch_periods=fallback_fetch_periods,
            loader=loader,
        )
    analyzed = []
    for row in stocks.itertuples(index=False):
        analysis = build_stock_analysis(
            row.symbol,
            "daily",
            fetch_period,
            fetch_interval,
            display_period,
            price_data_map.get(row.symbol, pd.DataFrame()),
            pd.DataFrame(),
            False,
        )
        analyzed.append({
            "row": row,
            "df": analysis["df"],
            "signal": analysis["signal"],
            "status": analysis["status"],
            "bucket": analysis["bucket"],
            "close_text": analysis["close_text"],
            "sort_metrics": analysis["sort_metrics"],
            "target_price_text": "-",
            "target_ratio_text": "-",
        })
    return analyzed


def generate_daily_theme_report(
    *,
    output_path: Path | None = None,
    top_n: int = 5,
    stock_limit: int | None = None,
    allow_live_fetch: bool = False,
    as_of: str | None = None,
) -> Path:
    report_as_of = as_of or date.today().isoformat()
    output_path = output_path or dated_daily_theme_report_path(report_as_of)
    stocks = load_report_stock_pool()
    if stock_limit is not None:
        stocks = stocks.head(stock_limit).copy()
    analyzed = analyze_stock_pool_for_report(stocks, allow_live_fetch=allow_live_fetch)
    markdown = render_daily_theme_report(
        analyzed,
        config=DailyReportConfig(as_of=report_as_of, top_n=top_n),
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown, encoding="utf-8")
    return output_path


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="產生台股每日題材 Markdown 快報。")
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Markdown 日報輸出路徑；未指定時輸出 reports/daily_theme_report_YYYY-MM-DD.md 以保留歷史。",
    )
    parser.add_argument("--top-n", type=int, default=5, help="最強題材列出數量。")
    parser.add_argument("--stock-limit", type=int, default=None, help="限制分析股票數，方便本機快速試跑。")
    parser.add_argument("--allow-live-fetch", action="store_true", help="允許缺少本機快取時即時抓價；預設只使用可用快取並清楚標示缺資料。")
    parser.add_argument("--as-of", default=None, help="指定日報日期文字，預設使用今天。")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_arg_parser().parse_args(argv)
    output = generate_daily_theme_report(
        output_path=args.output,
        top_n=max(args.top_n, 1),
        stock_limit=args.stock_limit,
        allow_live_fetch=args.allow_live_fetch,
        as_of=args.as_of,
    )
    print(f"wrote daily theme report to {output}")


__all__ = [
    "BREAKOUT_CODES",
    "DailyReportConfig",
    "dated_daily_theme_report_path",
    "MA20_BREAK_CODES",
    "OVERHEAT_CODES",
    "PRICE_MISSING_TEXT",
    "SUMMARY_MISSING_TEXT",
    "URL_MISSING_TEXT",
    "_merge_fallback_price_data",
    "analyze_stock_pool_for_report",
    "generate_daily_theme_report",
    "load_report_stock_pool",
    "render_daily_theme_report",
    "short_summary",
    "stock_reference_text",
]
