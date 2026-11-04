"""Plotly Sankey diagram component for supply chain failure root-cause analysis."""

import pandas as pd
import plotly.graph_objects as go


def create_delivery_sankey(
    df_orders: pd.DataFrame,
    segment_col: str = "customer_segment",
    delay_col: str = "delay_reason",
    pof_flag_col: str = "_is_pof",
    title: str = "Aliran Akar Masalah Keterlambatan & Kegagalan Pengiriman",
) -> go.Figure:
    """Generate a 3-tier Sankey diagram:
    Segment -> Root Cause (Delay Reason) -> Outcome (Perfect Order vs Failed).

    Parameters
    ----------
    df_orders : pd.DataFrame
        Detailed orders DataFrame containing segmentation, delay reasons, and POF flags.
    segment_col : str
    delay_col : str
    pof_flag_col : str
    title : str

    Returns
    -------
    go.Figure
    """
    df = df_orders.copy()
    if pof_flag_col not in df.columns:
        df[pof_flag_col] = (
            (
                pd.to_datetime(df["actual_delivery_date"])
                <= pd.to_datetime(df["promised_delivery_date"])
            )
            & (df["qty_delivered"] >= df["qty_ordered"])
            & (~df["is_damaged"])
            & (df["is_doc_complete"])
        )

    df["outcome"] = df[pof_flag_col].apply(
        lambda x: "Pesanan Sempurna (POF)" if x else "Pesanan Bermasalah (Gagal POF)"
    )
    if delay_col not in df.columns:
        df[delay_col] = "Normal"

    # Distinct nodes
    segments = sorted(list(df[segment_col].dropna().unique()))
    reasons = sorted(list(df[delay_col].dropna().unique()))
    outcomes = sorted(list(df["outcome"].unique()))

    all_nodes = segments + reasons + outcomes
    node_map = {name: idx for idx, name in enumerate(all_nodes)}

    # Link 1: Segment -> Reason
    link1 = df.groupby([segment_col, delay_col]).size().reset_index(name="count")
    # Link 2: Reason -> Outcome
    link2 = df.groupby([delay_col, "outcome"]).size().reset_index(name="count")

    sources = []
    targets = []
    values = []

    for _, row in link1.iterrows():
        sources.append(node_map[row[segment_col]])
        targets.append(node_map[row[delay_col]])
        values.append(int(row["count"]))

    for _, row in link2.iterrows():
        sources.append(node_map[row[delay_col]])
        targets.append(node_map[row["outcome"]])
        values.append(int(row["count"]))

    # Node colors
    node_colors = []
    for node in all_nodes:
        if node in segments:
            node_colors.append("#3b82f6")  # Blue
        elif node == "None" or node == "Normal":
            node_colors.append("#10b981")  # Green
        elif "Pesanan Sempurna" in node:
            node_colors.append("#059669")  # Dark Green
        elif "Gagal" in node:
            node_colors.append("#ef4444")  # Red
        else:
            node_colors.append("#f59e0b")  # Amber for delay causes

    fig = go.Figure(
        data=[
            go.Sankey(
                node=dict(
                    pad=18,
                    thickness=20,
                    line=dict(color="#64748b", width=0.5),
                    label=all_nodes,
                    color=node_colors,
                ),
                link=dict(
                    source=sources,
                    target=targets,
                    value=values,
                    color="rgba(148, 163, 184, 0.35)",
                ),
            )
        ]
    )

    fig.update_layout(
        title={"text": f"<b>{title}</b>", "font": {"size": 16, "color": "#1e293b"}},
        font=dict(size=11, family="sans-serif"),
        plot_bgcolor="#f8fafc",
        paper_bgcolor="rgba(0,0,0,0)",
        height=450,
        margin=dict(l=20, r=20, t=50, b=30),
    )
    return fig
