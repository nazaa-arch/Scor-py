"""Script untuk menghasilkan data sintetis rantai pasok:
1. data/sample_orders.csv
2. data/sample_financials.csv
3. data/sample_inventory.csv
"""

from datetime import datetime, timedelta

import numpy as np
import pandas as pd


def generate_orders(n=1200, seed=42):
    np.random.seed(seed)
    start_date = datetime(2025, 1, 1)

    so_numbers = [f"SO-{10000 + i}" for i in range(n)]
    order_offsets = np.random.randint(0, 360, size=n)
    order_dates = [start_date + timedelta(days=int(off)) for off in order_offsets]

    # Promised lead times usually 3 to 10 days
    promised_lead_times = np.random.choice([3, 4, 5, 7, 10], size=n, p=[0.2, 0.3, 0.25, 0.15, 0.1])
    promised_dates = [
        od + timedelta(days=int(plt))
        for od, plt in zip(order_dates, promised_lead_times, strict=False)
    ]

    # Delivery variance:
    # ~91% on time (actual_lead_time <= promised_lead_time)
    actual_dates = []
    delay_reasons = []

    reasons_pool = [
        "Supplier Shortage",
        "Warehouse Congestion",
        "Carrier Breakdown",
        "Customs Clearance",
        "Weather Delay",
    ]

    for od, _pd_date, plt in zip(order_dates, promised_dates, promised_lead_times, strict=False):
        # 91% on time
        is_on_time = np.random.rand() < 0.910
        if is_on_time:
            # actual delivery is between 1 day and plt days
            act_lead = np.random.randint(1, plt + 1)
            actual_dates.append(od + timedelta(days=int(act_lead)))
            delay_reasons.append("None")
        else:
            # late by 1 to 6 days
            late_days = np.random.randint(1, 7)
            act_lead = plt + late_days
            actual_dates.append(od + timedelta(days=int(act_lead)))
            delay_reasons.append(np.random.choice(reasons_pool))

    # Ordered and delivered quantities
    qty_ordered = np.random.choice(
        [10, 20, 50, 100, 200, 500, 1000], size=n, p=[0.15, 0.2, 0.25, 0.2, 0.1, 0.07, 0.03]
    )

    qty_delivered = []
    for qo in qty_ordered:
        # In-full probability around 88.5%
        if np.random.rand() < 0.885:
            # Full or slight surplus
            if np.random.rand() < 0.05:
                qty_delivered.append(qo + int(qo * 0.05))  # small bonus
            else:
                qty_delivered.append(qo)
        else:
            # Partial fulfillment (between 60% and 95%)
            delivered_pct = np.random.uniform(0.60, 0.95)
            qty_delivered.append(max(1, int(qo * delivered_pct)))

    # Damage: ~0.8% damaged (99.2% damage-free)
    is_damaged = [np.random.rand() < 0.008 for _ in range(n)]

    # Documentation complete: ~97.5% complete
    is_doc_complete = [np.random.rand() < 0.975 for _ in range(n)]

    customer_segments = np.random.choice(
        ["Enterprise", "Retail", "Wholesale"], size=n, p=[0.35, 0.40, 0.25]
    )
    product_categories = np.random.choice(
        ["Electronics", "Industrial", "FMCG"], size=n, p=[0.40, 0.35, 0.25]
    )
    suppliers = np.random.choice(
        ["Alpha Logistics", "Beta Supplies", "Gamma Global", "Delta Trans"],
        size=n,
        p=[0.35, 0.25, 0.25, 0.15],
    )

    df = pd.DataFrame(
        {
            "so_number": so_numbers,
            "order_date": [d.strftime("%Y-%m-%d") for d in order_dates],
            "promised_delivery_date": [d.strftime("%Y-%m-%d") for d in promised_dates],
            "actual_delivery_date": [d.strftime("%Y-%m-%d") for d in actual_dates],
            "qty_ordered": qty_ordered,
            "qty_delivered": qty_delivered,
            "is_damaged": is_damaged,
            "is_doc_complete": is_doc_complete,
            "customer_segment": customer_segments,
            "product_category": product_categories,
            "supplier": suppliers,
            "delay_reason": delay_reasons,
        }
    )

    # Sort by order_date
    df = df.sort_values("order_date").reset_index(drop=True)
    return df


