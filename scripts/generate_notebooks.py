"""Script to generate interactive Jupyter tutorials:
1. notebooks/01_scor_metrics_tutorial.ipynb
2. notebooks/02_bottleneck_simulation.ipynb
"""

import json
import os

def make_cell(cell_type, source):
    if cell_type == "markdown":
        return {
            "cell_type": "markdown",
            "metadata": {},
            "source": [s + "\n" for s in source.split("\n")]
        }
    else:
        return {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [s + "\n" for s in source.split("\n")]
        }

def create_notebook(cells, filepath):
    nb = {
        "cells": cells,
        "metadata": {
            "language_info": {
                "name": "python",
                "version": "3.10"
            }
        },
        "nbformat": 4,
        "nbformat_minor": 5
    }
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(nb, f, indent=2)
    print(f"Generated: {filepath}")

# ----------------- NOTEBOOK 1: TUTORIAL -----------------
nb1_cells = [
    make_cell("markdown", "# 📦 SCOR-Py: Panduan Metrik Rantai Pasok (SCOR Level 1 & 2)\n\nNotebook ini memandu Anda menghitung metrik kinerja rantai pasok berbasis kerangka kerja **SCOR (Supply Chain Operations Reference)** menggunakan pustaka **SCOR-Py**.\n\n### Daftar Isi:\n1. Persiapan & Import Data\n2. Atribut Keandalan (Reliability: POF & OTIF)\n3. Atribut Responsivitas (Responsiveness: OFCT)\n4. Atribut Biaya (Costs: Total SCM Cost)\n5. Atribut Efisiensi Aset (Asset Efficiency: Cash-to-Cash Cycle Time)"),
    make_cell("code", "import pandas as pd\nimport numpy as np\nfrom scorpy.reliability import ReliabilityMetrics\nfrom scorpy.responsiveness import ResponsivenessMetrics\nfrom scorpy.cost import CostMetrics\nfrom scorpy.asset_efficiency import AssetMetrics\n\nprint('SCOR-Py siap digunakan!')"),
    make_cell("markdown", "## 1. Memuat Data Transaksi ERP Sintetis"),
    make_cell("code", "df_orders = pd.read_csv('../data/sample_orders.csv')\ndf_fin = pd.read_csv('../data/sample_financials.csv')\ndf_inv = pd.read_csv('../data/sample_inventory.csv')\n\nprint(f'Total pesanan: {len(df_orders)}')\ndf_orders.head(3)"),
    make_cell("markdown", "## 2. Keandalan: Perfect Order Fulfillment (RL.1.1) & OTIF\n\nSebuah pesanan dianggap sempurna (**Perfect Order**) jika memenuhi 4 kondisi sekaligus:\n1. Tepat Waktu (On-Time)\n2. Lengkap (In-Full)\n3. Tanpa Kerusakan (Damage-Free)\n4. Dokumen Akurat (Doc-Accurate)\n\nHubungan Invarian: $\\text{POF} \\le \\text{OTIF} \\le \\min(\\text{On-Time}, \\text{In-Full})$"),
    make_cell("code", "rel = ReliabilityMetrics(\n    data=df_orders,\n    order_id_col='so_number',\n    promised_date_col='promised_delivery_date',\n    actual_date_col='actual_delivery_date',\n    ordered_qty_col='qty_ordered',\n    delivered_qty_col='qty_delivered',\n    damaged_flag_col='is_damaged',\n    doc_accurate_col='is_doc_complete',\n    on_time_grace_days=0,\n    in_full_tolerance=0.0,\n)\n\nsummary = rel.evaluate_all()\nfor k, v in summary.items():\n    print(f'{k:28}: {v}')"),
    make_cell("markdown", "### Evaluasi per Segmen Pelanggan"),
    make_cell("code", "rel.evaluate_all(group_by='customer_segment')"),
    make_cell("markdown", "## 3. Responsivitas: Order Fulfillment Cycle Time (RS.1.1)\n\nMetrik ini mengukur durasi dari pesanan dibuat hingga diterima pelanggan (`actual_delivery_date - order_date`)."),
    make_cell("code", "resp = ResponsivenessMetrics(df_orders)\nofct = resp.order_fulfillment_cycle_time()\nprint('Statistik Waktu Siklus (Hari):')\nfor k, v in ofct.items():\n    print(f'{k:15}: {v} hari')"),
    make_cell("markdown", "## 4. Efisiensi Biaya: Total SCM Cost (CO.1.1)\n\nAgregasi biaya transportasi, pergudangan, pengadaan, dan pengembalian barang (*reverse logistics*)."),
    make_cell("code", "cost = CostMetrics.from_dataframe(df_fin)\ncost_eval = cost.evaluate_all()\nprint(f'Total Pendapatan : Rp {cost_eval[\"revenue\"]:,.0f}')\nprint(f'Total Biaya SCM  : Rp {cost_eval[\"total_scm_cost\"]:,.0f}')\nprint(f'Rasio Biaya SCM  : {cost_eval[\"scm_cost_pct_revenue\"]:.2f}% dari pendapatan')"),
    make_cell("markdown", "## 5. Efisiensi Aset: Cash-to-Cash Cycle Time (AM.1.1)\n\n$$\\text{C2C} = \\text{IDS} + \\text{DSO} - \\text{DPO}$$"),
    make_cell("code", "asset = AssetMetrics.from_dataframes(df_financials=df_fin, df_inventory=df_inv)\nc2c = asset.cash_to_cash_cycle()\nprint(f'IDS (Hari Persediaan) : {c2c[\"IDS\"]} hari')\nprint(f'DSO (Hari Piutang)    : {c2c[\"DSO\"]} hari')\nprint(f'DPO (Hari Utang)      : {c2c[\"DPO\"]} hari')\nprint(f'Cash-to-Cash Net      : {c2c[\"C2C_days\"]} hari')"),
]

