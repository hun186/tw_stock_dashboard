from __future__ import annotations

import html
import json
import math
from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable


BUCKET_COUNT_FIELDS = {
    "bull": "bull_count",
    "observe": "observe_count",
    "warn": "warn_count",
    "bear": "bear_count",
    "neutral": "neutral_count",
}


@dataclass(frozen=True, slots=True)
class ThemeRotationRow:
    group: str
    subgroup: str
    stock_count: int
    bull_count: int
    observe_count: int
    warn_count: int
    bear_count: int
    neutral_count: int
    avg_change_pct: float
    avg_signal_score: float
    heat_score: float

    @property
    def group_label(self) -> str:
        return self.group or "未分類"

    @property
    def subgroup_label(self) -> str:
        return self.subgroup or "未分類"


def _clean_text(value: object) -> str:
    return str(value or "").strip()


def _safe_float(value: object, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default


def _bucket_field(bucket: object) -> str:
    return BUCKET_COUNT_FIELDS.get(_clean_text(bucket), "neutral_count")


def _theme_heat_score(
    *,
    stock_count: int,
    bull_count: int,
    observe_count: int,
    warn_count: int,
    bear_count: int,
    avg_change_pct: float,
    avg_signal_score: float,
) -> float:
    if stock_count <= 0:
        return 0.0
    bull_ratio = bull_count / stock_count
    observe_ratio = observe_count / stock_count
    warn_ratio = warn_count / stock_count
    bear_ratio = bear_count / stock_count
    breadth_bonus = min(math.log1p(stock_count) * 4.0, 12.0)
    score = (
        avg_signal_score
        + avg_change_pct * 3.0
        + bull_ratio * 45.0
        + observe_ratio * 12.0
        + breadth_bonus
        - warn_ratio * 28.0
        - bear_ratio * 40.0
    )
    return round(score, 1)


def build_theme_rotation_rows(analyzed_stocks: Iterable[dict]) -> list[ThemeRotationRow]:
    """Aggregate analyzed stock signals into group/subgroup theme rotation rows.

    The function intentionally tolerates empty input, missing row metadata and
    absent sort metrics so broad category requests and legacy watchlists can
    still render the dashboard safely.
    """
    groups: dict[tuple[str, str], dict] = defaultdict(
        lambda: {
            "stock_count": 0,
            "bull_count": 0,
            "observe_count": 0,
            "warn_count": 0,
            "bear_count": 0,
            "neutral_count": 0,
            "change_total": 0.0,
            "signal_score_total": 0.0,
        }
    )

    for item in analyzed_stocks or []:
        row = item.get("row") if isinstance(item, dict) else None
        group = _clean_text(getattr(row, "group", ""))
        subgroup = _clean_text(getattr(row, "subgroup", ""))
        key = (group, subgroup)
        entry = groups[key]
        entry["stock_count"] += 1
        entry[_bucket_field(item.get("bucket") if isinstance(item, dict) else None)] += 1
        sort_metrics = item.get("sort_metrics", {}) if isinstance(item, dict) else {}
        entry["change_total"] += _safe_float(sort_metrics.get("change_pct") if isinstance(sort_metrics, dict) else None)
        entry["signal_score_total"] += _safe_float(
            sort_metrics.get("signal_score") if isinstance(sort_metrics, dict) else None
        )

    rows = []
    for (group, subgroup), entry in groups.items():
        stock_count = int(entry["stock_count"])
        if stock_count <= 0:
            continue
        avg_change_pct = round(entry["change_total"] / stock_count, 2)
        avg_signal_score = round(entry["signal_score_total"] / stock_count, 1)
        rows.append(
            ThemeRotationRow(
                group=group,
                subgroup=subgroup,
                stock_count=stock_count,
                bull_count=int(entry["bull_count"]),
                observe_count=int(entry["observe_count"]),
                warn_count=int(entry["warn_count"]),
                bear_count=int(entry["bear_count"]),
                neutral_count=int(entry["neutral_count"]),
                avg_change_pct=avg_change_pct,
                avg_signal_score=avg_signal_score,
                heat_score=_theme_heat_score(
                    stock_count=stock_count,
                    bull_count=int(entry["bull_count"]),
                    observe_count=int(entry["observe_count"]),
                    warn_count=int(entry["warn_count"]),
                    bear_count=int(entry["bear_count"]),
                    avg_change_pct=avg_change_pct,
                    avg_signal_score=avg_signal_score,
                ),
            )
        )

    rows.sort(key=lambda row: (row.heat_score, row.stock_count, row.bull_count, row.avg_change_pct), reverse=True)
    return rows


def _format_signed_pct(value: float) -> str:
    return f"{value:+.2f}%"


def render_theme_rotation_radar(rows: Iterable[ThemeRotationRow], *, max_rows: int = 12) -> str:
    visible_rows = list(rows or [])[:max_rows]
    if not visible_rows:
        table_body = "<tr><td colspan='11' class='empty-radar'>尚無符合目前篩選的已分析股票可聚合題材輪動。</td></tr>"
    else:
        table_body = "".join(_render_theme_rotation_row(row) for row in visible_rows)

    return f"""
    <section class='section-card theme-radar-card collapsible-section' data-collapsible-section='themeRadar' aria-labelledby='themeRadarTitle'>
      <div class='section-header'>
        <button type='button' class='section-toggle section-toggle-with-subtitle' data-collapse-target='themeRadarBody' aria-expanded='true' aria-controls='themeRadarBody'>
          <span class='section-toggle-icon' aria-hidden='true'>▾</span>
          <span><span id='themeRadarTitle' class='section-toggle-title'>題材熱度榜</span><span class='section-subtitle'>依主題 / 次題材聚合目前符合篩選的已分析股票形勢判斷、平均漲跌幅與訊號分數。</span></span>
        </button>
      </div>
      <div id='themeRadarBody' class='collapsible-content'>
      <div class='theme-radar-wrap'>
        <table class='theme-radar-table'>
          <thead><tr><th>題材</th><th>檔數</th><th>偏多</th><th>觀察</th><th>警示</th><th>轉弱</th><th>中性</th><th>平均漲跌</th><th>平均訊號</th><th>熱度</th><th>篩選</th></tr></thead>
          <tbody>{table_body}</tbody>
        </table>
      </div>
      </div>
    </section>
    """


def _render_theme_rotation_row(row: ThemeRotationRow) -> str:
    group_json = html.escape(json.dumps(row.group, ensure_ascii=False), quote=True)
    subgroup_json = html.escape(json.dumps(row.subgroup, ensure_ascii=False), quote=True)
    button_disabled = " disabled" if not row.group else ""
    button_title = "套用主題 / 次題材篩選" if row.group else "未分類題材無法套用既有題材篩選"
    return (
        "<tr>"
        f"<td><strong>{html.escape(row.group_label)}</strong><span>{html.escape(row.subgroup_label)}</span></td>"
        f"<td>{row.stock_count}</td>"
        f"<td class='radar-bull'>{row.bull_count}</td>"
        f"<td class='radar-observe'>{row.observe_count}</td>"
        f"<td class='radar-warn'>{row.warn_count}</td>"
        f"<td class='radar-bear'>{row.bear_count}</td>"
        f"<td>{row.neutral_count}</td>"
        f"<td>{_format_signed_pct(row.avg_change_pct)}</td>"
        f"<td>{row.avg_signal_score:.1f}</td>"
        f"<td><span class='heat-score'>{row.heat_score:.1f}</span></td>"
        "<td><button type='button' class='btn-soft radar-filter-btn' "
        f"title='{html.escape(button_title, quote=True)}' onclick='applyThemeRadarFilter({group_json}, {subgroup_json})'{button_disabled}>套用</button></td>"
        "</tr>"
    )


__all__ = ["ThemeRotationRow", "build_theme_rotation_rows", "render_theme_rotation_radar"]
