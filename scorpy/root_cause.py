"""Root-cause diagnosis and Pareto analysis module for SCOR-Py.

Identifies failure modes preventing Perfect Order Fulfillment (POF) and classifies
vital few root causes (80/20 rule).
"""

from typing import Dict, Any, Optional
import pandas as pd
import numpy as np


def pareto_failure_analysis(
    df_orders: pd.DataFrame,
    promised_date_col: str = "promised_delivery_date",
    actual_date_col: str = "actual_delivery_date",
    ordered_qty_col: str = "qty_ordered",
    delivered_qty_col: str = "qty_delivered",
    damaged_flag_col: str = "is_damaged",
    doc_accurate_col: str = "is_doc_complete",
    delay_reason_col: Optional[str] = "delay_reason",
    on_time_grace_days: int = 0,
    in_full_tolerance: float = 0.0,
) -> pd.DataFrame:
    """Perform a Pareto (80/20) failure analysis across all imperfect orders.

    Breaks down each imperfect order into its constituent failure categories:
    - Delivery Delay (with delay reason attribution if available)
    - Under-shipment (Quantity short)
    - Product Damage
    - Incomplete / Inaccurate Documentation

    Returns
    -------
    pd.DataFrame
        Ranked failure modes with counts, percentages, cumulative percentages,
        and vital_few classification.
    """
    df = df_orders.copy()
    df[promised_date_col] = pd.to_datetime(df[promised_date_col])
    df[actual_date_col] = pd.to_datetime(df[actual_date_col])

    # Only evaluate orders with actual delivery
    shipped = df[df[actual_date_col].notna()].copy()
    if len(shipped) == 0:
        return pd.DataFrame(
            columns=[
                "failure_mode",
                "failure_count",
                "failure_pct",
                "cumulative_pct",
                "is_vital_few",
            ]
        )

    # Boolean flags
    grace_delta = pd.to_timedelta(on_time_grace_days, unit="D")
    is_late = shipped[actual_date_col] > (shipped[promised_date_col] + grace_delta)

    threshold = shipped[ordered_qty_col] * (1.0 - in_full_tolerance)
    is_short = shipped[delivered_qty_col] < (threshold - 1e-9)

    is_damaged = shipped[damaged_flag_col].astype(bool)
    is_doc_err = ~shipped[doc_accurate_col].astype(bool)

    # Collect failure occurrences
    failure_records = []

    for idx, row in shipped.iterrows():
        # Check if imperfect
        late = is_late.loc[idx]
        short = is_short.loc[idx]
        damaged = is_damaged.loc[idx]
        doc_err = is_doc_err.loc[idx]

        if late:
            reason = (
                row.get(delay_reason_col, "Delay (Unspecified)")
                if delay_reason_col
                else "Delay (Unspecified)"
            )
            mode_name = f"Late: {reason}" if reason and reason != "None" else "Late: Delivery Delay"
            failure_records.append(mode_name)

        if short:
            failure_records.append("Quantity: Under-shipment / Partial Delivery")

        if damaged:
            failure_records.append("Quality: In-transit Damage")

        if doc_err:
            failure_records.append("Compliance: Documentation Incomplete/Inaccurate")

    if not failure_records:
        return pd.DataFrame(
            [
                {
                    "failure_mode": "Zero Defects (100% Perfect)",
                    "failure_count": 0,
                    "failure_pct": 0.0,
                    "cumulative_pct": 0.0,
                    "is_vital_few": False,
                }
            ]
        )

    s = pd.Series(failure_records).value_counts().reset_index()
    s.columns = ["failure_mode", "failure_count"]

    total_failures = s["failure_count"].sum()
    s["failure_pct"] = (s["failure_count"] / total_failures * 100.0).round(2)
    s["cumulative_pct"] = s["failure_pct"].cumsum().round(2)
    # Vital few: cumulative percentage <= 80% (plus the boundary defect)
    s["is_vital_few"] = s["cumulative_pct"].shift(1, fill_value=0.0) < 80.0

    return s
