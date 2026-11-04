"""Unit tests for scorpy.export utilities."""

import json

import pandas as pd

from scorpy.export import (
    export_to_excel,
    export_to_json,
    generate_unified_scorecard,
)


def test_generate_unified_scorecard():
    df_orders = pd.read_csv("data/sample_orders.csv")
    df_fin = pd.read_csv("data/sample_financials.csv")
    df_inv = pd.read_csv("data/sample_inventory.csv")

    sc = generate_unified_scorecard(df_orders, df_fin, df_inv)
    assert "reliability" in sc
    assert "responsiveness" in sc
    assert "cost" in sc
    assert "asset_efficiency" in sc
    assert sc["reliability"]["Total_Orders_Evaluated"] == 1200


def test_export_to_json_and_excel(tmp_path):
    df_orders = pd.read_csv("data/sample_orders.csv")
    df_fin = pd.read_csv("data/sample_financials.csv")
    sc = generate_unified_scorecard(df_orders, df_fin)

    # Test JSON export
    json_file = tmp_path / "scorecard.json"
    export_to_json(sc, json_file)
    assert json_file.exists()

    with open(json_file, "r") as f:
        loaded = json.load(f)
    assert loaded["reliability"]["Total_Orders_Evaluated"] == 1200

    # Test Excel export
    excel_file = tmp_path / "scorecard.xlsx"
    export_to_excel(sc, excel_file)
    assert excel_file.exists()
    assert excel_file.stat().st_size > 0
