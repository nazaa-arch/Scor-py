"""Export and reporting utilities for SCOR-Py.

Enables exporting unified SCOR scorecards to JSON, CSV bundles, and formatted Excel workbooks.
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional, Union

import pandas as pd

from scorpy.asset_efficiency import AssetMetrics
from scorpy.cost import CostMetrics
from scorpy.reliability import ReliabilityMetrics
from scorpy.responsiveness import ResponsivenessMetrics


def generate_unified_scorecard(
    df_orders: pd.DataFrame,
    df_financials: Optional[pd.DataFrame] = None,
    df_inventory: Optional[pd.DataFrame] = None,
    grace_days: int = 0,
    in_full_tolerance: float = 0.0,
) -> Dict[str, Any]:
    """Compile all SCOR Level 1 & 2 metrics into a single unified scorecard dictionary."""
    rel = ReliabilityMetrics(
        df_orders,
        on_time_grace_days=grace_days,
        in_full_tolerance=in_full_tolerance,
    )
    resp = ResponsivenessMetrics(df_orders)

    scorecard: Dict[str, Any] = {
        "reliability": rel.evaluate_all(),
        "responsiveness": resp.order_fulfillment_cycle_time(),
        "lead_time_adherence": resp.lead_time_variance(),
    }

    if df_financials is not None:
        cost = CostMetrics.from_dataframe(df_financials)
        scorecard["cost"] = cost.evaluate_all()

        asset = AssetMetrics.from_dataframes(
            df_financials=df_financials,
            df_inventory=df_inventory,
            scm_cost_cols=["transport_cost", "warehousing_cost", "procurement_cost", "return_cost"],
        )
        scorecard["asset_efficiency"] = asset.evaluate_all()

    return scorecard


def export_to_json(scorecard: Dict[str, Any], filepath: Union[str, Path]) -> None:
    """Export scorecard dictionary to a formatted JSON file."""
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(scorecard, f, indent=2, default=str)


def export_to_excel(
    scorecard: Dict[str, Any],
    filepath: Union[str, Path],
    df_by_segment: Optional[pd.DataFrame] = None,
) -> None:
    """Export scorecard into a multi-tab Microsoft Excel workbook (.xlsx)."""
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)

    with pd.ExcelWriter(path, engine="xlsxwriter") as writer:
        # Sheet 1: Executive Summary (Level 1 KPIs)
        exec_summary = []
        rel = scorecard.get("reliability", {})
        resp = scorecard.get("responsiveness", {})
        cost = scorecard.get("cost", {})
        asset = scorecard.get("asset_efficiency", {})

        if rel:
            exec_summary.append(
                {
                    "SCOR Attribute": "Reliability",
                    "Metric Code": "RL.1.1",
                    "Metric Name": "Perfect Order Fulfillment",
                    "Value": f"{rel.get('Perfect_Order_Fulfillment', 0) * 100:.2f}%",
                }
            )
            exec_summary.append(
                {
                    "SCOR Attribute": "Reliability",
                    "Metric Code": "–",
                    "Metric Name": "OTIF Rate",
                    "Value": f"{rel.get('OTIF_rate', 0) * 100:.2f}%",
                }
            )
        if resp:
            exec_summary.append(
                {
                    "SCOR Attribute": "Responsiveness",
                    "Metric Code": "RS.1.1",
                    "Metric Name": "Order Fulfillment Cycle Time (Mean)",
                    "Value": f"{resp.get('mean_days', 0):.1f} days",
                }
            )
        if cost:
            exec_summary.append(
                {
                    "SCOR Attribute": "Costs",
                    "Metric Code": "CO.1.1",
                    "Metric Name": "SCM Cost % of Revenue",
                    "Value": f"{cost.get('scm_cost_pct_revenue', 0):.2f}%",
                }
            )
        if asset:
            exec_summary.append(
                {
                    "SCOR Attribute": "Asset Efficiency",
                    "Metric Code": "AM.1.1",
                    "Metric Name": "Cash-to-Cash Cycle Time",
                    "Value": f"{asset.get('C2C_days', 0):.1f} days",
                }
            )

        df_exec = pd.DataFrame(exec_summary)
        df_exec.to_excel(writer, sheet_name="Executive Summary", index=False)

        # Sheet 2: Reliability
        if rel:
            df_rel = pd.DataFrame(list(rel.items()), columns=["Metric", "Value"])
            df_rel.to_excel(writer, sheet_name="Reliability", index=False)

        # Sheet 3: Segment Breakdown (if provided)
        if df_by_segment is not None:
            df_by_segment.to_excel(writer, sheet_name="By Customer Segment")

        # Sheet 4: Responsiveness
        if resp:
            df_resp = pd.DataFrame(list(resp.items()), columns=["Cycle Time Statistic", "Days"])
            df_resp.to_excel(writer, sheet_name="Responsiveness", index=False)

        # Sheet 5: Asset Efficiency
        if asset:
            df_asset = pd.DataFrame(list(asset.items()), columns=["Asset Metric", "Value"])
            df_asset.to_excel(writer, sheet_name="Asset Efficiency", index=False)

        # Sheet 6: Costs
        if cost and "breakdown" in cost:
            df_cost = (
                pd.DataFrame(cost["breakdown"])
                .T.reset_index()
                .rename(columns={"index": "Cost Component"})
            )
            df_cost.to_excel(writer, sheet_name="SCM Costs", index=False)
