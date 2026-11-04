"""Schema validation module for SCOR-Py using Pandera.

Provides fail-fast validation for supply chain transaction logs, financial records,
and inventory levels.
"""

import pandas as pd

try:
    from pandera.pandas import Check, Column, DataFrameSchema, errors
except (ImportError, AttributeError):
    from pandera import Check, Column, DataFrameSchema, errors


class SchemaValidationError(ValueError):
    """Custom exception raised when input DataFrame fails SCOR-Py validation rules."""

    pass


def build_orders_schema(
    order_id_col: str = "so_number",
    order_date_col: str = "order_date",
    promised_date_col: str = "promised_delivery_date",
    actual_date_col: str = "actual_delivery_date",
    ordered_qty_col: str = "qty_ordered",
    delivered_qty_col: str = "qty_delivered",
    damaged_flag_col: str = "is_damaged",
    doc_accurate_col: str = "is_doc_complete",
    allow_unshipped: bool = True,
) -> DataFrameSchema:
    """Build a Pandera DataFrameSchema for validating order & delivery logs.

    Parameters
    ----------
    order_id_col : str
        Column name for unique sales order ID.
    order_date_col : str
        Column name for order placement date.
    promised_date_col : str
        Column name for promised delivery date.
    actual_date_col : str
        Column name for actual delivery date.
    ordered_qty_col : str
        Column name for ordered quantity.
    delivered_qty_col : str
        Column name for delivered quantity.
    damaged_flag_col : str
        Column name for damage boolean flag.
    doc_accurate_col : str
        Column name for documentation completeness boolean flag.
    allow_unshipped : bool
        If True, actual_delivery_date may be null for unshipped orders.

    Returns
    -------
    DataFrameSchema
    """
    dataframe_checks = []

    # Cross-column check: promised date >= order date (when both non-null)
    def check_promised_ge_order(df: pd.DataFrame) -> bool:
        mask = df[order_date_col].notna() & df[promised_date_col].notna()
        return bool((df.loc[mask, promised_date_col] >= df.loc[mask, order_date_col]).all())

    # Cross-column check: actual delivery date >= order date (when both non-null)
    def check_actual_ge_order(df: pd.DataFrame) -> bool:
        mask = df[order_date_col].notna() & df[actual_date_col].notna()
        return bool((df.loc[mask, actual_date_col] >= df.loc[mask, order_date_col]).all())

    dataframe_checks.append(
        Check(
            check_promised_ge_order,
            error=f"'{promised_date_col}' must be greater than or equal to '{order_date_col}'.",
        )
    )
    dataframe_checks.append(
        Check(
            check_actual_ge_order,
            error=f"'{actual_date_col}' must be greater than or equal to '{order_date_col}'.",
        )
    )

    schema = DataFrameSchema(
        columns={
            order_id_col: Column(
                checks=[
                    Check(lambda s: s.nunique() == len(s), error=f"'{order_id_col}' must be unique")
                ],
                nullable=False,
                coerce=True,
            ),
            order_date_col: Column(
                dtype="datetime64[ns]",
                nullable=False,
                coerce=True,
            ),
            promised_date_col: Column(
                dtype="datetime64[ns]",
                nullable=False,
                coerce=True,
            ),
            actual_date_col: Column(
                dtype="datetime64[ns]",
                nullable=allow_unshipped,
                coerce=True,
            ),
            ordered_qty_col: Column(
                checks=[Check.gt(0, error=f"'{ordered_qty_col}' must be strictly positive (> 0)")],
                nullable=False,
                coerce=True,
            ),
            delivered_qty_col: Column(
                checks=[Check.ge(0, error=f"'{delivered_qty_col}' must be non-negative (>= 0)")],
                nullable=False,
                coerce=True,
            ),
            damaged_flag_col: Column(
                dtype=bool,
                nullable=False,
                coerce=True,
            ),
            doc_accurate_col: Column(
                dtype=bool,
                nullable=False,
                coerce=True,
            ),
        },
        checks=dataframe_checks,
        coerce=True,
    )
    return schema


