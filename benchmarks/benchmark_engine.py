"""Performance benchmarking suite for SCOR-Py calculation engines."""

import time
import pandas as pd
import numpy as np
from scorpy.reliability import ReliabilityMetrics
from scorpy.responsiveness import ResponsivenessMetrics
from scorpy.simulator import SupplyChainSimulator


def generate_benchmark_data(n_orders: int) -> pd.DataFrame:
    """Generate in-memory orders DataFrame for benchmarking."""
    np.random.seed(42)
    base_date = pd.Timestamp("2025-01-01")
    order_offsets = np.random.randint(0, 300, size=n_orders)
    lead_times = np.random.randint(2, 10, size=n_orders)
    actual_shifts = np.random.choice([0, 1, 2, -1], size=n_orders, p=[0.7, 0.15, 0.1, 0.05])

    order_dates = [base_date + pd.Timedelta(days=int(off)) for off in order_offsets]
    promised_dates = [
        od + pd.Timedelta(days=int(lt)) for od, lt in zip(order_dates, lead_times, strict=False)
    ]
    actual_dates = [
        pd_d + pd.Timedelta(days=int(s))
        for pd_d, s in zip(promised_dates, actual_shifts, strict=False)
    ]

    qty = np.random.choice([50, 100, 200, 500], size=n_orders)
    delivered = np.where(np.random.rand(n_orders) < 0.90, qty, (qty * 0.8).astype(int))

    return pd.DataFrame(
        {
            "so_number": [f"SO-{i}" for i in range(n_orders)],
            "order_date": order_dates,
            "promised_delivery_date": promised_dates,
            "actual_delivery_date": actual_dates,
            "qty_ordered": qty,
            "qty_delivered": delivered,
            "is_damaged": np.random.rand(n_orders) < 0.01,
            "is_doc_complete": np.random.rand(n_orders) < 0.98,
            "customer_segment": np.random.choice(
                ["Enterprise", "Retail", "Wholesale"], size=n_orders
            ),
            "supplier": np.random.choice(["Vendor A", "Vendor B", "Vendor C"], size=n_orders),
        }
    )


def run_benchmarks():
    print("=" * 65)
    print("SCOR-PY ENGINE PERFORMANCE BENCHMARKS")
    print("=" * 65)

    scales = [1_000, 10_000, 50_000]

    print("\n--- 1. Reliability & Responsiveness Evaluation Speed ---")
    for n in scales:
        df = generate_benchmark_data(n)

        # Benchmark Reliability
        t0 = time.perf_counter()
        rel = ReliabilityMetrics(df, validate=False)
        _ = rel.evaluate_all()
        t_rel = time.perf_counter() - t0

        # Benchmark Responsiveness
        t0 = time.perf_counter()
        resp = ResponsivenessMetrics(df)
        _ = resp.order_fulfillment_cycle_time()
        t_resp = time.perf_counter() - t0

        orders_per_sec = n / t_rel
        print(
            f"Scale: {n:6,} orders | Rel: {t_rel * 1000:6.1f} ms ({orders_per_sec:10,.0f} ord/s) | Resp: {t_resp * 1000:6.1f} ms"
        )

    print("\n--- 2. Monte Carlo Simulation Engine Speed (1,000 base orders) ---")
    df_base = generate_benchmark_data(1_000)
    sim = SupplyChainSimulator.from_orders(df_base, seed=42)

    for runs in [500, 1_000, 5_000]:
        t0 = time.perf_counter()
        _ = sim.run(n_runs=runs, scenario={"supplier_lead_time_shift_days": 2})
        t_sim = time.perf_counter() - t0
        runs_per_sec = runs / t_sim
        print(
            f"Iterations: {runs:5,} runs | Time: {t_sim:5.2f} s | Throughput: {runs_per_sec:6,.0f} runs/sec"
        )

    print("=" * 65)
    print("BENCHMARK COMPLETED SUCCESSFULLY!")
    print("=" * 65)


if __name__ == "__main__":
    run_benchmarks()
