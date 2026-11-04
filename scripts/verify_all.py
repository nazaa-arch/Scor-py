"""Verification script to test all SCOR-Py components against specifications."""

import os
import sys
import pandas as pd
from scorpy.reliability import ReliabilityMetrics
from scorpy.asset_efficiency import AssetMetrics
from scorpy.responsiveness import ResponsivenessMetrics
from scorpy.cost import CostMetrics
from scorpy.simulator import SupplyChainSimulator
from scorpy.schema import validate_orders, validate_financials, validate_inventory
from dashboard.components.gauge import create_gauge_chart
from dashboard.components.waterfall import create_c2c_waterfall, create_cost_waterfall
from dashboard.components.sankey import create_delivery_sankey

def verify_all():
    print("=" * 60)
    print("1. CHECKING DATASETS AND SCHEMAS")
    print("=" * 60)
    df_orders = pd.read_csv("data/sample_orders.csv", parse_dates=["order_date", "promised_delivery_date", "actual_delivery_date"])
    df_fin = pd.read_csv("data/sample_financials.csv")
    df_inv = pd.read_csv("data/sample_inventory.csv")

    vo = validate_orders(df_orders)
    vf = validate_financials(df_fin)
    vi = validate_inventory(df_inv)
    print(f"[OK] sample_orders.csv: valid ({len(vo)} rows)")
    print(f"[OK] sample_financials.csv: valid ({len(vf)} rows)")
    print(f"[OK] sample_inventory.csv: valid ({len(vi)} rows)")

    print("\n" + "=" * 60)
    print("2. CHECKING RELIABILITY METRICS & INVARIANTS")
    print("=" * 60)
    rel = ReliabilityMetrics(
        data=df_orders,
        order_id_col="so_number",
        promised_date_col="promised_delivery_date",
        actual_date_col="actual_delivery_date",
        ordered_qty_col="qty_ordered",
        delivered_qty_col="qty_delivered",
        damaged_flag_col="is_damaged",
        doc_accurate_col="is_doc_complete",
        on_time_grace_days=0,
        in_full_tolerance=0.0,
    )
    summary = rel.evaluate_all()
    print("Summary:", summary)

    # Invariant verification
    pof = summary["Perfect_Order_Fulfillment"]
    otif = summary["OTIF_rate"]
    on_time = summary["On_Time_rate"]
    in_full = summary["In_Full_rate"]
    assert pof <= otif <= min(on_time, in_full), f"Invariant violated: {pof} <= {otif} <= min({on_time}, {in_full})"
    print(f"[OK] SCOR Invariant Holds: POF ({pof}) <= OTIF ({otif}) <= min(On-Time: {on_time}, In-Full: {in_full})")

    by_customer = rel.evaluate_all(group_by="customer_segment")
    assert isinstance(by_customer, pd.DataFrame)
    print(f"[OK] Customer Segmentation: {list(by_customer.index)}")

    print("\n" + "=" * 60)
    print("3. CHECKING ASSET EFFICIENCY & GOLDEN TEST")
    print("=" * 60)
    assets = AssetMetrics(
        annual_cogs=15_000_000_000,
        annual_revenue=22_500_000_000,
        avg_inventory_value=2_100_000_000,
        accounts_receivable=1_800_000_000,
        accounts_payable=1_400_000_000,
        days_in_year=365,
    )
    c2c = assets.cash_to_cash_cycle()
    print(f"IDS: {c2c['IDS']:.1f} hari (Expected: 51.1)")
    print(f"DSO: {c2c['DSO']:.1f} hari (Expected: 29.2)")
    print(f"DPO: {c2c['DPO']:.1f} hari (Expected: 34.1)")
    print(f"C2C: {c2c['C2C_days']:.1f} hari (Expected: 46.2)")
    assert c2c["IDS"] == 51.1
    assert c2c["DSO"] == 29.2
    assert c2c["DPO"] == 34.1
    assert c2c["C2C_days"] == 46.2
    print("[OK] Golden test verified perfectly!")

    print("\n" + "=" * 60)
    print("4. CHECKING RESPONSIVENESS (OFCT)")
    print("=" * 60)
    resp = ResponsivenessMetrics(df_orders)
    ofct = resp.order_fulfillment_cycle_time()
    print("OFCT stats:", ofct)
    assert ofct["mean_days"] > 0
    assert ofct["median_days"] > 0
    assert ofct["p90_days"] >= ofct["median_days"]
    print("[OK] OFCT statistics verified!")

    print("\n" + "=" * 60)
    print("5. CHECKING COST METRICS (CO.1.1)")
    print("=" * 60)
    cm = CostMetrics.from_dataframe(df_fin)
    cost_summary = cm.evaluate_all()
    print("SCM Cost % of Revenue:", cost_summary["scm_cost_pct_revenue"], "%")
    assert cost_summary["total_scm_cost"] > 0
    assert 0 < cost_summary["scm_cost_pct_revenue"] < 100
    print("[OK] SCM Cost metrics verified!")

    print("\n" + "=" * 60)
    print("6. CHECKING WHAT-IF SIMULATOR & SAFETY STOCK TRADEOFF")
    print("=" * 60)
    sim = SupplyChainSimulator.from_orders(df_orders, seed=42)
    sim_res = sim.run(n_runs=1000, scenario={"supplier_lead_time_shift_days": 3})
    comp = sim_res.compare_to_baseline("OTIF_rate")
    print("Simulated OTIF Comparison:", comp)
    assert comp["ci_95_lower"] <= comp["scenario_mean"] <= comp["ci_95_upper"]
    print("[OK] Monte Carlo confidence intervals verified!")

    # Safety stock tradeoff
    ss_calc = SupplyChainSimulator.simulate_safety_stock_adjustment(
        avg_inventory_value=2_100_000_000,
        annual_cogs=15_000_000_000,
        annual_revenue=22_500_000_000,
        accounts_receivable=1_800_000_000,
        accounts_payable=1_400_000_000,
        safety_stock_pct_of_inventory=0.40,
        safety_stock_change_pct=-0.15,
        days_in_year=365,
    )
    print("Working capital freed:", ss_calc["working_capital_freed"], "IDR")
    print("Delta IDS:", ss_calc["delta_IDS_days"], "days")
    assert ss_calc["working_capital_freed"] == 126_000_000.0
    assert ss_calc["delta_IDS_days"] == -3.1
    print("[OK] Safety stock trade-off formula verified!")

    print("\n" + "=" * 60)
    print("7. CHECKING PLOTLY DASHBOARD COMPONENTS")
    print("=" * 60)
    g_fig = create_gauge_chart(0.85, "Test Gauge")
    w_fig = create_c2c_waterfall(51.1, 29.2, 34.1)
    s_fig = create_delivery_sankey(df_orders)
    assert g_fig is not None and w_fig is not None and s_fig is not None
    print("[OK] Gauge, Waterfall, and Sankey visual components generated successfully!")

    print("\n" + "=" * 60)
    print("ALL VERIFICATION CHECKS PASSED WITH ZERO ERRORS!")
    print("=" * 60)

if __name__ == "__main__":
    verify_all()
