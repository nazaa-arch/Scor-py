"""Unit tests for scorpy.root_cause Pareto analysis."""

import pandas as pd
from scorpy.root_cause import pareto_failure_analysis


def test_pareto_failure_analysis():
    df = pd.DataFrame(
        {
            "order_date": ["2025-01-01"] * 5,
            "promised_delivery_date": ["2025-01-05"] * 5,
            "actual_delivery_date": [
                "2025-01-04",
                "2025-01-06",
                "2025-01-07",
                "2025-01-04",
                "2025-01-04",
            ],
            "qty_ordered": [100] * 5,
            "qty_delivered": [100, 100, 80, 100, 100],  # row 3 is short
            "is_damaged": [False, False, False, True, False],  # row 4 is damaged
            "is_doc_complete": [True, True, True, True, False],  # row 5 is missing doc
            "delay_reason": ["None", "Carrier Delay", "Warehouse Delay", "None", "None"],
        }
    )

    pareto_df = pareto_failure_analysis(df)
    assert len(pareto_df) >= 3
    assert "failure_mode" in pareto_df.columns
    assert "failure_count" in pareto_df.columns
    assert "cumulative_pct" in pareto_df.columns
    assert "is_vital_few" in pareto_df.columns
    assert pareto_df["cumulative_pct"].iloc[-1] == 100.0


def test_pareto_zero_defects():
    df = pd.DataFrame(
        {
            "order_date": ["2025-01-01"],
            "promised_delivery_date": ["2025-01-05"],
            "actual_delivery_date": ["2025-01-04"],
            "qty_ordered": [100],
            "qty_delivered": [100],
            "is_damaged": [False],
            "is_doc_complete": [True],
        }
    )
    pareto_df = pareto_failure_analysis(df)
    assert len(pareto_df) == 1
    assert "Zero Defects" in pareto_df.loc[0, "failure_mode"]


def test_pareto_empty():
    df = pd.DataFrame(
        {
            "order_date": [],
            "promised_delivery_date": [],
            "actual_delivery_date": [],
            "qty_ordered": [],
            "qty_delivered": [],
            "is_damaged": [],
            "is_doc_complete": [],
        }
    )
    pareto_df = pareto_failure_analysis(df)
    assert len(pareto_df) == 0
