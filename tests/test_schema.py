"""Unit tests for scorpy.schema validation."""

import pandas as pd
import pytest

from scorpy.schema import (
    SchemaValidationError,
    validate_financials,
    validate_inventory,
    validate_orders,
)


def test_valid_orders_pass():
    df = pd.DataFrame(
        {
            "so_number": ["SO-1", "SO-2"],
            "order_date": ["2025-01-01", "2025-01-02"],
            "promised_delivery_date": ["2025-01-05", "2025-01-06"],
            "actual_delivery_date": ["2025-01-04", "2025-01-07"],
            "qty_ordered": [10, 20],
            "qty_delivered": [10, 20],
            "is_damaged": [False, False],
            "is_doc_complete": [True, True],
        }
    )
    validated = validate_orders(df)
    assert len(validated) == 2


def test_reversed_dates_fail():
    # actual_delivery_date before order_date
    df = pd.DataFrame(
        {
            "so_number": ["SO-1"],
            "order_date": ["2025-01-05"],
            "promised_delivery_date": ["2025-01-06"],
            "actual_delivery_date": ["2025-01-02"],  # Invalid: actual < order
            "qty_ordered": [10],
            "qty_delivered": [10],
            "is_damaged": [False],
            "is_doc_complete": [True],
        }
    )
    with pytest.raises(SchemaValidationError):
        validate_orders(df)


def test_negative_quantity_fails():
    df = pd.DataFrame(
        {
            "so_number": ["SO-1"],
            "order_date": ["2025-01-01"],
            "promised_delivery_date": ["2025-01-05"],
            "actual_delivery_date": ["2025-01-04"],
            "qty_ordered": [-10],  # Invalid: negative
            "qty_delivered": [10],
            "is_damaged": [False],
            "is_doc_complete": [True],
        }
    )
    with pytest.raises(SchemaValidationError):
        validate_orders(df)


def test_duplicate_order_id_fails():
    df = pd.DataFrame(
        {
            "so_number": ["SO-1", "SO-1"],  # Duplicate ID
            "order_date": ["2025-01-01", "2025-01-02"],
            "promised_delivery_date": ["2025-01-05", "2025-01-06"],
            "actual_delivery_date": ["2025-01-04", "2025-01-05"],
            "qty_ordered": [10, 20],
            "qty_delivered": [10, 20],
            "is_damaged": [False, False],
            "is_doc_complete": [True, True],
        }
    )
    with pytest.raises(SchemaValidationError):
        validate_orders(df)


def test_valid_financials_pass():
    df = pd.DataFrame(
        {
            "period": ["2025-01"],
            "revenue": [1000.0],
            "cogs": [700.0],
            "accounts_receivable": [200.0],
            "accounts_payable": [150.0],
        }
    )
    validated = validate_financials(df)
    assert len(validated) == 1


def test_negative_financials_fail():
    df = pd.DataFrame(
        {
            "period": ["2025-01"],
            "revenue": [-1000.0],  # Invalid
            "cogs": [700.0],
            "accounts_receivable": [200.0],
            "accounts_payable": [150.0],
        }
    )
    with pytest.raises(SchemaValidationError):
        validate_financials(df)


def test_valid_inventory_pass():
    df = pd.DataFrame(
        {
            "date": ["2025-01-01"],
            "sku": ["SKU-1"],
            "on_hand_qty": [100],
            "unit_cost": [50.0],
        }
    )
    validated = validate_inventory(df)
    assert len(validated) == 1


def test_invalid_inventory_fail():
    df = pd.DataFrame(
        {
            "date": ["2025-01-01"],
            "sku": ["SKU-1"],
            "on_hand_qty": [-5],  # Negative
            "unit_cost": [50.0],
        }
    )
    with pytest.raises(SchemaValidationError):
        validate_inventory(df)


def test_empty_dataframe_raises():
    with pytest.raises(SchemaValidationError):
        validate_orders(pd.DataFrame())
    with pytest.raises(SchemaValidationError):
        validate_financials(pd.DataFrame())
    with pytest.raises(SchemaValidationError):
        validate_inventory(pd.DataFrame())
