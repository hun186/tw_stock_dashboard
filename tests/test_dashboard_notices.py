from __future__ import annotations

from api.dashboard_notices import render_data_quality_notice


def test_render_data_quality_notice_includes_warning_items() -> None:
    html = render_data_quality_notice(warnings=["偵測到代號 6990.TWO 出現多個名稱"])
    assert "資料品質警示" in html
    assert "6990.TWO" in html
    assert "人工檢查來源 Excel" in html
