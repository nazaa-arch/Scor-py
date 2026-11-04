"""Unit tests for scorpy.cost."""

import pandas as pd
import pytest

from scorpy.cost import CostMetrics


def test_cost_metrics_calculation():
    cm = CostMetrics(
        revenue=100_000_000,
        transport_cost=4_000_000,
        warehousing_cost=3_000_000,
        procurement_cost=2_000_000,
        return_cost=1_000_000,
    )
    # Total SCM Cost = 4M + 3M + 2M + 1M = 10M
    assert cm.total_scm_cost() == 10_000_000
    # SCM Cost % = 10M / 100M * 100 = 10%
    assert cm.scm_cost_pct_revenue() == 10.0

    breakdown = cm.cost_breakdown()
    # Transport is 4M / 10M = 40% of SCM Cost, and 4% of revenue
    assert breakdown["transportation"]["pct_of_scm_cost"] == 40.0
    assert breakdown["transportation"]["pct_of_revenue"] == 4.0
    assert breakdown["warehousing"]["pct_of_scm_cost"] == 30.0


def test_cost_from_dataframe():
    df = pd.DataFrame(
        {
            "period": ["2025-01", "2025-02"],
            "revenue": [50_000_000, 50_000_000],
            "transport_cost": [2_000_000, 2_000_000],
            "warehousing_cost": [1_500_000, 1_500_000],
            "procurement_cost": [1_000_000, 1_000_000],
            "return_cost": [500_000, 500_000],
        }
    )
    cm = CostMetrics.from_dataframe(df)
    assert cm.revenue == 100_000_000
    assert cm.total_scm_cost() == 10_000_000
    assert cm.scm_cost_pct_revenue() == 10.0


def test_periodic_trend():
    df = pd.DataFrame(
        {
            "period": ["2025-01", "2025-02"],
            "revenue": [100_000, 200_000],
            "transport_cost": [4_000, 8_000],
            "warehousing_cost": [3_000, 6_000],
            "procurement_cost": [2_000, 4_000],
            "return_cost": [1_000, 2_000],
        }
    )
    trend = CostMetrics.periodic_trend(df)
    assert "total_scm_cost" in trend.columns
    assert "scm_cost_pct" in trend.columns
    assert trend.loc[0, "total_scm_cost"] == 10_000
    assert trend.loc[0, "scm_cost_pct"] == 10.0
    assert trend.loc[1, "total_scm_cost"] == 20_000
    assert trend.loc[1, "scm_cost_pct"] == 10.0


def test_zero_revenue_raises():
    with pytest.raises(ZeroDivisionError):
        CostMetrics(revenue=0)