# ----------------- NOTEBOOK 2: SIMULATION -----------------
nb2_cells = [
    make_cell("markdown", "# 🔬 SCOR-Py: Simulasi Monte Carlo & Analisis Hambatan (*Bottleneck*)\n\nNotebook ini mendemonstrasikan bagaimana **SCOR-Py** mengubah metrik historis menjadi keputusan strategis melalui analisis skenario *What-If* berbasis simulasi Monte Carlo.\n\n### Kasus Bisnis yang Dianalisis:\n1. **Dampak Keterlambatan Pemasok** terhadap Service Level (OTIF).\n2. **Optimasi Stok Pengaman (Safety Stock)** dan Pembebasan Modal Kerja.\n3. **Estimasi Ketangkasan Rantai Pasok (Agility AG.1.1)**."),
    make_cell("code", "import pandas as pd\nimport numpy as np\nfrom scorpy.simulator import SupplyChainSimulator\n\ndf_orders = pd.read_csv('../data/sample_orders.csv')\nsim = SupplyChainSimulator.from_orders(df_orders, seed=42)\nprint('Simulator diinisialisasi dengan data transaksi.')"),
    make_cell("markdown", "## 1. Skenario: Keterlambatan Pemasok (+3 Hari)\n\nBagaimana jika terjadi hambatan pengiriman dari vendor sebesar 3 hari? Berapa penurunan OTIF dan batas toleransi keyakinan 95%?"),
    make_cell("code", "result = sim.run(n_runs=1000, scenario={'supplier_lead_time_shift_days': 3})\notif_comparison = result.compare_to_baseline('OTIF_rate')\n\nprint(f'OTIF Baseline   : {otif_comparison[\"baseline\"]*100:.1f}%')\nprint(f'OTIF Proyeksi   : {otif_comparison[\"scenario_mean\"]*100:.1f}%')\nprint(f'Perubahan Rata2 : {otif_comparison[\"delta_mean\"]*100:+.1f}% ({otif_comparison[\"delta_pct\"]:+.1f}%)')\nprint(f'95% CI          : [{otif_comparison[\"ci_95_lower\"]*100:.1f}%, {otif_comparison[\"ci_95_upper\"]*100:.1f}%]')"),
    make_cell("markdown", "### Ringkasan Lengkap Dampak ke Semua Metrik"),
    make_cell("code", "result.summary()"),
    make_cell("markdown", "## 2. Skenario: Optimasi Safety Stock & Modal Kerja\n\nJika stok pengaman diturunkan 15%, berapa modal kerja yang dibebaskan dan bagaimana dampaknya terhadap siklus Cash-to-Cash?"),
    make_cell("code", "ss_sim = SupplyChainSimulator.simulate_safety_stock_adjustment(\n    avg_inventory_value=2_100_000_000,\n    annual_cogs=15_000_000_000,\n    annual_revenue=22_500_000_000,\n    accounts_receivable=1_800_000_000,\n    accounts_payable=1_400_000_000,\n    safety_stock_pct_of_inventory=0.40,\n    safety_stock_change_pct=-0.15,\n)\n\nprint(f'Modal Kerja Dibebaskan : Rp {ss_sim[\"working_capital_freed\"]:,.0f}')\nprint(f'Dampak ke IDS          : {ss_sim[\"delta_IDS_days\"]:+.1f} hari (dari {ss_sim[\"baseline_IDS_days\"]} ke {ss_sim[\"new_IDS_days\"]} hari)')\nprint(f'Dampak ke C2C          : {ss_sim[\"delta_C2C_days\"]:+.1f} hari')"),
    make_cell("markdown", "## 3. Estimasi Ketangkasan (Agility AG.1.1: Upside Flexibility)\n\nBerapa hari yang dibutuhkan perusahaan untuk memenuhi lonjakan permintaan +20% tanpa mengorbankan tingkat layanan?"),
    make_cell("code", "ag = sim.estimate_upside_flexibility(target_demand_increase_pct=0.20)\nprint(f'Metrik                     : {ag[\"metric\"]}')\nprint(f'Target Kenaikan Permintaan : +{ag[\"target_increase_pct\"]:.0f}%')\nprint(f'Waktu Adaptasi Estimasi    : {ag[\"estimated_days_to_adapt\"]} hari')"),
]

if __name__ == "__main__":
    create_notebook(nb1_cells, "notebooks/01_scor_metrics_tutorial.ipynb")
    create_notebook(nb2_cells, "notebooks/02_bottleneck_simulation.ipynb")
