"""Supply Chain Management Cost metrics module for SCOR-Py (CO.1.1).

Implements:
- Total Supply Chain Management Cost (CO.1.1)
- SCM Cost as Percentage of Revenue
- Cost breakdown (Transport, Warehousing, Procurement, Return/Reverse Logistics)
- Periodic trend analysis
"""

from typing import Any, Dict, List, Optional

import pandas as pd


class CostMetrics:
    """Calculates SCOR Cost metrics (CO.1.1 Total Supply Chain Management Cost).

    Parameters
    ----------
    revenue : float
        Gross revenue / total sales.
    transport_cost : float, default 0.0
        Freight / transportation logistics cost.
    warehousing_cost : float, default 0.0
        Storage, holding, and distribution center cost.
    procurement_cost : float, default 0.0
        Purchasing and sourcing management cost.
    return_cost : float, default 0.0
        Reverse logistics, inspection, and return cost.
    other_costs : Optional[Dict[str, float]], default None
        Optional additional SCM costs (e.g. planning, packaging).
    """

    def __init__(
        self,
        revenue: float,
        transport_cost: float = 0.0,
        warehousing_cost: float = 0.0,
        procurement_cost: float = 0.0,
        return_cost: float = 0.0,
        other_costs: Optional[Dict[str, float]] = None,
    ):
        if revenue <= 0:
            raise ZeroDivisionError("Revenue must be strictly greater than 0.")

        self.revenue = float(revenue)
        self.transport_cost = float(transport_cost)
        self.warehousing_cost = float(warehousing_cost)
        self.procurement_cost = float(procurement_cost)
        self.return_cost = float(return_cost)
        self.other_costs = {k: float(v) for k, v in (other_costs or {}).items()}

    @classmethod
    def from_dataframe(
        cls,
        df: pd.DataFrame,
        revenue_col: str = "revenue",
        transport_col: str = "transport_cost",
        warehousing_col: str = "warehousing_cost",
        procurement_col: str = "procurement_cost",
        return_col: str = "return_cost",
        other_cols: Optional[List[str]] = None,
    ) -> "CostMetrics":
        """Instantiate CostMetrics by aggregating columns from a financial DataFrame."""
        rev = float(df[revenue_col].sum())
        trans = float(df[transport_col].sum()) if transport_col in df.columns else 0.0
        ware = float(df[warehousing_col].sum()) if warehousing_col in df.columns else 0.0
        proc = float(df[procurement_col].sum()) if procurement_col in df.columns else 0.0
        ret = float(df[return_col].sum()) if return_col in df.columns else 0.0

        others = {}
        if other_cols:
            for col in other_cols:
                if col in df.columns:
                    others[col] = float(df[col].sum())

        return cls(
            revenue=rev,
            transport_cost=trans,
            warehousing_cost=ware,
            procurement_cost=proc,
            return_cost=ret,
            other_costs=others,
        )

    def total_scm_cost(self) -> float:
        """Calculate total SCM cost."""
        base_sum = (
            self.transport_cost + self.warehousing_cost + self.procurement_cost + self.return_cost
        )
        others_sum = sum(self.other_costs.values())
        return base_sum + others_sum

    def scm_cost_pct_revenue(self) -> float:
        """Calculate SCM Cost as a percentage of revenue (CO.1.1)."""
        return (self.total_scm_cost() / self.revenue) * 100.0

    def cost_breakdown(self) -> Dict[str, Dict[str, float]]:
        """Return detailed cost breakdown with amount, pct of revenue, and pct of total SCM cost."""
        total = self.total_scm_cost()
        safe_total = total if total > 0 else 1.0

        components = {
            "transportation": self.transport_cost,
            "warehousing": self.warehousing_cost,
            "procurement": self.procurement_cost,
            "returns": self.return_cost,
        }
        components.update(self.other_costs)

        breakdown = {}
        for name, amount in components.items():
            breakdown[name] = {
                "amount": round(amount, 2),
                "pct_of_revenue": round((amount / self.revenue) * 100.0, 3),
                "pct_of_scm_cost": round((amount / safe_total) * 100.0, 3),
            }
        return breakdown

    def evaluate_all(self) -> Dict[str, Any]:
        """Evaluate all SCM cost metrics."""
        return {
            "revenue": round(self.revenue, 2),
            "total_scm_cost": round(self.total_scm_cost(), 2),
            "scm_cost_pct_revenue": round(self.scm_cost_pct_revenue(), 2),
            "breakdown": self.cost_breakdown(),
        }

    @staticmethod
    def periodic_trend(
        df: pd.DataFrame,
        period_col: str = "period",
        revenue_col: str = "revenue",
        cost_cols: Optional[List[str]] = None,
    ) -> pd.DataFrame:
        """Compute periodic SCM cost trend from monthly/quarterly records."""
        if cost_cols is None:
            cost_cols = [
                c
                for c in ["transport_cost", "warehousing_cost", "procurement_cost", "return_cost"]
                if c in df.columns
            ]
        trend_df = df[[period_col, revenue_col] + cost_cols].copy()
        trend_df["total_scm_cost"] = trend_df[cost_cols].sum(axis=1)
        trend_df["scm_cost_pct"] = (trend_df["total_scm_cost"] / trend_df[revenue_col]) * 100.0
        return trend_df
