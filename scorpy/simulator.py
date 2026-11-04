"""Monte Carlo simulation module for SCOR-Py.

Implements:
- What-If disruption analysis (e.g. supplier lead time shifts)
- Monte Carlo resampling of delivery delays & fulfillment
- Confidence intervals (95%) for SCOR reliability metrics
- Safety stock and working capital trade-off simulator
- Agility (AG.1.1 Upside Supply Chain Flexibility) estimation
"""

from typing import Any, Dict, Optional

import numpy as np
import pandas as pd

from scorpy.reliability import ReliabilityMetrics


class SimulationResult:
    """Encapsulates the outputs of a Monte Carlo supply chain simulation.

    Parameters
    ----------
    baseline_metrics : Dict[str, float]
        Pre-disruption baseline SCOR metrics.
    runs_df : pd.DataFrame
        Metrics across all Monte Carlo iterations.
    scenario : Dict[str, Any]
        Scenario parameter dictionary applied.
    """

    def __init__(
        self,
        baseline_metrics: Dict[str, float],
        runs_df: pd.DataFrame,
        scenario: Dict[str, Any],
    ):
        self.baseline_metrics = baseline_metrics
        self.runs_df = runs_df
        self.scenario = scenario

    def compare_to_baseline(self, metric_name: str = "OTIF_rate") -> Dict[str, Any]:
        """Compare a simulated metric against the baseline with a 95% confidence interval.

        Parameters
        ----------
        metric_name : str, default "OTIF_rate"
            SCOR metric to evaluate (e.g. "OTIF_rate", "On_Time_rate", "In_Full_rate", "Perfect_Order_Fulfillment").

        Returns
        -------
        dict
            Dict with baseline, scenario_mean, delta_mean, ci_95_lower, ci_95_upper.
        """
        if metric_name not in self.runs_df.columns:
            raise KeyError(f"Metric '{metric_name}' not found in simulation results.")

        baseline = self.baseline_metrics.get(metric_name, 0.0)
        scenario_series = self.runs_df[metric_name]
        mean_val = float(scenario_series.mean())
        delta = mean_val - baseline
        ci_lower = float(np.percentile(scenario_series, 2.5))
        ci_upper = float(np.percentile(scenario_series, 97.5))

        return {
            "metric": metric_name,
            "baseline": round(baseline, 4),
            "scenario_mean": round(mean_val, 4),
            "delta_mean": round(delta, 4),
            "delta_pct": round((delta / baseline * 100.0) if baseline > 0 else 0.0, 2),
            "ci_95_lower": round(ci_lower, 4),
            "ci_95_upper": round(ci_upper, 4),
        }

    def summary(self) -> pd.DataFrame:
        """Generate a comparison table for all tracked metrics."""
        records = []
        for col in self.runs_df.columns:
            if col in self.baseline_metrics:
                records.append(self.compare_to_baseline(col))
        return pd.DataFrame(records)


