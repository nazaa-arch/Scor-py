"""Reliability metrics module for SCOR-Py (SCOR Level 1 & 2).

Implements:
- Perfect Order Fulfillment (RL.1.1)
- OTIF (On-Time In-Full)
- On-Time Delivery Rate (with configurable grace days)
- In-Full Delivery Rate (with configurable quantity tolerance)
- Damage-Free Rate
- Documentation Accuracy Rate
"""

from typing import Dict, Optional, Union

import pandas as pd

from scorpy.schema import validate_orders


class ReliabilityMetrics:
    """Calculates SCOR Reliability metrics (RL.1.1 and sub-metrics).

    Parameters
    ----------
    data : pd.DataFrame
        Transactional order log DataFrame.
    order_id_col : str, default "so_number"
        Column name for unique order identifier.
    promised_date_col : str, default "promised_delivery_date"
        Column name for promised delivery date.
    actual_date_col : str, default "actual_delivery_date"
        Column name for actual delivery date.
    ordered_qty_col : str, default "qty_ordered"
        Column name for ordered quantity.
    delivered_qty_col : str, default "qty_delivered"
        Column name for delivered quantity.
    damaged_flag_col : str, default "is_damaged"
        Column name for damage boolean flag (True if damaged).
    doc_accurate_col : str, default "is_doc_complete"
        Column name for documentation completeness flag (True if accurate/complete).
    on_time_grace_days : int, default 0
        Grace period in days allowed before delivery is considered late.
    in_full_tolerance : float, default 0.0
        Allowed fraction tolerance for short delivery (e.g. 0.02 = 2% tolerance).
    validate : bool, default True
        Whether to validate inputs against Pandera schema.
    exclude_unshipped : bool, default True
        Whether to exclude orders with null actual delivery dates from the denominator.
    """

    def __init__(
        self,
        data: pd.DataFrame,
        order_id_col: str = "so_number",
        promised_date_col: str = "promised_delivery_date",
        actual_date_col: str = "actual_delivery_date",
        ordered_qty_col: str = "qty_ordered",
        delivered_qty_col: str = "qty_delivered",
        damaged_flag_col: str = "is_damaged",
        doc_accurate_col: str = "is_doc_complete",
        on_time_grace_days: int = 0,
        in_full_tolerance: float = 0.0,
        validate: bool = True,
        exclude_unshipped: bool = True,
    ):
        if data is None or len(data) == 0:
            raise ValueError("Input data DataFrame cannot be empty.")

        self.order_id_col = order_id_col
        self.promised_date_col = promised_date_col
        self.actual_date_col = actual_date_col
        self.ordered_qty_col = ordered_qty_col
        self.delivered_qty_col = delivered_qty_col
        self.damaged_flag_col = damaged_flag_col
        self.doc_accurate_col = doc_accurate_col
        self.on_time_grace_days = max(0, int(on_time_grace_days))
        self.in_full_tolerance = max(0.0, float(in_full_tolerance))
        self.exclude_unshipped = exclude_unshipped

        df = data.copy()
        if validate:
            df = validate_orders(
                df,
                order_id_col=self.order_id_col,
                promised_date_col=self.promised_date_col,
                actual_date_col=self.actual_date_col,
                ordered_qty_col=self.ordered_qty_col,
                delivered_qty_col=self.delivered_qty_col,
                damaged_flag_col=self.damaged_flag_col,
                doc_accurate_col=self.doc_accurate_col,
                allow_unshipped=True,
            )
        else:
            df[self.promised_date_col] = pd.to_datetime(df[self.promised_date_col])
            df[self.actual_date_col] = pd.to_datetime(df[self.actual_date_col])

        # Track unshipped orders count
        self._unshipped_count = int(df[self.actual_date_col].isna().sum())

        if self.exclude_unshipped:
            self.df = df[df[self.actual_date_col].notna()].copy()
        else:
            self.df = df

        self._compute_flags()

    @property
    def unshipped_orders_count(self) -> int:
        """Count of orders without an actual delivery date."""
        return self._unshipped_count

    def _compute_flags(self) -> None:
        """Compute row-level boolean flags for each condition."""
        if len(self.df) == 0:
            self.df["_is_on_time"] = pd.Series(dtype=bool)
            self.df["_is_in_full"] = pd.Series(dtype=bool)
            self.df["_is_damage_free"] = pd.Series(dtype=bool)
            self.df["_is_doc_accurate"] = pd.Series(dtype=bool)
            self.df["_is_otif"] = pd.Series(dtype=bool)
            self.df["_is_pof"] = pd.Series(dtype=bool)
            return

        # 1. On-Time check
        # actual_date <= promised_date + grace_days
        grace_delta = pd.to_timedelta(self.on_time_grace_days, unit="D")
        self.df["_is_on_time"] = self.df[self.actual_date_col] <= (
            self.df[self.promised_date_col] + grace_delta
        )

        # 2. In-Full check
        # qty_delivered >= qty_ordered * (1 - tolerance)
        threshold = self.df[self.ordered_qty_col] * (1.0 - self.in_full_tolerance)
        # Using floating tolerance check with small epsilon
        self.df["_is_in_full"] = self.df[self.delivered_qty_col] >= (threshold - 1e-9)

        # 3. Damage-Free check
        # not is_damaged
        self.df["_is_damage_free"] = ~self.df[self.damaged_flag_col].astype(bool)

        # 4. Doc-Accurate check
        # is_doc_complete
        self.df["_is_doc_accurate"] = self.df[self.doc_accurate_col].astype(bool)

        # 5. OTIF: On-Time AND In-Full
        self.df["_is_otif"] = self.df["_is_on_time"] & self.df["_is_in_full"]

        # 6. POF: All four conditions satisfied simultaneously
        self.df["_is_pof"] = (
            self.df["_is_on_time"]
            & self.df["_is_in_full"]
            & self.df["_is_damage_free"]
            & self.df["_is_doc_accurate"]
        )

    def detailed_orders(self) -> pd.DataFrame:
        """Return the DataFrame with added boolean evaluation flags."""
        return self.df.copy()

    def _calc_rate(self, flag_col: str, group_by: Optional[str] = None) -> Union[float, pd.Series]:
        if len(self.df) == 0:
            return 0.0 if group_by is None else pd.Series(dtype=float)

        if group_by is None:
            return float(self.df[flag_col].mean())
        else:
            if group_by not in self.df.columns:
                raise KeyError(f"Group by column '{group_by}' not found in data.")
            return self.df.groupby(group_by)[flag_col].mean()

    def on_time_rate(self, group_by: Optional[str] = None) -> Union[float, pd.Series]:
        """Percentage of orders delivered on time."""
        return self._calc_rate("_is_on_time", group_by)

    def in_full_rate(self, group_by: Optional[str] = None) -> Union[float, pd.Series]:
        """Percentage of orders delivered in full."""
        return self._calc_rate("_is_in_full", group_by)

    def otif_rate(self, group_by: Optional[str] = None) -> Union[float, pd.Series]:
        """Percentage of orders delivered On-Time and In-Full."""
        return self._calc_rate("_is_is_otif" if "_is_is_otif" in self.df else "_is_otif", group_by)

    def damage_free_rate(self, group_by: Optional[str] = None) -> Union[float, pd.Series]:
        """Percentage of orders delivered without damage."""
        return self._calc_rate("_is_damage_free", group_by)

    def doc_accurate_rate(self, group_by: Optional[str] = None) -> Union[float, pd.Series]:
        """Percentage of orders delivered with accurate documentation."""
        return self._calc_rate("_is_doc_accurate", group_by)

    def perfect_order_fulfillment(self, group_by: Optional[str] = None) -> Union[float, pd.Series]:
        """Perfect Order Fulfillment rate (RL.1.1)."""
        return self._calc_rate("_is_pof", group_by)

    def evaluate_all(self, group_by: Optional[str] = None) -> Union[Dict[str, float], pd.DataFrame]:
        """Evaluate all SCOR reliability metrics.

        Parameters
        ----------
        group_by : Optional[str], default None
            Column name to segment calculations by (e.g. customer_segment).

        Returns
        -------
        dict or pd.DataFrame
            Dictionary if group_by is None, or pd.DataFrame indexed by group.
        """
        if group_by is None:
            return {
                "On_Time_rate": round(float(self.on_time_rate()), 4),
                "In_Full_rate": round(float(self.in_full_rate()), 4),
                "OTIF_rate": round(float(self.otif_rate()), 4),
                "Damage_Free_rate": round(float(self.damage_free_rate()), 4),
                "Doc_Accurate_rate": round(float(self.doc_accurate_rate()), 4),
                "Perfect_Order_Fulfillment": round(float(self.perfect_order_fulfillment()), 4),
                "Total_Orders_Evaluated": len(self.df),
                "Unshipped_Orders_Excluded": self._unshipped_count,
            }
        else:
            if group_by not in self.df.columns:
                raise KeyError(f"Group by column '{group_by}' not found in data.")

            grouped = self.df.groupby(group_by)
            summary = pd.DataFrame(
                {
                    "Total_Orders": grouped.size(),
                    "On_Time_rate": grouped["_is_on_time"].mean(),
                    "In_Full_rate": grouped["_is_in_full"].mean(),
                    "OTIF_rate": grouped["_is_otif"].mean(),
                    "Damage_Free_rate": grouped["_is_damage_free"].mean(),
                    "Doc_Accurate_rate": grouped["_is_doc_accurate"].mean(),
                    "Perfect_Order_Fulfillment": grouped["_is_pof"].mean(),
                }
            ).round(4)
            return summary
