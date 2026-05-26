from __future__ import annotations

import html

from api.market_data import _symbol_key


def render_limited_notice(
    *,
    candidate_count: int,
    is_limited_analysis: bool,
    max_serverless_analysis_stocks: int,
) -> str:
    if not is_limited_analysis:
        return ""
    return (
        f"<div class='notice'>目前候選股共有 {candidate_count} 檔；"
        f"為避免 Vercel Serverless 逾時，本次先分析前 {max_serverless_analysis_stocks} 檔。"
        "可用產業、主題或自訂清單縮小範圍以取得完整排序。</div>"
    )


def render_category_all_coverage_notice(*, tab: str, industry: str, industry_df, source_stocks) -> str:
    if tab != "category" or industry != "all":
        return ""

    official_symbol_keys = set(industry_df["symbol"].map(_symbol_key)) if "symbol" in industry_df.columns else set()
    if not official_symbol_keys:
        return (
            "<div class='notice'>本次未載入交易所／櫃買官方產業表，分類股池目前主要來自 "
            "LLM/Gemini 題材資料與自選清單；這不等於標的停業，請以 K 線是否可下載、"
            "公開資訊觀測站與交易所公告確認交易／營運狀態。</div>"
        )

    source_symbol_keys = source_stocks["symbol"].map(_symbol_key)
    extra_count = int((~source_symbol_keys.isin(official_symbol_keys)).sum())
    if not extra_count:
        return ""
    return (
        "<div class='notice'>分類股池／不限產業已合併官方產業表與 LLM/Gemini 題材資料；"
        f"其中 {extra_count} 檔目前不在本次載入的交易所／櫃買官方產業表。"
        "這不等於停業，常見原因是 Excel 靜態資料、興櫃/ETF/代碼異動、"
        "下市櫃或官方 API 暫時取不到；請以 K 線是否可下載、公開資訊觀測站"
        "與交易所公告確認交易／營運狀態。</div>"
    )


def render_data_quality_notice(*, warnings: list[str]) -> str:
    if not warnings:
        return ""
    items = "".join([f"<li>{html.escape(w)}</li>" for w in warnings])
    return (
        "<div class='notice'><strong>資料品質警示：</strong>偵測到題材清單代號/名稱衝突，"
        "已自動套用防呆規則。請管理者人工檢查來源 Excel：<ul>"
        f"{items}</ul></div>"
    )
