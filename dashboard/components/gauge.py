"""Plotly Gauge indicator component for SCOR metrics."""

from typing import Optional

import plotly.graph_objects as go


def create_gauge_chart(
    value: float,
    title: str,
    target: Optional[float] = None,
    max_val: float = 100.0,
    is_percentage: bool = True,
    threshold_green: float = 85.0,
    threshold_yellow: float = 70.0,
) -> go.Figure:
    """Create an interactive Plotly gauge chart for SCOR KPI tracking.

    Parameters
    ----------
    value : float
        Current metric value (in % or days/currency).
    title : str
        KPI title (e.g. "Perfect Order Fulfillment (RL.1.1)").
    target : Optional[float]
        Benchmark or historical target line.
    max_val : float, default 100.0
        Maximum axis value.
    is_percentage : bool, default True
        If True, formats suffix as '%'.
    threshold_green : float, default 85.0
        Lower bound for healthy (green) range.
    threshold_yellow : float, default 70.0
        Lower bound for caution (yellow) range.

    Returns
    -------
    go.Figure
    """
    suffix = "%" if is_percentage else ""
    val_disp = value * 100.0 if (is_percentage and value <= 1.0) else value
    target_disp = (
        (target * 100.0 if (is_percentage and target is not None and target <= 1.0) else target)
        if target
        else None
    )

    delta_config = {}
    if target_disp is not None:
        delta_config = {
            "reference": target_disp,
            "increasing": {"color": "#10b981"},
            "decreasing": {"color": "#ef4444"},
        }

    fig = go.Figure(
        go.Indicator(
            mode="gauge+number" + ("+delta" if target_disp is not None else ""),
            value=val_disp,
            number={
                "suffix": suffix,
                "valueformat": ".1f",
                "font": {"size": 28, "color": "#1e293b"},
            },
            delta=delta_config,
            title={"text": f"<b>{title}</b>", "font": {"size": 16, "color": "#334155"}},
            gauge={
                "axis": {"range": [0, max_val], "tickwidth": 1, "tickcolor": "#94a3b8"},
                "bar": {"color": "#3b82f6", "thickness": 0.28},
                "bgcolor": "white",
                "borderwidth": 1,
                "bordercolor": "#e2e8f0",
                "steps": [
                    {"range": [0, threshold_yellow], "color": "#fee2e2"},
                    {"range": [threshold_yellow, threshold_green], "color": "#fef3c7"},
                    {"range": [threshold_green, max_val], "color": "#dcfce7"},
                ],
                "threshold": (
                    {
                        "line": {"color": "#dc2626", "width": 3},
                        "thickness": 0.75,
                        "value": target_disp,
                    }
                    if target_disp is not None
                    else None
                ),
            },
        )
    )

    fig.update_layout(
        height=220,
        margin=dict(l=20, r=20, t=40, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        font={"family": "sans-serif"},
    )
    return fig
