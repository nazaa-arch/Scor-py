"""Unit tests for scorpy.simulator."""

import pandas as pd
import pytest

from scorpy.simulator import SupplyChainSimulator


@pytest.fixture
def sample_orders_df():
    # 20 orders with some delays and variations
    records = []
    for i in range(20):
        # 16 on time (actual Jan 5 <= promised Jan 5), 4 delayed by 2 days
        actual = "2025-01-05" if i < 16 else "2025-01-07"
        records.append(
            {
                "so_number": f"SO-{i + 1}",
                "order_date": "2025-01-01",
                "promised_delivery_date": "2025-01-05",
                "actual_delivery_date": actual,
                "qty_ordered": 100,
                "qty_delivered": 100 if i < 18 else 80,
                "is_damaged": False,
                "is_doc_complete": True,
                "supplier": "Vendor A" if i < 10 else "Vendor B",
            }
        )
    return pd.DataFrame(records)


def test_simulation_run_reproducible(sample_orders_df):
    sim1 = SupplyChainSimulator.from_orders(sample_orders_df, seed=42)
    res1 = sim1.run(n_runs=100, scenario={"supplier_lead_time_shift_days": 2})

    sim2 = SupplyChainSimulator.from_orders(sample_orders_df, seed=42)
    res2 = sim2.run(n_runs=100, scenario={"supplier_lead_time_shift_days": 2})

    comp1 = res1.compare_to_baseline("OTIF_rate")
    comp2 = res2.compare_to_baseline("OTIF_rate")
    assert comp1["scenario_mean"] == comp2["scenario_mean"]
    assert comp1["ci_95_lower"] == comp2["ci_95_lower"]


def test_lead_time_shift_lowers_on_time_rate(sample_orders_df):
    sim = SupplyChainSimulator.from_orders(sample_orders_df, seed=42)
    res = sim.run(n_runs=200, scenario={"supplier_lead_time_shift_days": 5})

    comp = res.compare_to_baseline("On_Time_rate")
    assert comp["scenario_mean"] < comp["baseline"]
    assert comp["delta_mean"] < 0


def test_summary_dataframe(sample_orders_df):
    sim = SupplyChainSimulator.from_orders(sample_orders_df, seed=42)
    res = sim.run(n_runs=50)
    summary_df = res.summary()
    assert isinstance(summary_df, pd.DataFrame)
    assert "metric" in summary_df.columns
    assert "baseline" in summary_df.columns
    assert "scenario_mean" in summary_df.columns
    assert "ci_95_lower" in summary_df.columns
    assert "ci_95_upper" in summary_df.columns


def test_safety_stock_adjustment_calculation():
    """Verify example from docs:
    avg_inventory = Rp 2,100,000,000, 40% safety stock share, -15% reduction ->
    Rp 126,000,000 capital freed, -3.1 days IDS.
    """
    res = SupplyChainSimulator.simulate_safety_stock_adjustment(
        avg_inventory_value=2_100_000_000,
        annual_cogs=15_000_000_000,
        annual_revenue=22_500_000_000,
        accounts_receivable=1_800_000_000,
        accounts_payable=1_400_000_000,
        safety_stock_pct_of_inventory=0.40,
        safety_stock_change_pct=-0.15,
        days_in_year=365,
    )

    assert res["working_capital_freed"] == 126_000_000.0
    assert res["delta_IDS_days"] == -3.1
    assert res["baseline_C2C_days"] == 46.2
    assert res["delta_C2C_days"] == -3.1


def test_upside_flexibility(sample_orders_df):
    sim = SupplyChainSimulator.from_orders(sample_orders_df, seed=42)
    res = sim.estimate_upside_flexibility(target_demand_increase_pct=0.20)
    assert res["target_increase_pct"] == 20.0
    assert res["estimated_days_to_adapt"] > 0


def test_simulation_with_multipliers_and_filters(sample_orders_df):
    sim = SupplyChainSimulator.from_orders(sample_orders_df, seed=42)
    res = sim.run(
        n_runs=50,
        scenario={
            "supplier_lead_time_shift_days": 2,
            "supplier_filter": "Vendor A",
            "demand_spike_pct": 0.20,
            "damage_rate_multiplier": 1.5,
            "doc_error_rate_multiplier": 1.5,
        },
    )
    summary = res.summary()
    assert len(summary) >= 4
