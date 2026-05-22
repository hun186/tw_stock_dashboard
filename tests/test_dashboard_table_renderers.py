from pathlib import Path

from api.dashboard_table_renderers import render_change_pct_class, render_change_pct_text


def test_render_change_pct_class_uses_market_colors():
    assert render_change_pct_text({"change_pct": 1.23}) == "+1.23%"
    assert render_change_pct_class({"change_pct": 1.23}) == " is-up"
    assert render_change_pct_class({"change_pct": -0.5}) == " is-down"
    assert render_change_pct_class({"change_pct": 0}) == " is-flat"
    assert render_change_pct_class({"change_pct": -999}) == ""


def test_dashboard_css_defines_change_pct_market_colors():
    css = Path("api/static/dashboard.css").read_text(encoding="utf-8")
    assert "--up:#dc2626" in css
    assert "--down:#16a34a" in css
    assert "--flat:#111827" in css
    assert ".change-pct-cell.is-up{color:var(--up)}" in css
    assert ".change-pct-cell.is-down{color:var(--down)}" in css
    assert ".change-pct-cell.is-flat{color:var(--flat)}" in css
