"""Asset Management Efficiency metrics module for SCOR-Py (SCOR Level 1 & 2).

Implements:
- Cash-to-Cash Cycle Time (AM.1.1)
  - Inventory Days of Supply (IDS)
  - Days Sales Outstanding (DSO)
  - Days Payable Outstanding (DPO)
- Return on Supply Chain Fixed Assets (AM.1.2)
- Return on Working Capital (AM.1.3)
"""

from typing import Any, Dict, Optional

import pandas as pd


class AssetMetrics:
    """Calculates SCOR Asset Management Efficiency metrics.

    Parameters
    ----------
    annual_cogs : float
        Cost of Goods Sold (annual or annualized period).
    annual_revenue : float
        Gross revenue / sales (annual or annualized period).
    avg_inventory_value : float
        Average inventory value over the period.
    accounts_receivable : float
        Accounts receivable (AR) balance.
    accounts_payable : float
        Accounts payable (AP) balance.
    annual_purchases : Optional[float], default None
        Optional annual purchases amount (if DPO is calculated against purchases rather than COGS).
    scm_cost : Optional[float], default None
        Total supply chain management costs (for AM.1.2 and AM.1.3).
    sc_fixed_assets : Optional[float], default None
        Supply chain fixed assets value (for AM.1.2).
    days_in_year : int, default 365
        Number of days in reporting year (e.g. 365 or 360).
    """

    def __init__(
        self,
        annual_cogs: float,
        annual_revenue: float,
        avg_inventory_value: float,
        accounts_receivable: float,
        accounts_payable: float,
        annual_purchases: Optional[float] = None,
        scm_cost: Optional[float] = None,
        sc_fixed_assets: Optional[float] = None,
        days_in_year: int = 365,
    ):
        if annual_cogs <= 0:
            raise ZeroDivisionError("annual_cogs must be strictly greater than 0.")
        if annual_revenue <= 0:
            raise ZeroDivisionError("annual_revenue must be strictly greater than 0.")
        if days_in_year <= 0:
            raise ValueError("days_in_year must be positive.")

        self.annual_cogs = float(annual_cogs)
        self.annual_revenue = float(annual_revenue)
        self.avg_inventory_value = float(avg_inventory_value)
        self.accounts_receivable = float(accounts_receivable)
        self.accounts_payable = float(accounts_payable)
        self.annual_purchases = float(annual_purchases) if annual_purchases is not None else None
        self.scm_cost = float(scm_cost) if scm_cost is not None else None
        self.sc_fixed_assets = float(sc_fixed_assets) if sc_fixed_assets is not None else None
        self.days_in_year = int(days_in_year)

    @classmethod
    def from_dataframes(
        cls,
        df_financials: pd.DataFrame,
        df_inventory: Optional[pd.DataFrame] = None,
        revenue_col: str = "revenue",
        cogs_col: str = "cogs",
        ar_col: str = "accounts_receivable",
        ap_col: str = "accounts_payable",
        fixed_assets_col: Optional[str] = "sc_fixed_assets",
        inventory_value_col: Optional[str] = "inventory_value",
        scm_cost_cols: Optional[list] = None,
        days_in_year: int = 365,
    ) -> "AssetMetrics":
        """Factory method to instantiate AssetMetrics from pandas DataFrames."""
        total_revenue = float(df_financials[revenue_col].sum())
        total_cogs = float(df_financials[cogs_col].sum())
        avg_ar = float(df_financials[ar_col].mean())
        avg_ap = float(df_financials[ap_col].mean())

        # Average inventory value
        if df_inventory is not None and inventory_value_col in df_inventory.columns:
            # If daily records, average daily total inventory
            if "date" in df_inventory.columns:
                daily_totals = df_inventory.groupby("date")[inventory_value_col].sum()
                avg_inv = float(daily_totals.mean())
            else:
                avg_inv = float(df_inventory[inventory_value_col].mean())
        else:
            # Fallback or approximation if not in inventory dataframe
            avg_inv = total_cogs * (45.0 / days_in_year)

        sc_fixed_assets = None
        if fixed_assets_col and fixed_assets_col in df_financials.columns:
            sc_fixed_assets = float(df_financials[fixed_assets_col].mean())

        scm_cost = None
        if scm_cost_cols:
            valid_cols = [c for c in scm_cost_cols if c in df_financials.columns]
            if valid_cols:
                scm_cost = float(df_financials[valid_cols].sum().sum())

        return cls(
            annual_cogs=total_cogs,
            annual_revenue=total_revenue,
            avg_inventory_value=avg_inv,
            accounts_receivable=avg_ar,
            accounts_payable=avg_ap,
            scm_cost=scm_cost,
            sc_fixed_assets=sc_fixed_assets,
            days_in_year=days_in_year,
        )

    def inventory_days_of_supply(self) -> float:
        """Calculate Inventory Days of Supply (IDS).

        Formula: (avg_inventory_value / annual_cogs) * days_in_year
        """
        return (self.avg_inventory_value / self.annual_cogs) * self.days_in_year

    def days_sales_outstanding(self) -> float:
        """Calculate Days Sales Outstanding (DSO).

        Formula: (accounts_receivable / annual_revenue) * days_in_year
        """
        return (self.accounts_receivable / self.annual_revenue) * self.days_in_year

    def days_payable_outstanding(self) -> float:
        """Calculate Days Payable Outstanding (DPO).

        Formula: (accounts_payable / annual_cogs) * days_in_year
        (or annual_purchases if provided).
        """
        denominator = (
            self.annual_purchases if self.annual_purchases is not None else self.annual_cogs
        )
        if denominator <= 0:
            raise ZeroDivisionError("Denominator for DPO must be strictly greater than 0.")
        return (self.accounts_payable / denominator) * self.days_in_year

    def cash_to_cash_cycle(self) -> Dict[str, float]:
        """Calculate Cash-to-Cash Cycle Time (AM.1.1).

        Formula: C2C = IDS + DSO - DPO
        """
        ids = self.inventory_days_of_supply()
        dso = self.days_sales_outstanding()
        dpo = self.days_payable_outstanding()
        c2c = ids + dso - dpo
        return {
            "IDS": round(ids, 1),
            "DSO": round(dso, 1),
            "DPO": round(dpo, 1),
            "C2C_days": round(c2c, 1),
        }

    def return_on_fixed_assets(self) -> Optional[float]:
        """Calculate Return on Supply Chain Fixed Assets (AM.1.2).

        Formula: (annual_revenue - annual_cogs - scm_cost) / sc_fixed_assets
        """
        if self.sc_fixed_assets is None or self.scm_cost is None:
            return None
        if self.sc_fixed_assets <= 0:
            raise ZeroDivisionError("Supply chain fixed assets must be strictly greater than 0.")
        operating_income_sc = self.annual_revenue - self.annual_cogs - self.scm_cost
        return operating_income_sc / self.sc_fixed_assets

    def return_on_working_capital(self) -> Optional[float]:
        """Calculate Return on Working Capital (AM.1.3).

        Formula: (annual_revenue - annual_cogs - scm_cost) / (avg_inventory + AR - AP)
        """
        if self.scm_cost is None:
            return None
        working_capital = (
            self.avg_inventory_value + self.accounts_receivable - self.accounts_payable
        )
        if abs(working_capital) < 1e-6:
            raise ZeroDivisionError("Working capital cannot be zero.")
        operating_income_sc = self.annual_revenue - self.annual_cogs - self.scm_cost
        return operating_income_sc / working_capital

    def evaluate_all(self) -> Dict[str, Any]:
        """Evaluate all asset efficiency metrics."""
        c2c = self.cash_to_cash_cycle()
        res = {
            **c2c,
            "annual_revenue": self.annual_revenue,
            "annual_cogs": self.annual_cogs,
            "avg_inventory_value": self.avg_inventory_value,
            "accounts_receivable": self.accounts_receivable,
            "accounts_payable": self.accounts_payable,
        }
        rofa = self.return_on_fixed_assets()
        if rofa is not None:
            res["return_on_sc_fixed_assets"] = round(rofa, 4)
        rowc = self.return_on_working_capital()
        if rowc is not None:
            res["return_on_working_capital"] = round(rowc, 4)
        return res
