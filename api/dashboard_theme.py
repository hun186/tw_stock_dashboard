"""HTML helpers for dashboard theme metadata."""

from __future__ import annotations

import html


def theme_summary_text(value: object) -> str:
    text = str(value or "").strip()
    return text if text else "-"


def theme_reference_html(value: object) -> str:
    url = str(value or "").strip()
    if not url:
        return "-"
    escaped = html.escape(url, quote=True)
    label = "來源連結" if url.lower().startswith(("http://", "https://")) else url
    if url.lower().startswith(("http://", "https://")):
        return f"<a class='source-link' href='{escaped}' target='_blank' rel='noopener noreferrer'>{html.escape(label)}</a>"
    return html.escape(label)


def theme_compact_html(group_value: object, subgroup_value: object) -> str:
    group = str(group_value or "").strip()
    subgroup = str(subgroup_value or "").strip()
    group_label = group or "-"
    subgroup_label = subgroup or "-"
    title_parts = []
    if group:
        title_parts.append(f"主題分類：{group}")
    if subgroup:
        title_parts.append(f"次題材：{subgroup}")
    title = "；".join(title_parts) or "尚無題材分類"
    return (
        f"<div class='theme-compact' title='{html.escape(title, quote=True)}'>"
        f"<span class='theme-chip theme-chip-main'>{html.escape(group_label)}</span>"
        f"<span class='theme-chip theme-chip-sub'>{html.escape(subgroup_label)}</span>"
        "</div>"
    )
