"""Stress tests and boundary condition edge cases for SCOR-Py."""

import numpy as np
import pandas as pd

from scorpy.asset_efficiency import AssetMetrics
from scorpy.reliability import ReliabilityMetrics
from scorpy.responsiveness import ResponsivenessMetrics


def test_zero_day_lead_time_orders():
    """Same-day order and delivery should evaluate to 0 days OFCT and On-Time."""
    df = pd.DataFrame(
        {
            "so_number": ["SO-SAME-1", "SO-SAME-2"],
            "order_date": ["2025-05-01", "2025-05-02"],
            "promised_delivery_date": ["2025-05-01", "2025-05-02"],
            "actual_delivery_date": ["2025-05-01", "2025-05-02"],
            "qty_ordered": [50, 100],
            "qty_delivered": [50, 100],
            "is_damaged": [False, False],
            "is_doc_complete": [True, True],
        }
    )
    rel = ReliabilityMetrics(df)
    resp = ResponsivenessMetrics(df)

    assert rel.on_time_rate() == 1.0
    assert rel.perfect_order_fulfillment() == 1.0

    ofct = resp.order_fulfillment_cycle_time()
    assert ofct["mean_days"] == 0.0
    assert ofct["min_days"] == 0.0


def test_leap_year_handling():
    """Verify leap day (Feb 29) date arithmetic."""
    df = pd.DataFrame(
        {
            "so_number": ["SO-LEAP"],
            "order_date": ["2024-02-28"],
            "promised_delivery_date": ["2024-03-01"],
            "actual_delivery_date": ["2024-02-29"],
            "qty_ordered": [100],
            "qty_delivered": [100],
            "is_damaged": [False],
            "is_doc_complete": [True],
        }
    )
    rel = ReliabilityMetrics(df)
    resp = ResponsivenessMetrics(df)

    assert rel.on_time_rate() == 1.0
    ofct = resp.order_fulfillment_cycle_time()
    assert ofct["mean_days"] == 1.0


def test_large_dataset_throughput():
    """Stress test with 10,000 synthetic orders."""
    n = 10_000
    base = pd.Timestamp("2025-01-01")
    offsets = np.random.randint(0, 300, size=n)
    leads = np.random.randint(2, 8, size=n)

    ods = [base + pd.Timedelta(days=int(off)) for off in offsets]
    pds = [od + pd.Timedelta(days=int(ld)) for od, ld in zip(ods, leads, strict=False)]
    ads = [pd_d + pd.Timedelta(days=1) for pd_d in pds]

    df = pd.DataFrame(
        {
            "so_number": [f"SO-{i}" for i in range(n)],
            "order_date": ods,
            "promised_delivery_date": pds,
            "actual_delivery_date": ads,
            "qty_ordered": [100] * n,
            "qty_delivered": [100] * n,
            "is_damaged": [False] * n,
            "is_doc_complete": [True] * n,
        }
    )

    rel = ReliabilityMetrics(df, validate=False)
    summary = rel.evaluate_all()
    assert summary["Total_Orders_Evaluated"] == n


def test_extreme_financial_values():
    """Test scaling with enterprise multi-trillion IDR numbers."""
    assets = AssetMetrics(
        annual_cogs=1_500_000_000_000,  # 1.5 Trillion
        annual_revenue=2_500_000_000_000,  # 2.5 Trillion
        avg_inventory_value=200_000_000_000,  # 200 Billion
        accounts_receivable=150_000_000_000,
        accounts_payable=120_000_000_000,
        days_in_year=365,
    )
    c2c = assets.cash_to_cash_cycle()
    assert c2c["C2C_days"] > 0
    assert c2c["IDS"] > 0
