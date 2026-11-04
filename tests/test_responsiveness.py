"""Unit tests for scorpy.responsiveness."""

import pandas as pd
import pytest

from scorpy.responsiveness import ResponsivenessMetrics


@pytest.fixture
def sample_orders_df():
    return pd.DataFrame(
        {
            "order_date": ["2025-01-01", "2025-01-01", "2025-01-02", "2025-01-02"],
            "promised_delivery_date": ["2025-01-05", "2025-01-05", "2025-01-07", "2025-01-08"],
            "actual_delivery_date": ["2025-01-04", "2025-01-07", "2025-01-06", "2025-01-12"],
            # Cycle times: 3 days, 6 days, 4 days, 10 days
            "customer_segment": ["Enterprise", "Retail", "Enterprise", "Retail"],
        }
    )


def test_order_fulfillment_cycle_time(sample_orders_df):
    resp = ResponsivenessMetrics(sample_orders_df)
    stats = resp.order_fulfillment_cycle_time()

    # Cycle times: [3, 6, 4, 10]
    # Mean: (3+6+4+10)/4 = 23/4 = 5.75
    # Median: (4+6)/2 = 5.0
    # Min: 3.0, Max: 10.0
    assert stats["mean_days"] == 5.75
    assert stats["median_days"] == 5.0
    assert stats["min_days"] == 3.0
    assert stats["max_days"] == 10.0
    assert stats["p90_days"] > 5.0


def test_ofct_group_by(sample_orders_df):
    resp = ResponsivenessMetrics(sample_orders_df)
    res = resp.order_fulfillment_cycle_time(group_by="customer_segment")
    assert isinstance(res, pd.DataFrame)
    # Enterprise: [3, 4] -> mean = 3.5
    assert res.loc["Enterprise", "mean_days"] == 3.5
    # Retail: [6, 10] -> mean = 8.0
    assert res.loc["Retail", "mean_days"] == 8.0


def test_multi_stage_cycle_time():
    df = pd.DataFrame(
        {
            "order_date": ["2025-01-01", "2025-01-01"],
            "actual_delivery_date": ["2025-01-10", "2025-01-12"],
            "t_source": [2, 3],
            "t_make": [4, 5],
            "t_deliver": [1, 2],
        }
    )
    resp = ResponsivenessMetrics(
        df,
        source_cycle_col="t_source",
        make_cycle_col="t_make",
        deliver_cycle_col="t_deliver",
    )
    stats = resp.order_fulfillment_cycle_time()
    # Row 1: 2+4+1 = 7 days
    # Row 2: 3+5+2 = 10 days
    # Mean: 8.5
    assert stats["mean_days"] == 8.5


def test_lead_time_variance(sample_orders_df):
    resp = ResponsivenessMetrics(sample_orders_df)
    var = resp.lead_time_variance()
    # Actual - Promised:
    # Row 1: Jan 4 - Jan 5 = -1 (early)
    # Row 2: Jan 7 - Jan 5 = +2 (late)
    # Row 3: Jan 6 - Jan 7 = -1 (early)
    # Row 4: Jan 12 - Jan 8 = +4 (late)
    # Early/On-Time: 2 out of 4 = 50%
    # Delayed: 2 out of 4 = 50%
    assert var["pct_early_or_on_time"] == 0.50
    assert var["pct_delayed"] == 0.50