def generate_financials():
    # 12 monthly periods in 2025
    # Total annual revenue ~ 22.5 billion IDR
    # Total annual cogs ~ 15.0 billion IDR
    periods = [f"2025-{m:02d}" for m in range(1, 13)]

    monthly_rev_base = 22_500_000_000 / 12
    monthly_cogs_base = 15_000_000_000 / 12

    np.random.seed(42)
    # Seasonal weights (slightly higher Q4)
    seasonal_weights = [0.92, 0.94, 0.98, 1.0, 1.02, 1.01, 0.99, 1.03, 1.02, 1.04, 1.08, 1.12]
    rev_weights = np.array(seasonal_weights) / np.mean(seasonal_weights)

    revenues = monthly_rev_base * rev_weights * np.random.uniform(0.98, 1.02, 12)
    cogs = monthly_cogs_base * rev_weights * np.random.uniform(0.97, 1.03, 12)

    # AR around 1.8 billion (DSO ~ 29.2 days)
    # AP around 1.4 billion (DPO ~ 34.1 days)
    ar = 1_800_000_000 * np.random.uniform(0.95, 1.05, 12)
    ap = 1_400_000_000 * np.random.uniform(0.95, 1.05, 12)

    # Logistics / SCM Costs
    # Transport ~ 4% of revenue
    # Warehousing ~ 3% of revenue
    # Procurement ~ 1.5% of revenue
    # Return / Reverse ~ 0.5% of revenue
    transport_cost = revenues * 0.040 * np.random.uniform(0.95, 1.05, 12)
    warehousing_cost = revenues * 0.030 * np.random.uniform(0.95, 1.05, 12)
    procurement_cost = revenues * 0.015 * np.random.uniform(0.95, 1.05, 12)
    return_cost = revenues * 0.005 * np.random.uniform(0.90, 1.10, 12)

    # Supply chain fixed assets ~ 5 billion IDR
    sc_fixed_assets = [5_000_000_000.0] * 12

    df = pd.DataFrame(
        {
            "period": periods,
            "revenue": np.round(revenues, 2),
            "cogs": np.round(cogs, 2),
            "accounts_receivable": np.round(ar, 2),
            "accounts_payable": np.round(ap, 2),
            "transport_cost": np.round(transport_cost, 2),
            "warehousing_cost": np.round(warehousing_cost, 2),
            "procurement_cost": np.round(procurement_cost, 2),
            "return_cost": np.round(return_cost, 2),
            "sc_fixed_assets": sc_fixed_assets,
        }
    )
    return df


def generate_inventory():
    # SKUs and daily inventory for Q4 2025 (or full year 2025)
    # Average inventory value should be around 2.1 billion IDR
    np.random.seed(42)
    dates = pd.date_range("2025-01-01", "2025-12-31", freq="D")

    skus = [
        ("SKU-ELC-01", "Electronics", 150_000.0, 3000),
        ("SKU-ELC-02", "Electronics", 450_000.0, 1200),
        ("SKU-IND-01", "Industrial", 800_000.0, 800),
        ("SKU-IND-02", "Industrial", 250_000.0, 1500),
        ("SKU-FMC-01", "FMCG", 25_000.0, 12000),
        ("SKU-FMC-02", "FMCG", 50_000.0, 6000),
    ]

    records = []
    for d in dates:
        d_str = d.strftime("%Y-%m-%d")
        for sku_id, category, unit_cost, target_qty in skus:
            # Daily inventory fluctuation around target_qty
            daily_qty = max(0, int(np.random.normal(target_qty, target_qty * 0.08)))
            records.append(
                {
                    "date": d_str,
                    "sku": sku_id,
                    "category": category,
                    "on_hand_qty": daily_qty,
                    "unit_cost": unit_cost,
                    "inventory_value": round(daily_qty * unit_cost, 2),
                }
            )

    df = pd.DataFrame(records)
    return df


if __name__ == "__main__":
    df_orders = generate_orders()
    df_orders.to_csv("data/sample_orders.csv", index=False)
    print(f"Generated sample_orders.csv: {len(df_orders)} rows")

    df_financials = generate_financials()
    df_financials.to_csv("data/sample_financials.csv", index=False)
    print(f"Generated sample_financials.csv: {len(df_financials)} rows")

    df_inventory = generate_inventory()
    df_inventory.to_csv("data/sample_inventory.csv", index=False)
    print(f"Generated sample_inventory.csv: {len(df_inventory)} rows")

    avg_inv = df_inventory.groupby("date")["inventory_value"].sum().mean()
    print(f"Average daily inventory value: Rp {avg_inv:,.2f}")
