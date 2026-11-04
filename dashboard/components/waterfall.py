"""Plotly Waterfall chart components for SCOR Cash-to-Cash and SCM Cost breakdown."""

from typing import Dict

import plotly.graph_objects as go


def create_c2c_waterfall(
    ids: float,
    dso: float,
    dpo: float,
    title: str = "Dekomposisi Cash-to-Cash Cycle Time (AM.1.1)",
) -> go.Figure:
    """Create a waterfall chart showing C2C = IDS + DSO - DPO.

    Parameters
    ----------
    ids : float
        Inventory Days of Supply (days).
    dso : float
        Days Sales Outstanding (days).
    dpo : float
        Days Payable Outstanding (days).
    title : str

    Returns
    -------
    go.Figure
    """
    c2c = ids + dso - dpo

    fig = go.Figure(
        go.Waterfall(
            name="C2C Breakdown",
            orientation="v",
            measure=["relative", "relative", "relative", "total"],
            x=[
                "IDS<br>(Persediaan)",
                "DSO<br>(Piutang)",
                "DPO<br>(Utang Pemasok)",
                "C2C Net<br>Cycle Time",
            ],
            textposition="outside",
            text=[f"+{ids:.1f} d", f"+{dso:.1f} d", f"-{dpo:.1f} d", f"<b>{c2c:.1f} d</b>"],
            y=[ids, dso, -dpo, c2c],
            connector={"line": {"color": "#94a3b8", "dash": "dot"}},
            decreasing={"marker": {"color": "#10b981"}},  # DPO helps reduce C2C
            increasing={"marker": {"color": "#f59e0b"}},  # IDS & DSO increase cash tied up
            totals={"marker": {"color": "#2563eb"}},
        )
    )

    fig.update_layout(
        title={"text": f"<b>{title}</b>", "font": {"size": 16, "color": "#1e293b"}},
        yaxis_title="Hari (Days)",
        plot_bgcolor="#f8fafc",
        paper_bgcolor="rgba(0,0,0,0)",
        height=380,
        margin=dict(l=40, r=40, t=60, b=40),
    )
    return fig


def create_cost_waterfall(
    breakdown: Dict[str, Dict[str, float]],
    title: str = "Dekomposisi Biaya Manajemen Rantai Pasok (CO.1.1)",
    currency: str = "IDR",
) -> go.Figure:
    """Create a waterfall chart showing SCM cost breakdown.

    Parameters
    ----------
    breakdown : dict
        Dict formatted like `CostMetrics.cost_breakdown()`.
    title : str
    currency : str

    Returns
    -------
    go.Figure
    """
    labels = []
    values = []
    texts = []
    measures = []

    for name, data in breakdown.items():
        labels.append(name.capitalize())
        amount = data["amount"]
        values.append(amount)
        # Format in Millions or Billions IDR
        if amount >= 1_000_000_000:
            texts.append(f"{amount / 1e9:.2f} M")
        elif amount >= 1_000_000:
            texts.append(f"{amount / 1e6:.1f} Jt")
        else:
            texts.append(f"{amount:,.0f}")
        measures.append("relative")

    labels.append("Total SCM Cost")
    measures.append("total")
    total_val = sum(values)
    values.append(total_val)
    if total_val >= 1_000_000_000:
        texts.append(f"<b>{total_val / 1e9:.2f} M</b>")
    else:
        texts.append(f"<b>{total_val / 1e6:.1f} Jt</b>")

    fig = go.Figure(
        go.Waterfall(
            name="SCM Cost",
            orientation="v",
            measure=measures,
            x=labels,
            textposition="outside",
            text=texts,
            y=values,
            connector={"line": {"color": "#94a3b8"}},
            increasing={"marker": {"color": "#3b82f6"}},
            totals={"marker": {"color": "#1e40af"}},
        )
    )

    fig.update_layout(
        title={"text": f"<b>{title}</b>", "font": {"size": 16, "color": "#1e293b"}},
        yaxis_title=f"Nilai ({currency})",
        plot_bgcolor="#f8fafc",
        paper_bgcolor="rgba(0,0,0,0)",
        height=380,
        margin=dict(l=40, r=40, t=60, b=40),
    )
    return fig
