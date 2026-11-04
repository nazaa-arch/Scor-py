"""Streamlit Dashboard for SCOR-Py: Toolkit Metrik & Simulasi Rantai Pasok Berbasis SCOR."""

import os

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from dashboard.components.gauge import create_gauge_chart
from dashboard.components.sankey import create_delivery_sankey
from dashboard.components.waterfall import create_c2c_waterfall, create_cost_waterfall
from scorpy.asset_efficiency import AssetMetrics
from scorpy.cost import CostMetrics
from scorpy.reliability import ReliabilityMetrics
from scorpy.responsiveness import ResponsivenessMetrics
from scorpy.simulator import SupplyChainSimulator

st.set_page_config(
    page_title="SCOR-Py | Toolkit Kinerja Rantai Pasok & Simulasi",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling
st.markdown(
    """
    <style>
    .main { background-color: #f8fafc; }
    .metric-card {
        background-color: white;
        padding: 18px;
        border-radius: 10px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        margin-bottom: 12px;
    }
    .metric-title { font-size: 0.85rem; color: #64748b; font-weight: 600; text-transform: uppercase; }
    .metric-value { font-size: 1.8rem; font-weight: 700; color: #1e293b; }
    .metric-delta { font-size: 0.85rem; font-weight: 600; }
    </style>
    """,
    unsafe_allow_html=True,
)


# ----------------- DATA LOADING -----------------
@st.cache_data
def load_sample_data():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    orders_path = os.path.join(base_dir, "data", "sample_orders.csv")
    fin_path = os.path.join(base_dir, "data", "sample_financials.csv")
    inv_path = os.path.join(base_dir, "data", "sample_inventory.csv")

    df_orders = pd.read_csv(orders_path)
    df_fin = pd.read_csv(fin_path)
    df_inv = pd.read_csv(inv_path)
    return df_orders, df_fin, df_inv


# Load data
df_orders_raw, df_fin_raw, df_inv_raw = load_sample_data()

# ----------------- SIDEBAR -----------------
st.sidebar.image("https://img.shields.io/badge/SCOR--Py-v0.1.0-blue?style=for-the-badge", width=180)
st.sidebar.title("Kontrol & Parameter")

data_source = st.sidebar.radio(
    "Sumber Data", ["Data Sampel Sintetis ERP", "Unggah Berkas CSV Sendiri"]
)

if data_source == "Unggah Berkas CSV Sendiri":
    up_orders = st.sidebar.file_uploader("Unggah Orders CSV", type=["csv"])
    if up_orders:
        df_orders_raw = pd.read_csv(up_orders)

# Preprocessing dates
df_orders = df_orders_raw.copy()
df_orders["order_date"] = pd.to_datetime(df_orders["order_date"])
df_orders["actual_delivery_date"] = pd.to_datetime(df_orders["actual_delivery_date"])
df_orders["promised_delivery_date"] = pd.to_datetime(df_orders["promised_delivery_date"])

# Filters
min_date = df_orders["order_date"].min().date()
max_date = df_orders["order_date"].max().date()
date_range = st.sidebar.date_input("Rentang Tanggal Pesanan", [min_date, max_date])

if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
    start_d, end_d = date_range
    df_orders = df_orders[
        (df_orders["order_date"].dt.date >= start_d) & (df_orders["order_date"].dt.date <= end_d)
    ]

# Segment filter
all_segments = ["Semua"] + sorted(list(df_orders["customer_segment"].dropna().unique()))
sel_segment = st.sidebar.selectbox("Segmen Pelanggan", all_segments)
if sel_segment != "Semua":
    df_orders = df_orders[df_orders["customer_segment"] == sel_segment]

# Supplier filter
all_suppliers = ["Semua"] + sorted(list(df_orders["supplier"].dropna().unique()))
sel_supplier = st.sidebar.selectbox("Pemasok / Vendor", all_suppliers)
if sel_supplier != "Semua":
    df_orders = df_orders[df_orders["supplier"] == sel_supplier]

st.sidebar.markdown("---")
st.sidebar.subheader("Toleransi SCOR")
grace_days = st.sidebar.number_input(
    "Toleransi Hari Keterlambatan (Grace Days)", min_value=0, max_value=7, value=0
)
in_full_tol = (
    st.sidebar.slider(
        "Toleransi Kuantitas In-Full (%)", min_value=0.0, max_value=10.0, value=0.0, step=0.5
    )
    / 100.0
)

st.title("📦 SCOR-Py: Dashboard Metrik & Simulasi Rantai Pasok")
st.caption("Implementasi Kerangka Kerja SCOR (Supply Chain Operations Reference) Level 1 & 2")

# Main Navigation Tabs
tab_rel, tab_resp, tab_asset_cost, tab_sim = st.tabs(
    [
        "🎯 1. Keandalan (Reliability)",
        "⏱️ 2. Responsivitas (Responsiveness)",
        "💰 3. Efisiensi Aset & Biaya (Assets & Costs)",
        "🔬 4. What-If Simulator (Monte Carlo)",
    ]
)

# ----------------- TAB 1: RELIABILITY -----------------
with tab_rel:
    st.subheader("Keandalan Rantai Pasok: Perfect Order Fulfillment (RL.1.1)")

    if len(df_orders) == 0:
        st.warning("Tidak ada data pesanan untuk filter yang dipilih.")
    else:
        rel = ReliabilityMetrics(
            data=df_orders,
            order_id_col="so_number",
            promised_date_col="promised_delivery_date",
            actual_date_col="actual_delivery_date",
            ordered_qty_col="qty_ordered",
            delivered_qty_col="qty_delivered",
            damaged_flag_col="is_damaged",
            doc_accurate_col="is_doc_complete",
            on_time_grace_days=grace_days,
            in_full_tolerance=in_full_tol,
            validate=False,
        )
        rel_summary = rel.evaluate_all()

        col1, col2, col3 = st.columns(3)
        with col1:
            st.plotly_chart(
                create_gauge_chart(
                    rel_summary["Perfect_Order_Fulfillment"],
                    "Perfect Order Fulfillment (RL.1.1)",
                    target=0.85,
                ),
                use_container_width=True,
            )
        with col2:
            st.plotly_chart(
                create_gauge_chart(rel_summary["OTIF_rate"], "On-Time In-Full (OTIF)", target=0.90),
                use_container_width=True,
            )
        with col3:
            st.plotly_chart(
                create_gauge_chart(
                    rel_summary["On_Time_rate"], "On-Time Delivery Rate", target=0.95
                ),
                use_container_width=True,
            )

        col4, col5, col6 = st.columns(3)
        with col4:
            st.plotly_chart(
                create_gauge_chart(
                    rel_summary["In_Full_rate"], "In-Full Delivery Rate", target=0.95
                ),
                use_container_width=True,
            )
        with col5:
            st.plotly_chart(
                create_gauge_chart(
                    rel_summary["Damage_Free_rate"], "Damage-Free Rate", target=0.99
                ),
                use_container_width=True,
            )
        with col6:
            st.plotly_chart(
                create_gauge_chart(
                    rel_summary["Doc_Accurate_rate"], "Documentation Accurate Rate", target=0.98
                ),
                use_container_width=True,
            )

        # Invariant Verification Alert
        pof = rel_summary["Perfect_Order_Fulfillment"]
        otif = rel_summary["OTIF_rate"]
        on_time = rel_summary["On_Time_rate"]
        in_full = rel_summary["In_Full_rate"]
        is_invariant_valid = (pof <= otif + 1e-6) and (otif <= min(on_time, in_full) + 1e-6)

        st.info(
            f"✅ **Verifikasi Hubungan Invarian SCOR:** "
            f"POF ({pof * 100:.1f}%) ≤ OTIF ({otif * 100:.1f}%) ≤ min(On-Time: {on_time * 100:.1f}%, In-Full: {in_full * 100:.1f}%) → **{'VALID' if is_invariant_valid else 'TIDAK VALID'}**"
        )

        st.markdown("---")
        st.subheader("Analisis Segmentasi & Aliran Akar Masalah")

        c_left, c_right = st.columns([1, 1])
        with c_left:
            st.markdown("##### Performa Metrik per Segmen Pelanggan")
            df_by_seg = rel.evaluate_all(group_by="customer_segment")
            st.dataframe(
                df_by_seg.style.format(
                    "{:.2%}",
                    subset=[c for c in df_by_seg.columns if "rate" in c or "Fulfillment" in c],
                ),
                use_container_width=True,
            )

            st.markdown("##### Performa Metrik per Pemasok")
            df_by_sup = rel.evaluate_all(group_by="supplier")
            st.dataframe(
                df_by_sup.style.format(
                    "{:.2%}",
                    subset=[c for c in df_by_sup.columns if "rate" in c or "Fulfillment" in c],
                ),
                use_container_width=True,
            )

        with c_right:
            st.markdown("##### Aliran Akar Masalah Keterlambatan (Sankey)")
            detailed_df = rel.detailed_orders()
            sankey_fig = create_delivery_sankey(detailed_df)
            st.plotly_chart(sankey_fig, use_container_width=True)

# ----------------- TAB 2: RESPONSIVENESS -----------------
with tab_resp:
    st.subheader("Responsivitas Rantai Pasok: Order Fulfillment Cycle Time (RS.1.1)")
    resp = ResponsivenessMetrics(df_orders)
    ofct_stats = resp.order_fulfillment_cycle_time()

    r1, r2, r3, r4 = st.columns(4)
    r1.metric("OFCT Rata-rata (Mean)", f"{ofct_stats['mean_days']:.1f} hari")
    r2.metric("OFCT Median (P50)", f"{ofct_stats['median_days']:.1f} hari")
    r3.metric("OFCT Persentil 90 (P90)", f"{ofct_stats['p90_days']:.1f} hari")
    r4.metric(
        "Rentang Waktu (Min - Max)",
        f"{ofct_stats['min_days']:.0f} - {ofct_stats['max_days']:.0f} hari",
    )

    c_plot1, c_plot2 = st.columns(2)
    with c_plot1:
        st.markdown("##### Distribusi Waktu Siklus Pemenuhan Pesanan (OFCT)")
        fig_hist = px.histogram(
            resp.valid_df,
            x="_ofct_days",
            nbins=20,
            color_discrete_sequence=["#3b82f6"],
            labels={"_ofct_days": "Waktu Siklus (Hari)"},
            title="Histogram OFCT",
        )
        fig_hist.add_vline(
            x=ofct_stats["mean_days"],
            line_dash="dash",
            line_color="orange",
            annotation_text=f"Mean: {ofct_stats['mean_days']:.1f}d",
        )
        fig_hist.add_vline(
            x=ofct_stats["p90_days"],
            line_dash="dot",
            line_color="red",
            annotation_text=f"P90: {ofct_stats['p90_days']:.1f}d",
        )
        fig_hist.update_layout(plot_bgcolor="#f8fafc", height=350)
        st.plotly_chart(fig_hist, use_container_width=True)

    with c_plot2:
        st.markdown("##### Sebaran OFCT Berdasarkan Segmen Pelanggan")
        fig_box = px.box(
            resp.valid_df,
            x="customer_segment",
            y="_ofct_days",
            color="customer_segment",
            labels={"_ofct_days": "Waktu Siklus (Hari)", "customer_segment": "Segmen Pelanggan"},
            title="Distribusi Waktu Siklus per Segmen",
        )
        fig_box.update_layout(plot_bgcolor="#f8fafc", height=350, showlegend=False)
        st.plotly_chart(fig_box, use_container_width=True)

    st.markdown("##### Variansi Lead Time terhadap Janji Kirim")
    variance_stats = resp.lead_time_variance()
    v1, v2 = st.columns(2)
    v1.metric(
        "Pesanan Tepat Waktu / Lebih Cepat", f"{variance_stats['pct_early_or_on_time'] * 100:.1f}%"
    )
    v2.metric(
        "Pesanan Melewati Janji Kirim (Delayed)", f"{variance_stats['pct_delayed'] * 100:.1f}%"
    )

# ----------------- TAB 3: ASSETS & COSTS -----------------
with tab_asset_cost:
    st.subheader("Efisiensi Aset & Biaya Manajemen Rantai Pasok (AM.1.1 & CO.1.1)")

    # Asset Metrics
    asset_engine = AssetMetrics.from_dataframes(
        df_financials=df_fin_raw,
        df_inventory=df_inv_raw,
        scm_cost_cols=["transport_cost", "warehousing_cost", "procurement_cost", "return_cost"],
    )
    c2c_dict = asset_engine.cash_to_cash_cycle()
    rofa = asset_engine.return_on_fixed_assets()
    rowc = asset_engine.return_on_working_capital()

    a1, a2, a3, a4 = st.columns(4)
    a1.metric("Cash-to-Cash Cycle Time (C2C)", f"{c2c_dict['C2C_days']:.1f} hari")
    a2.metric("Inventory Days of Supply (IDS)", f"{c2c_dict['IDS']:.1f} hari")
    a3.metric("Days Sales Outstanding (DSO)", f"{c2c_dict['DSO']:.1f} hari")
    a4.metric("Days Payable Outstanding (DPO)", f"{c2c_dict['DPO']:.1f} hari")

    col_w1, col_w2 = st.columns(2)
    with col_w1:
        st.plotly_chart(
            create_c2c_waterfall(c2c_dict["IDS"], c2c_dict["DSO"], c2c_dict["DPO"]),
            use_container_width=True,
        )

    with col_w2:
        # Cost Metrics
        cost_engine = CostMetrics.from_dataframe(df_fin_raw)
        cost_summary = cost_engine.evaluate_all()
        st.plotly_chart(create_cost_waterfall(cost_summary["breakdown"]), use_container_width=True)

    st.markdown("---")
    st.subheader("Efisiensi Modal & Tren Biaya SCM")
    ec1, ec2, ec3 = st.columns(3)
    ec1.metric("Total SCM Cost", f"Rp {cost_summary['total_scm_cost']:,.0f}")
    ec2.metric("SCM Cost % of Revenue", f"{cost_summary['scm_cost_pct_revenue']:.2f}%")
    if rofa is not None:
        ec3.metric("Return on SC Fixed Assets (AM.1.2)", f"{rofa * 100:.2f}%")

    # Periodic trend
    st.markdown("##### Tren Bulanan Biaya SCM vs Pendapatan")
    trend_df = CostMetrics.periodic_trend(df_fin_raw)
    fig_trend = go.Figure()
    fig_trend.add_trace(
        go.Bar(
            x=trend_df["period"],
            y=trend_df["total_scm_cost"],
            name="Biaya SCM (IDR)",
            marker_color="#3b82f6",
        )
    )
    fig_trend.add_trace(
        go.Scatter(
            x=trend_df["period"],
            y=trend_df["scm_cost_pct"],
            name="SCM Cost %",
            yaxis="y2",
            line=dict(color="#ef4444", width=3),
        )
    )
    fig_trend.update_layout(
        title="Biaya SCM Bulanan dan Rasio terhadap Pendapatan",
        yaxis=dict(title="Biaya SCM (IDR)"),
        yaxis2=dict(title="Persentase Pendapatan (%)", overlaying="y", side="right"),
        plot_bgcolor="#f8fafc",
        height=380,
    )
    st.plotly_chart(fig_trend, use_container_width=True)

# ----------------- TAB 4: WHAT-IF SIMULATOR -----------------
with tab_sim:
    st.subheader("🔬 Simulator What-If & Analisis Skenario Monte Carlo")
    st.markdown(
        "Gunakan simulator ini untuk memproyeksikan dampak gangguan rantai pasok terhadap metrik keandalan "
        "atau menghitung potensi pembebasan modal kerja dari optimasi persediaan."
    )

    sim_col1, sim_col2 = st.columns(2)

    with sim_col1:
        st.markdown("#### Skenario 1: Pergeseran Lead Time Pemasok")
        lead_shift = st.slider(
            "Pergeseran Waktu Tunggu Pemasok (Hari)",
            min_value=-5,
            max_value=10,
            value=3,
            step=1,
            help="Nilai positif berarti pemasok terlambat sekian hari.",
        )
        target_sim_sup = st.selectbox(
            "Pemasok yang Terdampak",
            ["Semua Pemasok"] + sorted(list(df_orders["supplier"].dropna().unique())),
        )
        demand_surge = (
            st.slider(
                "Lonjakan Permintaan Mendadak (Demand Spike %)",
                min_value=0,
                max_value=50,
                value=0,
                step=5,
            )
            / 100.0
        )
        n_iterations = st.select_slider(
            "Jumlah Replikasi Monte Carlo", options=[200, 500, 1000, 2000, 5000], value=1000
        )

        run_sim = st.button("🚀 Jalankan Simulasi Monte Carlo", type="primary")

    with sim_col2:
        st.markdown("#### Skenario 2: Optimasi Safety Stock & Modal Kerja")
        ss_reduction = st.slider(
            "Penyesuaian Stok Pengaman / Safety Stock (%)",
            min_value=-30,
            max_value=30,
            value=-15,
            step=5,
            help="Nilai negatif berarti penurunan persediaan cadangan.",
        )
        ss_share = (
            st.slider(
                "Porsi Safety Stock dari Total Persediaan (%)",
                min_value=20,
                max_value=60,
                value=40,
                step=5,
            )
            / 100.0
        )

        inv_calc = SupplyChainSimulator.simulate_safety_stock_adjustment(
            avg_inventory_value=asset_engine.avg_inventory_value,
            annual_cogs=asset_engine.annual_cogs,
            annual_revenue=asset_engine.annual_revenue,
            accounts_receivable=asset_engine.accounts_receivable,
            accounts_payable=asset_engine.accounts_payable,
            safety_stock_pct_of_inventory=ss_share,
            safety_stock_change_pct=ss_reduction / 100.0,
        )

        st.markdown("##### Hasil Simulasi Modal Kerja:")
        kc1, kc2 = st.columns(2)
        kc1.metric("Modal Kerja yang Dibebaskan", f"Rp {inv_calc['working_capital_freed']:,.0f}")
        kc2.metric("Dampak ke IDS (Hari)", f"{inv_calc['delta_IDS_days']:+.1f} hari")
        kc3, kc4 = st.columns(2)
        kc3.metric(
            "Cash-to-Cash Baru",
            f"{inv_calc['new_C2C_days']:.1f} hari",
            f"{inv_calc['delta_C2C_days']:+.1f} hari",
        )
        kc4.metric("Nilai Persediaan Baru", f"Rp {inv_calc['new_inventory_value']:,.0f}")

    if run_sim:
        st.markdown("---")
        st.subheader("Hasil Simulasi Monte Carlo:")
        with st.spinner("Menjalankan simulasi berulang..."):
            sim_engine = SupplyChainSimulator.from_orders(df_orders, seed=42)
            scenario_params = {
                "supplier_lead_time_shift_days": lead_shift,
                "demand_spike_pct": demand_surge,
            }
            if target_sim_sup != "Semua Pemasok":
                scenario_params["supplier_filter"] = target_sim_sup

            sim_result = sim_engine.run(n_runs=n_iterations, scenario=scenario_params)

        otif_comp = sim_result.compare_to_baseline("OTIF_rate")
        pof_comp = sim_result.compare_to_baseline("Perfect_Order_Fulfillment")
        on_time_comp = sim_result.compare_to_baseline("On_Time_rate")

        sc1, sc2, sc3 = st.columns(3)
        sc1.metric(
            "OTIF Terproyeksi",
            f"{otif_comp['scenario_mean'] * 100:.1f}%",
            f"{otif_comp['delta_mean'] * 100:+.1f}% ({otif_comp['delta_pct']:+.1f}%)",
        )
        sc2.metric(
            "POF Terproyeksi",
            f"{pof_comp['scenario_mean'] * 100:.1f}%",
            f"{pof_comp['delta_mean'] * 100:+.1f}% ({pof_comp['delta_pct']:+.1f}%)",
        )
        sc3.metric(
            "On-Time Rate Terproyeksi",
            f"{on_time_comp['scenario_mean'] * 100:.1f}%",
            f"{on_time_comp['delta_mean'] * 100:+.1f}% ({on_time_comp['delta_pct']:+.1f}%)",
        )

        st.caption(
            f"ℹ️ **Interval Kepercayaan 95% (OTIF):** {otif_comp['ci_95_lower'] * 100:.1f}% - {otif_comp['ci_95_upper'] * 100:.1f}% "
            f"(Berdasarkan {n_iterations:,} iterasi Monte Carlo)"
        )

        # Plot distribution of runs
        st.markdown("##### Sebaran Hasil Simulasi Replikasi Monte Carlo")
        fig_dist = px.histogram(
            sim_result.runs_df,
            x=["OTIF_rate", "Perfect_Order_Fulfillment"],
            barmode="overlay",
            nbins=30,
            labels={"value": "Tingkat Metrik (Rasio)", "variable": "Metrik"},
            title="Distribusi Probabilitas Metrik Pasca-Gangguan",
        )
        fig_dist.add_vline(
            x=otif_comp["baseline"],
            line_dash="dash",
            line_color="green",
            annotation_text=f"Baseline OTIF: {otif_comp['baseline'] * 100:.1f}%",
        )
        fig_dist.update_layout(plot_bgcolor="#f8fafc", height=380)
        st.plotly_chart(fig_dist, use_container_width=True)

        st.markdown("##### Tabel Perbandingan Lengkap:")
        st.dataframe(sim_result.summary(), use_container_width=True)

    # Agility Estimator
    st.markdown("---")
    st.subheader("Ketangkasan Rantai Pasok: Upside Supply Chain Flexibility (AG.1.1)")
    sim_engine = SupplyChainSimulator.from_orders(df_orders, seed=42)
    ag_data = sim_engine.estimate_upside_flexibility(target_demand_increase_pct=0.20)
    ag_col1, ag_col2 = st.columns(2)
    ag_col1.metric(
        "Waktu Adaptasi Peningkatan Permintaan +20%", f"{ag_data['estimated_days_to_adapt']} hari"
    )
    ag_col2.info(
        f"📌 {ag_data['note']} (Waktu siklus saat ini: {ag_data['mean_current_cycle_days']} hari)"
    )
