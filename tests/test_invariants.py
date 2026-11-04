"""Property-based invariant testing for SCOR-Py using Hypothesis."""

import pandas as pd
from hypothesis import given, settings
from hypothesis import strategies as st

from scorpy.reliability import ReliabilityMetrics


# Strategy to generate valid order records
@st.composite
def orders_dataframe_strategy(draw):
    n_rows = draw(st.integers(min_value=1, max_value=50))
    base_date = pd.Timestamp("2025-01-01")

    order_offsets = draw(
        st.lists(st.integers(min_value=0, max_value=100), min_size=n_rows, max_size=n_rows)
    )
    promised_lead = draw(
        st.lists(st.integers(min_value=1, max_value=20), min_size=n_rows, max_size=n_rows)
    )
    actual_lead = draw(
        st.lists(st.integers(min_value=0, max_value=30), min_size=n_rows, max_size=n_rows)
    )
    qty_ordered = draw(
        st.lists(st.integers(min_value=1, max_value=500), min_size=n_rows, max_size=n_rows)
    )
    qty_delivered = draw(
        st.lists(st.integers(min_value=0, max_value=600), min_size=n_rows, max_size=n_rows)
    )
    is_damaged = draw(st.lists(st.booleans(), min_size=n_rows, max_size=n_rows))
    is_doc_complete = draw(st.lists(st.booleans(), min_size=n_rows, max_size=n_rows))

    records = []
    for i in range(n_rows):
        od = base_date + pd.Timedelta(days=order_offsets[i])
        pd_date = od + pd.Timedelta(days=promised_lead[i])
        ad_date = od + pd.Timedelta(days=actual_lead[i])

        records.append(
            {
                "so_number": f"SO-{i + 1}",
                "order_date": od,
                "promised_delivery_date": pd_date,
                "actual_delivery_date": ad_date,
                "qty_ordered": qty_ordered[i],
                "qty_delivered": qty_delivered[i],
                "is_damaged": is_damaged[i],
                "is_doc_complete": is_doc_complete[i],
            }
        )

    return pd.DataFrame(records)


@settings(max_examples=50, deadline=None)
@given(df=orders_dataframe_strategy())
def test_scor_reliability_invariants(df):
    """Property Invariant:
    POF <= OTIF <= min(On-Time, In-Full), and all rates in [0.0, 1.0].
    """
    rel = ReliabilityMetrics(df, validate=False)
    summary = rel.evaluate_all()

    pof = summary["Perfect_Order_Fulfillment"]
    otif = summary["OTIF_rate"]
    on_time = summary["On_Time_rate"]
    in_full = summary["In_Full_rate"]
    damage_free = summary["Damage_Free_rate"]
    doc_accurate = summary["Doc_Accurate_rate"]

    # All rates within [0, 1]
    for r in [pof, otif, on_time, in_full, damage_free, doc_accurate]:
        assert 0.0 <= r <= 1.0 + 1e-6

    # Invariant: POF <= OTIF
    assert pof <= otif + 1e-6

    # Invariant: OTIF <= min(On-Time, In-Full)
    assert otif <= min(on_time, in_full) + 1e-6

    # Invariant: POF <= min(On-Time, In-Full, Damage-Free, Doc-Accurate)
    assert pof <= min(on_time, in_full, damage_free, doc_accurate) + 1e-6


@settings(max_examples=30, deadline=None)
@given(df=orders_dataframe_strategy())
def test_permutation_invariance(df):
    """Property: Row order does not affect aggregate metric values."""
    rel_orig = ReliabilityMetrics(df, validate=False)
    summary_orig = rel_orig.evaluate_all()

    # Shuffle DataFrame
    shuffled_df = df.sample(frac=1.0, random_state=123).reset_index(drop=True)
    rel_shuffled = ReliabilityMetrics(shuffled_df, validate=False)
    summary_shuffled = rel_shuffled.evaluate_all()

    for k in [
        "On_Time_rate",
        "In_Full_rate",
        "OTIF_rate",
        "Damage_Free_rate",
        "Doc_Accurate_rate",
        "Perfect_Order_Fulfillment",
    ]:
        assert abs(summary_orig[k] - summary_shuffled[k]) < 1e-4


@settings(max_examples=30, deadline=None)
@given(
    df=orders_dataframe_strategy(),
    g1=st.integers(min_value=0, max_value=5),
    g2=st.integers(min_value=0, max_value=5),
)
def test_grace_days_monotonicity(df, g1, g2):
    """Property: Increasing grace days monotonically increases or maintains On-Time rate."""
    grace_low = min(g1, g2)
    grace_high = max(g1, g2)

    rel_low = ReliabilityMetrics(df, on_time_grace_days=grace_low, validate=False)
    rel_high = ReliabilityMetrics(df, on_time_grace_days=grace_high, validate=False)

    assert rel_low.on_time_rate() <= rel_high.on_time_rate() + 1e-6


@settings(max_examples=30, deadline=None)
@given(
    df=orders_dataframe_strategy(),
    t1=st.floats(min_value=0.0, max_value=0.3),
    t2=st.floats(min_value=0.0, max_value=0.3),
)
def test_in_full_tolerance_monotonicity(df, t1, t2):
    """Property: Increasing in-full tolerance monotonically increases or maintains In-Full rate."""
    tol_low = min(t1, t2)
    tol_high = max(t1, t2)

    rel_low = ReliabilityMetrics(df, in_full_tolerance=tol_low, validate=False)
    rel_high = ReliabilityMetrics(df, in_full_tolerance=tol_high, validate=False)

    assert rel_low.in_full_rate() <= rel_high.in_full_rate() + 1e-6
