from __future__ import annotations

import html
import json


def progress_percent(done: int, total: int) -> int:
    if total <= 0:
        return 100
    return min(100, max(0, round((done / total) * 100)))


def build_progress_steps(
    *,
    analyzed_count: int,
    candidate_count: int,
    is_limited_analysis: bool,
    price_ready_count: int,
    progress_total_stocks: int,
    rendered_count: int,
    signal_ready_count: int,
    sorted_count: int,
    visible_stock_count: int,
) -> list[dict]:
    steps = [
        {
            "label": "股池與篩選",
            "done": int(candidate_count if not is_limited_analysis else visible_stock_count),
            "total": int(candidate_count),
            "detail": "已套用頁籤、產業、主題與個人標籤篩選",
        },
        {
            "label": "行情資料",
            "done": int(price_ready_count),
            "total": int(progress_total_stocks),
            "detail": "已讀取可用快取或下載結果",
        },
        {
            "label": "形勢資料",
            "done": int(signal_ready_count),
            "total": int(progress_total_stocks),
            "detail": "盤中模式會另外讀取日線判斷資料",
        },
        {
            "label": "技術分析",
            "done": int(analyzed_count),
            "total": int(progress_total_stocks),
            "detail": "已計算均線、量能、形勢分數與排序指標",
        },
        {
            "label": "頁面呈現",
            "done": int(rendered_count),
            "total": int(sorted_count),
            "detail": "已產生目前表格資料與可用圖卡 HTML",
        },
    ]
    for step in steps:
        step["percent"] = progress_percent(step["done"], step["total"])
    return steps


def render_progress_steps_html(progress_steps: list[dict]) -> str:
    return "".join([
        f"<li><span class='progress-stage-name'>{html.escape(step['label'])}</span>"
        f"<span class='progress-stage-ratio'>{step['done']} / {step['total']}（{step['percent']}%）</span>"
        f"<div class='progress-bar' aria-hidden='true'><span style='width:{step['percent']}%'></span></div>"
        f"<small>{html.escape(step['detail'])}</small></li>"
        for step in progress_steps
    ])


def progress_steps_json(progress_steps: list[dict]) -> str:
    return json.dumps(progress_steps, ensure_ascii=False).replace("</", "<\\/")