class SupplyChainSimulator:
    """Monte Carlo simulator for evaluating supply chain disruptions and what-if scenarios.

    Parameters
    ----------
    df_orders : pd.DataFrame
        Historical sales order and fulfillment logs.
    order_id_col : str, default "so_number"
    order_date_col : str, default "order_date"
    promised_date_col : str, default "promised_delivery_date"
    actual_date_col : str, default "actual_delivery_date"
    ordered_qty_col : str, default "qty_ordered"
    delivered_qty_col : str, default "qty_delivered"
    damaged_flag_col : str, default "is_damaged"
    doc_accurate_col : str, default "is_doc_complete"
    supplier_col : Optional[str], default "supplier"
    seed : Optional[int], default 42
    """

    def __init__(
        self,
        df_orders: pd.DataFrame,
        order_id_col: str = "so_number",
        order_date_col: str = "order_date",
        promised_date_col: str = "promised_delivery_date",
        actual_date_col: str = "actual_delivery_date",
        ordered_qty_col: str = "qty_ordered",
        delivered_qty_col: str = "qty_delivered",
        damaged_flag_col: str = "is_damaged",
        doc_accurate_col: str = "is_doc_complete",
        supplier_col: Optional[str] = "supplier",
        seed: Optional[int] = 42,
    ):
        self.seed = seed
        self.rng = np.random.default_rng(seed)

        self.order_id_col = order_id_col
        self.order_date_col = order_date_col
        self.promised_date_col = promised_date_col
        self.actual_date_col = actual_date_col
        self.ordered_qty_col = ordered_qty_col
        self.delivered_qty_col = delivered_qty_col
        self.damaged_flag_col = damaged_flag_col
        self.doc_accurate_col = doc_accurate_col
        self.supplier_col = supplier_col

        df = df_orders.copy()
        df[self.order_date_col] = pd.to_datetime(df[self.order_date_col])
        df[self.promised_date_col] = pd.to_datetime(df[self.promised_date_col])
        df[self.actual_date_col] = pd.to_datetime(df[self.actual_date_col])

        # Exclude unshipped for baseline
        self.df = df[df[self.actual_date_col].notna()].copy()

        # Compute lead time differences in days
        # Lead time delta = actual_date - promised_date (days)
        actual_diff = (
            self.df[self.actual_date_col] - self.df[self.promised_date_col]
        ).dt.total_seconds() / 86400.0
        self.df["_delay_days"] = actual_diff

        # Calculate baseline metrics
        rel_baseline = ReliabilityMetrics(
            data=self.df,
            order_id_col=self.order_id_col,
            promised_date_col=self.promised_date_col,
            actual_date_col=self.actual_date_col,
            ordered_qty_col=self.ordered_qty_col,
            delivered_qty_col=self.delivered_qty_col,
            damaged_flag_col=self.damaged_flag_col,
            doc_accurate_col=self.doc_accurate_col,
            validate=False,
        )
        self.baseline_metrics = rel_baseline.evaluate_all()

    @classmethod
    def from_orders(
        cls,
        df_orders: pd.DataFrame,
        seed: Optional[int] = 42,
        **kwargs,
    ) -> "SupplyChainSimulator":
        """Convenience constructor from orders DataFrame."""
        return cls(df_orders, seed=seed, **kwargs)

    def run(
        self,
        n_runs: int = 1000,
        scenario: Optional[Dict[str, Any]] = None,
    ) -> SimulationResult:
        """Run Monte Carlo simulation over the order distribution under scenario shifts.

        Supported scenario keys:
        - `supplier_lead_time_shift_days`: int or float (e.g. +3, -2)
        - `supplier_filter`: str (apply lead time shift only to a specific supplier)
        - `demand_spike_pct`: float (e.g. 0.20 = +20% demand, may cause fulfillment drop)
        - `damage_rate_multiplier`: float (e.g. 1.5)
        - `doc_error_rate_multiplier`: float (e.g. 1.2)

        Returns
        -------
        SimulationResult
        """
        if scenario is None:
            scenario = {}

        shift_days = float(scenario.get("supplier_lead_time_shift_days", 0.0))
        target_supplier = scenario.get("supplier_filter", None)
        demand_spike = float(scenario.get("demand_spike_pct", 0.0))
        damage_mult = float(scenario.get("damage_rate_multiplier", 1.0))
        doc_error_mult = float(scenario.get("doc_error_rate_multiplier", 1.0))

        n_orders = len(self.df)
        base_delays = self.df["_delay_days"].to_numpy()
        base_ordered = self.df[self.ordered_qty_col].to_numpy()
        base_delivered = self.df[self.delivered_qty_col].to_numpy()
        base_damaged = self.df[self.damaged_flag_col].to_numpy().astype(bool)
        base_doc = self.df[self.doc_accurate_col].to_numpy().astype(bool)

        supplier_mask = np.ones(n_orders, dtype=bool)
        if target_supplier and self.supplier_col in self.df.columns:
            supplier_mask = (self.df[self.supplier_col] == target_supplier).to_numpy()

        results_list = []

        for _ in range(n_runs):
            # Resample order indices with replacement (bootstrap sample)
            idx = self.rng.choice(n_orders, size=n_orders, replace=True)

            # 1. Lead time shift
            sample_delays = base_delays[idx].copy()
            sample_mask = supplier_mask[idx]
            # Add shift and stochastic jitter (normal with sd=0.5)
            jitter = self.rng.normal(0, 0.5, size=n_orders)
            sample_delays[sample_mask] += shift_days + jitter[sample_mask]

            # On-time when delay <= 0
            is_on_time = sample_delays <= 0

            # 2. Demand spike impact on fulfillment
            sample_ordered = base_ordered[idx] * (1.0 + demand_spike)
            # If demand spikes, delivery capacity might lag slightly
            capacity_strain = max(0.0, demand_spike * 0.3)
            strain_factor = 1.0 - self.rng.uniform(0.0, capacity_strain, size=n_orders)
            sample_delivered = base_delivered[idx] * strain_factor
            is_in_full = sample_delivered >= sample_ordered

            # 3. Damage rate
            sample_damaged = base_damaged[idx].copy()
            if damage_mult > 1.0:
                extra_damage_prob = min(1.0, (damage_mult - 1.0) * sample_damaged.mean())
                flip_mask = (~sample_damaged) & (self.rng.random(size=n_orders) < extra_damage_prob)
                sample_damaged[flip_mask] = True
            is_damage_free = ~sample_damaged

            # 4. Doc accuracy
            sample_doc = base_doc[idx].copy()
            if doc_error_mult > 1.0:
                extra_err_prob = min(1.0, (doc_error_mult - 1.0) * (1.0 - sample_doc.mean()))
                flip_err = sample_doc & (self.rng.random(size=n_orders) < extra_err_prob)
                sample_doc[flip_err] = False
            is_doc_accurate = sample_doc

            # Combined metrics
            otif = is_on_time & is_in_full
            pof = is_on_time & is_in_full & is_damage_free & is_doc_accurate

            results_list.append(
                {
                    "On_Time_rate": float(is_on_time.mean()),
                    "In_Full_rate": float(is_in_full.mean()),
                    "OTIF_rate": float(otif.mean()),
                    "Damage_Free_rate": float(is_damage_free.mean()),
                    "Doc_Accurate_rate": float(is_doc_accurate.mean()),
                    "Perfect_Order_Fulfillment": float(pof.mean()),
                }
            )

        runs_df = pd.DataFrame(results_list)
        return SimulationResult(
            baseline_metrics=self.baseline_metrics,
            runs_df=runs_df,
            scenario=scenario,
        )

    @staticmethod
    def simulate_safety_stock_adjustment(
        avg_inventory_value: float,
        annual_cogs: float,
        annual_revenue: float,
        accounts_receivable: float,
        accounts_payable: float,
        safety_stock_pct_of_inventory: float = 0.40,
        safety_stock_change_pct: float = -0.15,
        days_in_year: int = 365,
    ) -> Dict[str, Any]:
        """Simulate the financial and cycle time impact of adjusting safety stock levels.

        Parameters
        ----------
        avg_inventory_value : float
            Baseline average inventory value.
        annual_cogs : float
            Annual COGS.
        annual_revenue : float
            Annual Revenue.
        accounts_receivable : float
            AR balance.
        accounts_payable : float
            AP balance.
        safety_stock_pct_of_inventory : float, default 0.40
            Fraction of total inventory consisting of safety stock buffer.
        safety_stock_change_pct : float, default -0.15
            Adjustment percentage to safety stock (e.g. -0.15 = 15% reduction).
        days_in_year : int, default 365

        Returns
        -------
        dict
            Dict with capital freed, baseline vs new IDS, C2C, working capital.
        """
        safety_stock_val = avg_inventory_value * safety_stock_pct_of_inventory
        delta_inventory = safety_stock_val * safety_stock_change_pct
        new_inventory_value = avg_inventory_value + delta_inventory
        capital_freed = -delta_inventory  # Positive if inventory decreases

        # Baseline
        base_ids = (avg_inventory_value / annual_cogs) * days_in_year
        base_dso = (accounts_receivable / annual_revenue) * days_in_year
        base_dpo = (accounts_payable / annual_cogs) * days_in_year
        base_c2c = base_ids + base_dso - base_dpo
        base_wc = avg_inventory_value + accounts_receivable - accounts_payable

        # New
        new_ids = (new_inventory_value / annual_cogs) * days_in_year
        new_c2c = new_ids + base_dso - base_dpo
        new_wc = new_inventory_value + accounts_receivable - accounts_payable

        delta_ids = new_ids - base_ids
        delta_c2c = new_c2c - base_c2c

        return {
            "baseline_inventory_value": round(avg_inventory_value, 2),
            "safety_stock_share_pct": round(safety_stock_pct_of_inventory * 100.0, 1),
            "safety_stock_change_pct": round(safety_stock_change_pct * 100.0, 1),
            "working_capital_freed": round(capital_freed, 2),
            "new_inventory_value": round(new_inventory_value, 2),
            "baseline_IDS_days": round(base_ids, 1),
            "new_IDS_days": round(new_ids, 1),
            "delta_IDS_days": round(delta_ids, 1),
            "baseline_C2C_days": round(base_c2c, 1),
            "new_C2C_days": round(new_c2c, 1),
            "delta_C2C_days": round(delta_c2c, 1),
            "baseline_working_capital": round(base_wc, 2),
            "new_working_capital": round(new_wc, 2),
        }

    def estimate_upside_flexibility(
        self,
        target_demand_increase_pct: float = 0.20,
        historical_capacity_margin: float = 0.10,
    ) -> Dict[str, Any]:
        """Estimate SCOR Agility metric (AG.1.1 Upside Supply Chain Flexibility).

        Calculates estimated days to achieve an unplanned, sustainable +20% delivery
        increase based on supplier lead times and capacity headroom.
        """
        # Average lead time
        ofct_mean = float(
            (self.df[self.actual_date_col] - self.df[self.order_date_col]).dt.total_seconds().mean()
            / 86400.0
        )
        # Lead time needed to ramp up additional capacity
        # Ramp-up days ~ OFCT + buffer depending on capacity gap
        capacity_gap = max(0.0, target_demand_increase_pct - historical_capacity_margin)
        ramp_factor = 1.0 + (capacity_gap / target_demand_increase_pct) * 1.5
        flexibility_days = round(ofct_mean * ramp_factor, 1)

        return {
            "metric": "AG.1.1 Upside Supply Chain Flexibility",
            "target_increase_pct": target_demand_increase_pct * 100.0,
            "estimated_days_to_adapt": flexibility_days,
            "mean_current_cycle_days": round(ofct_mean, 1),
            "note": "Estimated time required to sustainably fulfill +20% demand volume without service level degradation.",
        }
