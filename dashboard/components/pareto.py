"""Plotly Pareto chart component for SCOR-Py failure analysis."""

import pandas as pd
import plotly.graph_objects as go


def create_pareto_chart(
    pareto_df: pd.DataFrame,
    title: str = "Analisis Pareto Mode Kegagalan Pesanan (Aturan 80/20)",
) -> go.Figure:
    """Create a Plotly dual-axis Pareto chart (bar count + cumulative percentage line).

    Parameters
    ----------
    pareto_df : pd.DataFrame
        DataFrame from `scorpy.root_cause.pareto_failure_analysis()`.
    title : str

    Returns
    -------
    go.Figure
    """
    if len(pareto_df) == 0:
        fig = go.Figure()
        fig.update_layout(title="Tidak ada data kegagalan.")
        return fig

    fig = go.Figure()

    # Bar chart for counts
    colors = ["#ef4444" if vital else "#94a3b8" for vital in pareto_df["is_vital_few"]]

    fig.add_trace(
        go.Bar(
            x=pareto_df["failure_mode"],
            y=pareto_df["failure_count"],
            name="Jumlah Kasus",
            marker_color=colors,
            yaxis="y",
            text=pareto_df["failure_count"],
            textposition="auto",
        )
    )

    # Line chart for cumulative percentage
    fig.add_trace(
        go.Scatter(
            x=pareto_df["failure_mode"],
            y=pareto_df["cumulative_pct"],
            name="Kumulatif (%)",
            mode="lines+markers",
            line=dict(color="#2563eb", width=3),
            marker=dict(size=8, color="#1e40af"),
            yaxis="y2",
        )
    )

    # 80% threshold line
    fig.add_hline(
        y=80,
        line_dash="dot",
        line_color="#dc2626",
        annotation_text="Ambang Batas 80% (Vital Few)",
        annotation_position="bottom right",
        yref="y2",
    )

    fig.update_layout(
        title={"text": f"<b>{title}</b>", "font": {"size": 16, "color": "#1e293b"}},
        xaxis=dict(title="Mode Kegagalan / Defek", tickangle=-25),
        yaxis=dict(title="Jumlah Frekuensi Kegagalan"),
        yaxis2=dict(
            title="Persentase Kumulatif (%)",
            overlaying="y",
            side="right",
            range=[0, 105],
            showgrid=False,
        ),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        plot_bgcolor="#f8fafc",
        paper_bgcolor="rgba(0,0,0,0)",
        height=450,
        margin=dict(l=40, r=40, t=60, b=100),
    )

    return fig
