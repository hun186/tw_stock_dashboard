from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from api.constants import DOWN_COLOR, MA5_COLOR, MA20_COLOR, MA60_COLOR, UP_COLOR


def _daily_date_rangebreaks(dates: pd.Series) -> list[dict[str, list[str]]]:
    parsed_dates = pd.to_datetime(dates, errors="coerce").dropna()
    if parsed_dates.empty:
        return []

    normalized_dates = parsed_dates.dt.normalize()
    if not (parsed_dates == normalized_dates).all():
        return []

    trading_days = pd.Index(normalized_dates.unique()).sort_values()
    calendar_days = pd.date_range(trading_days.min(), trading_days.max(), freq="D")
    missing_days = calendar_days.difference(trading_days)
    if missing_days.empty:
        return []

    return [{"values": [day.strftime("%Y-%m-%d") for day in missing_days]}]


def _volume_in_lots(series: pd.Series) -> pd.Series:
    return series / 1000


def make_chart_html(
    df: pd.DataFrame,
    title: str,
    show_volume: bool,
    show_ma: bool,
    intraday_ref_close: float | None = None,
    show_price: bool = True,
) -> str:
    if not show_price and not show_volume:
        return ""

    has_price_panel = show_price
    has_volume_panel = show_volume
    row_count = int(has_price_panel) + int(has_volume_panel)
    price_row = 1 if has_price_panel else None
    volume_row = row_count if has_volume_panel else None
    row_heights = [0.7, 0.3] if has_price_panel and has_volume_panel else [1.0]
    fig = make_subplots(rows=row_count, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=row_heights)

    if price_row is not None:
        price_open = df["Open"] if intraday_ref_close is None else np.full(len(df), intraday_ref_close)
        fig.add_trace(go.Candlestick(
            x=df["Date"], open=price_open, high=df["High"], low=df["Low"], close=df["Close"], name="價格K線",
            increasing_line_color=UP_COLOR, decreasing_line_color=DOWN_COLOR,
            increasing_fillcolor=UP_COLOR, decreasing_fillcolor=DOWN_COLOR,
            increasing=dict(line=dict(color=UP_COLOR), fillcolor=UP_COLOR),
            decreasing=dict(line=dict(color=DOWN_COLOR), fillcolor=DOWN_COLOR),
        ), row=price_row, col=1)
        if show_ma:
            fig.add_trace(go.Scatter(x=df["Date"], y=df["MA5"], mode="lines", name="MA5", line=dict(color=MA5_COLOR)), row=price_row, col=1)
            fig.add_trace(go.Scatter(x=df["Date"], y=df["MA20"], mode="lines", name="MA20", line=dict(color=MA20_COLOR)), row=price_row, col=1)
            fig.add_trace(go.Scatter(x=df["Date"], y=df["MA60"], mode="lines", name="MA60", line=dict(color=MA60_COLOR)), row=price_row, col=1)
        fig.update_yaxes(title_text="價格", row=price_row, col=1)

    if volume_row is not None:
        ref_series = df["RefClose"] if "RefClose" in df.columns else df["Open"]
        volume_colors = np.where(df["Close"] >= ref_series, UP_COLOR, DOWN_COLOR)
        volume_lots = _volume_in_lots(df["Volume"])
        fig.add_trace(
            go.Bar(
                x=df["Date"],
                y=volume_lots,
                name="量K線（張）",
                marker_color=volume_colors,
                opacity=0.8,
                hovertemplate="%{x}<br>成交量：%{y:,.0f} 張<extra></extra>",
            ),
            row=volume_row,
            col=1,
        )
        if show_ma:
            fig.add_trace(
                go.Scatter(
                    x=df["Date"],
                    y=_volume_in_lots(df["VMA5"]),
                    mode="lines",
                    name="VMA5（張）",
                    line=dict(color=MA5_COLOR),
                    hovertemplate="%{x}<br>VMA5：%{y:,.0f} 張<extra></extra>",
                ),
                row=volume_row,
                col=1,
            )
            fig.add_trace(
                go.Scatter(
                    x=df["Date"],
                    y=_volume_in_lots(df["VMA20"]),
                    mode="lines",
                    name="VMA20（張）",
                    line=dict(color=MA20_COLOR),
                    hovertemplate="%{x}<br>VMA20：%{y:,.0f} 張<extra></extra>",
                ),
                row=volume_row,
                col=1,
            )
            fig.add_trace(
                go.Scatter(
                    x=df["Date"],
                    y=_volume_in_lots(df["VMA60"]),
                    mode="lines",
                    name="VMA60（張）",
                    line=dict(color=MA60_COLOR),
                    hovertemplate="%{x}<br>VMA60：%{y:,.0f} 張<extra></extra>",
                ),
                row=volume_row,
                col=1,
            )
        fig.update_yaxes(title_text="成交量（張）", row=volume_row, col=1)

    daily_rangebreaks = _daily_date_rangebreaks(df["Date"]) if intraday_ref_close is None else []
    if daily_rangebreaks:
        fig.update_xaxes(rangebreaks=daily_rangebreaks)

    if intraday_ref_close is not None:
        ref_close = float(intraday_ref_close)
        limit_up = ref_close * 1.1
        limit_down = ref_close * 0.9
        session_date = pd.to_datetime(df["Date"]).max().normalize()
        session_start = session_date + pd.Timedelta(hours=9)
        session_end = session_date + pd.Timedelta(hours=13, minutes=30)
        if price_row is not None:
            fig.update_xaxes(range=[session_start, session_end], row=price_row, col=1)
            fig.update_yaxes(range=[limit_down, limit_up], row=price_row, col=1)
            step = ref_close * 0.02
            inner_down_ticks = [ref_close - step * i for i in range(1, 6)]
            inner_up_ticks = [ref_close + step * i for i in range(1, 6)]
            tickvals = [limit_down] + list(reversed(inner_down_ticks)) + [ref_close] + inner_up_ticks + [limit_up]
            ticktext = [f"{limit_down:.2f}"] + [f"{v:.2f}" for v in reversed(inner_down_ticks)] + [f"{ref_close:.2f}"] + [f"{v:.2f}" for v in inner_up_ticks] + [f"{limit_up:.2f}"]
            fig.update_yaxes(
                tickmode="array",
                tickvals=tickvals,
                ticktext=ticktext,
                row=price_row,
                col=1,
            )
            fig.add_hline(y=ref_close, line_color="#666", line_width=1, line_dash="dot", row=price_row, col=1)
        if volume_row is not None:
            fig.update_xaxes(range=[session_start, session_end], row=volume_row, col=1)

    height = 500 if has_price_panel and has_volume_panel else 320
    fig.update_layout(title=title, height=height, margin=dict(l=4, r=4, t=36, b=4), xaxis_rangeslider_visible=False)
    return fig.to_html(full_html=False, include_plotlyjs="cdn")
