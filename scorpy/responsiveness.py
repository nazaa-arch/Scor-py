"""Responsiveness metrics module for SCOR-Py (SCOR Level 1 & 2).

Implements:
- Order Fulfillment Cycle Time (OFCT, RS.1.1)
- Lead Time Distribution (mean, median, 90th percentile)
- Lead Time Variance & Adherence
- Multi-stage cycle time breakdown (Source, Make, Deliver)
"""

from typing import Dict, Optional, Union

import numpy as np
import pandas as pd


class ResponsivenessMetrics:
    """Calculates SCOR Responsiveness metrics (RS.1.1 Order Fulfillment Cycle Time).

    Parameters
    ----------
    data : pd.DataFrame
        Transactional order log DataFrame.
    order_date_col : str, default "order_date"
        Column name for order placement date.
    actual_date_col : str, default "actual_delivery_date"
        Column name for actual delivery date.
    promised_date_col : Optional[str], default "promised_delivery_date"
        Column name for promised delivery date (optional, for lead time adherence).
    source_cycle_col : Optional[str], default None
        Optional column for Source stage duration (days).
    make_cycle_col : Optional[str], default None
        Optional column for Make stage duration (days).
    deliver_cycle_col : Optional[str], default None
        Optional column for Deliver stage duration (days).
    """

    def __init__(
        self,
        data: pd.DataFrame,
        order_date_col: str = "order_date",
        actual_date_col: str = "actual_delivery_date",
        promised_date_col: Optional[str] = "promised_delivery_date",
        source_cycle_col: Optional[str] = None,
        make_cycle_col: Optional[str] = None,
        deliver_cycle_col: Optional[str] = None,
    ):
        if data is None or len(data) == 0:
            raise ValueError("Input data DataFrame cannot be empty.")

        self.df = data.copy()
        self.order_date_col = order_date_col
        self.actual_date_col = actual_date_col
        self.promised_date_col = promised_date_col
        self.source_cycle_col = source_cycle_col
        self.make_cycle_col = make_cycle_col
        self.deliver_cycle_col = deliver_cycle_col

        self.df[self.order_date_col] = pd.to_datetime(self.df[self.order_date_col])
        self.df[self.actual_date_col] = pd.to_datetime(self.df[self.actual_date_col])

        if self.promised_date_col and self.promised_date_col in self.df.columns:
            self.df[self.promised_date_col] = pd.to_datetime(self.df[self.promised_date_col])

        # Exclude unshipped orders from cycle time calculation
        self.valid_df = self.df[self.df[self.actual_date_col].notna()].copy()
        self._compute_cycle_times()

    def _compute_cycle_times(self) -> None:
        """Compute end-to-end cycle time in days."""
        if len(self.valid_df) == 0:
            self.valid_df["_ofct_days"] = pd.Series(dtype=float)
            return

        # Check if 3-stage SCOR columns exist
        has_stages = (
            self.source_cycle_col in self.valid_df.columns
            and self.make_cycle_col in self.valid_df.columns
            and self.deliver_cycle_col in self.valid_df.columns
        )
        if has_stages:
            self.valid_df["_ofct_days"] = (
                self.valid_df[self.source_cycle_col]
                + self.valid_df[self.make_cycle_col]
                + self.valid_df[self.deliver_cycle_col]
            ).astype(float)
        else:
            delta = self.valid_df[self.actual_date_col] - self.valid_df[self.order_date_col]
            # Convert timedelta to float days
            self.valid_df["_ofct_days"] = delta.dt.total_seconds() / 86400.0

        if self.promised_date_col and self.promised_date_col in self.valid_df.columns:
            delta_promised = (
                self.valid_df[self.promised_date_col] - self.valid_df[self.order_date_col]
            )
            self.valid_df["_promised_days"] = delta_promised.dt.total_seconds() / 86400.0
            # Variance: positive means delivered late, negative means delivered early
            self.valid_df["_lead_time_variance_days"] = (
                self.valid_df["_ofct_days"] - self.valid_df["_promised_days"]
            )

    def order_fulfillment_cycle_time(
        self, group_by: Optional[str] = None
    ) -> Union[Dict[str, float], pd.DataFrame]:
        """Compute Order Fulfillment Cycle Time (OFCT) summary statistics.

        Returns mean, median, p90, min, max, std.
        """
        if len(self.valid_df) == 0:
            empty_res = {
                "mean_days": 0.0,
                "median_days": 0.0,
                "p90_days": 0.0,
                "min_days": 0.0,
                "max_days": 0.0,
                "std_days": 0.0,
            }
            return empty_res if group_by is None else pd.DataFrame([empty_res])

        if group_by is None:
            s = self.valid_df["_ofct_days"]
            return {
                "mean_days": round(float(s.mean()), 2),
                "median_days": round(float(s.median()), 2),
                "p90_days": round(float(np.percentile(s, 90)), 2),
                "min_days": round(float(s.min()), 2),
                "max_days": round(float(s.max()), 2),
                "std_days": round(float(s.std()), 2),
            }
        else:
            if group_by not in self.valid_df.columns:
                raise KeyError(f"Group by column '{group_by}' not found in data.")

            grouped = self.valid_df.groupby(group_by)["_ofct_days"]
            summary = pd.DataFrame(
                {
                    "mean_days": grouped.mean().round(2),
                    "median_days": grouped.median().round(2),
                    "p90_days": grouped.apply(lambda s: np.percentile(s, 90)).round(2),
                    "min_days": grouped.min().round(2),
                    "max_days": grouped.max().round(2),
                    "std_days": grouped.std().round(2),
                }
            )
            return summary

    def lead_time_variance(
        self, group_by: Optional[str] = None
    ) -> Union[Dict[str, float], pd.DataFrame]:
        """Compute lead time variance compared to promised dates."""
        if "_lead_time_variance_days" not in self.valid_df.columns:
            raise ValueError("Promised delivery date column not available for variance analysis.")

        if group_by is None:
            s = self.valid_df["_lead_time_variance_days"]
            return {
                "mean_variance_days": round(float(s.mean()), 2),
                "median_variance_days": round(float(s.median()), 2),
                "pct_early_or_on_time": round(float((s <= 0).mean()), 4),
                "pct_delayed": round(float((s > 0).mean()), 4),
            }
        else:
            grouped = self.valid_df.groupby(group_by)["_lead_time_variance_days"]
            return pd.DataFrame(
                {
                    "mean_variance_days": grouped.mean().round(2),
                    "median_variance_days": grouped.median().round(2),
                    "pct_early_or_on_time": grouped.apply(lambda s: (s <= 0).mean()).round(4),
                    "pct_delayed": grouped.apply(lambda s: (s > 0).mean()).round(4),
                }
            )
