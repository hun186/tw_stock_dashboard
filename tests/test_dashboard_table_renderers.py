from api.dashboard_table_renderers import render_change_pct_class, render_change_pct_text


def test_render_change_pct_class_uses_market_colors():
    assert render_change_pct_text({"change_pct": 1.23}) == "+1.23%"
    assert render_change_pct_class({"change_pct": 1.23}) == " is-up"
    assert render_change_pct_class({"change_pct": -0.5}) == " is-down"
    assert render_change_pct_class({"change_pct": 0}) == " is-flat"
    assert render_change_pct_class({"change_pct": -999}) == ""
