"""Unit tests for scorpy.asset_efficiency including SCOR golden tests."""

import pandas as pd
import pytest

from scorpy.asset_efficiency import AssetMetrics


def test_golden_c2c_calculation():
    """Verify exact values specified in the SCOR-Py documentation."""
    assets = AssetMetrics(
        annual_cogs=15_000_000_000,
        annual_revenue=22_500_000_000,
        avg_inventory_value=2_100_000_000,
        accounts_receivable=1_800_000_000,
        accounts_payable=1_400_000_000,
        days_in_year=365,
    )

    c2c = assets.cash_to_cash_cycle()
    assert c2c["IDS"] == 51.1
    assert c2c["DSO"] == 29.2
    assert c2c["DPO"] == 34.1
    assert c2c["C2C_days"] == 46.2


def test_c2c_custom_days_in_year():
    """Verify 360-day accounting year configuration."""
    assets = AssetMetrics(
        annual_cogs=10_000_000,
        annual_revenue=20_000_000,
        avg_inventory_value=1_000_000,
        accounts_receivable=2_000_000,
        accounts_payable=1_000_000,
        days_in_year=360,
    )
    # IDS = 1M/10M * 360 = 36.0
    # DSO = 2M/20M * 360 = 36.0
    # DPO = 1M/10M * 360 = 36.0
    # C2C = 36 + 36 - 36 = 36.0
    c2c = assets.cash_to_cash_cycle()
    assert c2c["IDS"] == 36.0
    assert c2c["DSO"] == 36.0
    assert c2c["DPO"] == 36.0
    assert c2c["C2C_days"] == 36.0


def test_custom_purchases_for_dpo():
    assets = AssetMetrics(
        annual_cogs=10_000_000,
        annual_revenue=20_000_000,
        avg_inventory_value=1_000_000,
        accounts_receivable=1_000_000,
        accounts_payable=2_000_000,
        annual_purchases=8_000_000,
        days_in_year=365,
    )
    # DPO calculated against 8M instead of 10M
    # DPO = 2M / 8M * 365 = 91.25
    assert round(assets.days_payable_outstanding(), 1) == 91.2


def test_return_on_fixed_assets_and_working_capital():
    assets = AssetMetrics(
        annual_cogs=10_000_000,
        annual_revenue=15_000_000,
        avg_inventory_value=2_000_000,
        accounts_receivable=1_500_000,
        accounts_payable=1_000_000,
        scm_cost=1_000_000,
        sc_fixed_assets=4_000_000,
    )
    # Operating Income SC = 15M - 10M - 1M = 4M
    # AM.1.2 = 4M / 4M = 1.0 (100%)
    rofa = assets.return_on_fixed_assets()
    assert rofa == 1.0

    # Working Capital = 2M + 1.5M - 1M = 2.5M
    # AM.1.3 = 4M / 2.5M = 1.6
    rowc = assets.return_on_working_capital()
    assert rowc == 1.6


def test_zero_cogs_raises_exception():
    with pytest.raises(ZeroDivisionError):
        AssetMetrics(
            annual_cogs=0,
            annual_revenue=10_000,
            avg_inventory_value=1_000,
            accounts_receivable=1_000,
            accounts_payable=1_000,
        )


def test_from_dataframes():
    df_fin = pd.DataFrame(
        {
            "period": ["2025-01", "2025-02"],
            "revenue": [10_000_000, 10_000_000],
            "cogs": [5_000_000, 5_000_000],
            "accounts_receivable": [2_000_000, 2_000_000],
            "accounts_payable": [1_000_000, 1_000_000],
            "sc_fixed_assets": [4_000_000, 4_000_000],
            "transport_cost": [100_000, 100_000],
            "warehousing_cost": [50_000, 50_000],
        }
    )
    df_inv = pd.DataFrame(
        {
            "date": ["2025-01-01", "2025-01-02"],
            "inventory_value": [1_000_000, 1_000_000],
        }
    )
    assets = AssetMetrics.from_dataframes(
        df_financials=df_fin,
        df_inventory=df_inv,
        scm_cost_cols=["transport_cost", "warehousing_cost"],
    )
    assert assets.annual_revenue == 20_000_000
    assert assets.annual_cogs == 10_000_000
    assert assets.avg_inventory_value == 1_000_000
    assert assets.scm_cost == 300_000

    summary = assets.evaluate_all()
    assert "return_on_sc_fixed_assets" in summary
    assert "return_on_working_capital" in summary
    assert summary["IDS"] > 0
    assert summary["DSO"] > 0
    assert summary["DPO"] > 0