def validate_orders(
    df: pd.DataFrame,
    order_id_col: str = "so_number",
    order_date_col: str = "order_date",
    promised_date_col: str = "promised_delivery_date",
    actual_date_col: str = "actual_delivery_date",
    ordered_qty_col: str = "qty_ordered",
    delivered_qty_col: str = "qty_delivered",
    damaged_flag_col: str = "is_damaged",
    doc_accurate_col: str = "is_doc_complete",
    allow_unshipped: bool = True,
) -> pd.DataFrame:
    """Validate and coerce orders DataFrame according to SCOR-Py schema rules.

    Raises SchemaValidationError if invalid.
    """
    if df is None or len(df) == 0:
        raise SchemaValidationError("Input orders DataFrame is empty or None.")

    schema = build_orders_schema(
        order_id_col=order_id_col,
        order_date_col=order_date_col,
        promised_date_col=promised_date_col,
        actual_date_col=actual_date_col,
        ordered_qty_col=ordered_qty_col,
        delivered_qty_col=delivered_qty_col,
        damaged_flag_col=damaged_flag_col,
        doc_accurate_col=doc_accurate_col,
        allow_unshipped=allow_unshipped,
    )
    try:
        return schema.validate(df)
    except (errors.SchemaError, errors.SchemaErrors) as e:
        raise SchemaValidationError(f"Orders data validation failed: {str(e)}") from e


def build_financials_schema(
    period_col: str = "period",
    revenue_col: str = "revenue",
    cogs_col: str = "cogs",
    ar_col: str = "accounts_receivable",
    ap_col: str = "accounts_payable",
) -> DataFrameSchema:
    """Build DataFrameSchema for validating monthly/periodic financials."""
    return DataFrameSchema(
        columns={
            period_col: Column(nullable=False, coerce=True),
            revenue_col: Column(
                checks=[Check.ge(0, error=f"'{revenue_col}' must be >= 0")],
                nullable=False,
                coerce=True,
            ),
            cogs_col: Column(
                checks=[Check.ge(0, error=f"'{cogs_col}' must be >= 0")],
                nullable=False,
                coerce=True,
            ),
            ar_col: Column(
                checks=[Check.ge(0, error=f"'{ar_col}' must be >= 0")],
                nullable=False,
                coerce=True,
            ),
            ap_col: Column(
                checks=[Check.ge(0, error=f"'{ap_col}' must be >= 0")],
                nullable=False,
                coerce=True,
            ),
        },
        coerce=True,
    )


def validate_financials(
    df: pd.DataFrame,
    period_col: str = "period",
    revenue_col: str = "revenue",
    cogs_col: str = "cogs",
    ar_col: str = "accounts_receivable",
    ap_col: str = "accounts_payable",
) -> pd.DataFrame:
    """Validate and coerce financials DataFrame."""
    if df is None or len(df) == 0:
        raise SchemaValidationError("Input financials DataFrame is empty or None.")

    schema = build_financials_schema(
        period_col=period_col,
        revenue_col=revenue_col,
        cogs_col=cogs_col,
        ar_col=ar_col,
        ap_col=ap_col,
    )
    try:
        return schema.validate(df)
    except (errors.SchemaError, errors.SchemaErrors) as e:
        raise SchemaValidationError(f"Financials data validation failed: {str(e)}") from e


def build_inventory_schema(
    date_col: str = "date",
    sku_col: str = "sku",
    qty_col: str = "on_hand_qty",
    unit_cost_col: str = "unit_cost",
) -> DataFrameSchema:
    """Build DataFrameSchema for validating daily inventory records."""
    return DataFrameSchema(
        columns={
            date_col: Column(dtype="datetime64[ns]", nullable=False, coerce=True),
            sku_col: Column(nullable=False, coerce=True),
            qty_col: Column(
                checks=[Check.ge(0, error=f"'{qty_col}' must be >= 0")],
                nullable=False,
                coerce=True,
            ),
            unit_cost_col: Column(
                checks=[Check.ge(0, error=f"'{unit_cost_col}' must be >= 0")],
                nullable=False,
                coerce=True,
            ),
        },
        coerce=True,
    )


def validate_inventory(
    df: pd.DataFrame,
    date_col: str = "date",
    sku_col: str = "sku",
    qty_col: str = "on_hand_qty",
    unit_cost_col: str = "unit_cost",
) -> pd.DataFrame:
    """Validate and coerce inventory DataFrame."""
    if df is None or len(df) == 0:
        raise SchemaValidationError("Input inventory DataFrame is empty or None.")

    schema = build_inventory_schema(
        date_col=date_col,
        sku_col=sku_col,
        qty_col=qty_col,
        unit_cost_col=unit_cost_col,
    )
    try:
        return schema.validate(df)
    except (errors.SchemaError, errors.SchemaErrors) as e:
        raise SchemaValidationError(f"Inventory data validation failed: {str(e)}") from e
