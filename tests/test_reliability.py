"""Unit tests for scorpy.reliability."""

import pandas as pd
import pytest

from scorpy.reliability import ReliabilityMetrics


@pytest.fixture
def sample_orders_df():
    return pd.DataFrame(
        {
            "so_number": ["SO-1", "SO-2", "SO-3", "SO-4"],
            "order_date": ["2025-01-01", "2025-01-01", "2025-01-02", "2025-01-02"],
            "promised_delivery_date": ["2025-01-05", "2025-01-05", "2025-01-06", "2025-01-06"],
            "actual_delivery_date": ["2025-01-04", "2025-01-06", "2025-01-05", "2025-01-06"],
            "qty_ordered": [100, 100, 100, 100],
            "qty_delivered": [100, 80, 100, 100],
            "is_damaged": [False, False, True, False],
            "is_doc_complete": [True, True, True, False],
            "customer_segment": ["Enterprise", "Retail", "Enterprise", "Retail"],
        }
    )


def test_perfect_order_conditions(sample_orders_df):
    rel = ReliabilityMetrics(sample_orders_df, validate=True)
    summary = rel.evaluate_all()

    # SO-1: on-time (Jan 4 <= Jan 5), full (100>=100), undamaged, doc complete -> PERFECT
    # SO-2: late (Jan 6 > Jan 5), short (80 < 100), undamaged, doc complete -> FAILED
    # SO-3: on-time (Jan 5 <= Jan 6), full (100>=100), DAMAGED, doc complete -> FAILED
    # SO-4: on-time (Jan 6 <= Jan 6), full (100>=100), undamaged, DOC INCOMPLETE -> FAILED

    assert summary["Total_Orders_Evaluated"] == 4
    # On-time: SO-1, SO-3, SO-4 -> 3/4 = 0.75
    assert summary["On_Time_rate"] == 0.75
    # In-full: SO-1, SO-3, SO-4 -> 3/4 = 0.75
    assert summary["In_Full_rate"] == 0.75
    # OTIF: SO-1 (on-time & full), SO-3 (on-time & full), SO-4 (on-time & full) -> 3/4 = 0.75
    assert summary["OTIF_rate"] == 0.75
    # Damage-free: SO-1, SO-2, SO-4 -> 3/4 = 0.75
    assert summary["Damage_Free_rate"] == 0.75
    # Doc-accurate: SO-1, SO-2, SO-3 -> 3/4 = 0.75
    assert summary["Doc_Accurate_rate"] == 0.75
    # Perfect order: Only SO-1 -> 1/4 = 0.25
    assert summary["Perfect_Order_Fulfillment"] == 0.25


def test_on_time_grace_days(sample_orders_df):
    # SO-2 is late by 1 day (actual Jan 6 vs promised Jan 5)
    # With grace_days=1, SO-2 becomes on-time
    rel = ReliabilityMetrics(sample_orders_df, on_time_grace_days=1, validate=True)
    summary = rel.evaluate_all()
    assert summary["On_Time_rate"] == 1.0  # All 4 on-time


def test_in_full_tolerance(sample_orders_df):
    # SO-2 delivered 80 out of 100 (20% short)
    # With tolerance=0.20, SO-2 becomes in-full
    rel = ReliabilityMetrics(sample_orders_df, in_full_tolerance=0.20, validate=True)
    summary = rel.evaluate_all()
    assert summary["In_Full_rate"] == 1.0


def test_surplus_delivery():
    df = pd.DataFrame(
        {
            "so_number": ["SO-1"],
            "order_date": ["2025-01-01"],
            "promised_delivery_date": ["2025-01-05"],
            "actual_delivery_date": ["2025-01-04"],
            "qty_ordered": [100],
            "qty_delivered": [110],  # Over-delivery is counted as In-Full
            "is_damaged": [False],
            "is_doc_complete": [True],
        }
    )
    rel = ReliabilityMetrics(df, validate=True)
    assert rel.in_full_rate() == 1.0
    assert rel.perfect_order_fulfillment() == 1.0


def test_unshipped_orders_handling():
    df = pd.DataFrame(
        {
            "so_number": ["SO-1", "SO-2"],
            "order_date": ["2025-01-01", "2025-01-01"],
            "promised_delivery_date": ["2025-01-05", "2025-01-05"],
            "actual_delivery_date": ["2025-01-04", None],  # SO-2 unshipped
            "qty_ordered": [100, 50],
            "qty_delivered": [100, 0],
            "is_damaged": [False, False],
            "is_doc_complete": [True, False],
        }
    )
    rel = ReliabilityMetrics(df, exclude_unshipped=True, validate=True)
    assert rel.unshipped_orders_count == 1
    summary = rel.evaluate_all()
    assert summary["Total_Orders_Evaluated"] == 1
    assert summary["Unshipped_Orders_Excluded"] == 1
    assert summary["Perfect_Order_Fulfillment"] == 1.0


def test_group_by_segment(sample_orders_df):
    rel = ReliabilityMetrics(sample_orders_df, validate=True)
    res = rel.evaluate_all(group_by="customer_segment")
    assert isinstance(res, pd.DataFrame)
    assert "Enterprise" in res.index
    assert "Retail" in res.index
    assert "Perfect_Order_Fulfillment" in res.columns

    # Test individual rate methods with group_by
    ot_grp = rel.on_time_rate(group_by="customer_segment")
    assert isinstance(ot_grp, pd.Series)
    assert "Enterprise" in ot_grp.index

    inf_grp = rel.in_full_rate(group_by="customer_segment")
    assert isinstance(inf_grp, pd.Series)

    otif_grp = rel.otif_rate(group_by="customer_segment")
    assert isinstance(otif_grp, pd.Series)

    df_grp = rel.damage_free_rate(group_by="customer_segment")
    assert isinstance(df_grp, pd.Series)

    doc_grp = rel.doc_accurate_rate(group_by="customer_segment")
    assert isinstance(doc_grp, pd.Series)

    pof_grp = rel.perfect_order_fulfillment(group_by="customer_segment")
    assert isinstance(pof_grp, pd.Series)


def test_invalid_group_by_raises(sample_orders_df):
    rel = ReliabilityMetrics(sample_orders_df, validate=True)
    with pytest.raises(KeyError):
        rel.evaluate_all(group_by="non_existent_column")
    with pytest.raises(KeyError):
        rel.on_time_rate(group_by="non_existent_column")
