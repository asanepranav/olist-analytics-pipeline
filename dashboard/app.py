import sys
import streamlit as st
import duckdb
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import os
import subprocess

DB_PATH = "db/olist.duckdb"

st.set_page_config(
    page_title="Olist Analytics Pipeline",
    page_icon="📦",
    layout="wide"
)

st.markdown("""
    <style>
    .metric-card {
        background: #1e1e2e;
        border-radius: 10px;
        padding: 20px;
        border-left: 4px solid #7c3aed;
    }
    </style>
""", unsafe_allow_html=True)

@st.cache_resource
def get_conn():
    return duckdb.connect(DB_PATH)

@st.cache_data
def load_kpis():
    conn = duckdb.connect(DB_PATH)
    summary = conn.execute("""
        SELECT
            ROUND(AVG(seller_avg_review), 2) as avg_review,
            ROUND(AVG(seller_late_rate) * 100, 1) as late_pct,
            COUNT(*) as total_sellers,
            SUM(seller_total_orders) as total_orders
        FROM seller_features
    """).df()
    return summary.iloc[0]

@st.cache_data
def load_categories():
    conn = duckdb.connect(DB_PATH)
    return conn.execute("""
        SELECT product_category_name_english as category,
               category_total_orders as orders,
               ROUND(category_avg_price, 2) as avg_price,
               ROUND(category_avg_review, 2) as avg_review,
               ROUND(category_late_rate * 100, 1) as late_pct
        FROM category_features
        ORDER BY orders DESC
    """).df()

@st.cache_data
def load_states():
    conn = duckdb.connect(DB_PATH)
    return conn.execute("""
        SELECT customer_state as state,
               state_total_orders as orders,
               ROUND(state_late_rate * 100, 1) as late_pct,
               ROUND(state_avg_payment, 2) as avg_payment
        FROM customer_features
        ORDER BY late_pct DESC
    """).df()

@st.cache_data
def load_sellers():
    conn = duckdb.connect(DB_PATH)
    return conn.execute("""
        SELECT seller_id, seller_state,
               ROUND(seller_avg_review, 2) as avg_review,
               ROUND(seller_late_rate * 100, 1) as late_pct,
               seller_total_orders as total_orders
        FROM seller_features
        WHERE seller_total_orders >= 20
        ORDER BY late_pct DESC
        LIMIT 20
    """).df()

def load_report():
    path = "reports/olist_report.md"
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return None

# --- HEADER ---
st.title("📦 Olist E-Commerce Analytics Pipeline")
st.caption("PySpark · DuckDB · CrewAI · Streamlit")
st.divider()

# --- KPI CARDS ---
kpis = load_kpis()
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Orders", f"{int(kpis['total_orders']):,}")
c2.metric("Total Sellers", f"{int(kpis['total_sellers']):,}")
c3.metric("Avg Review Score", f"{kpis['avg_review']} / 5")
c4.metric("Late Delivery Rate", f"{kpis['late_pct']}%")

st.divider()

# --- CHARTS ROW 1 ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("Top Categories by Order Volume")
    cats = load_categories().head(10)
    fig = px.bar(
        cats, x="orders", y="category",
        orientation="h", color="avg_review",
        color_continuous_scale="Viridis",
        labels={"orders": "Total Orders", "category": ""},
    )
    fig.update_layout(height=400, margin=dict(l=0, r=0, t=0, b=0))
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("Late Delivery Rate by State")
    states = load_states()
    fig2 = px.bar(
        states, x="state", y="late_pct",
        color="late_pct", color_continuous_scale="Reds",
        labels={"late_pct": "Late %", "state": "State"},
    )
    fig2.update_layout(height=400, margin=dict(l=0, r=0, t=0, b=0))
    st.plotly_chart(fig2, use_container_width=True)

# --- CHARTS ROW 2 ---
col3, col4 = st.columns(2)

with col3:
    st.subheader("Category Avg Price vs Review Score")
    cats_all = load_categories()
    fig3 = px.scatter(
        cats_all, x="avg_price", y="avg_review",
        size="orders", color="late_pct",
        hover_name="category",
        color_continuous_scale="RdYlGn_r",
        labels={"avg_price": "Avg Price (R$)", "avg_review": "Avg Review"},
    )
    fig3.update_layout(height=400, margin=dict(l=0, r=0, t=0, b=0))
    st.plotly_chart(fig3, use_container_width=True)

with col4:
    st.subheader("State Avg Payment vs Late Rate")
    fig4 = px.scatter(
        states, x="avg_payment", y="late_pct",
        size="orders", hover_name="state",
        color="late_pct", color_continuous_scale="Reds",
        labels={"avg_payment": "Avg Payment (R$)", "late_pct": "Late %"},
    )
    fig4.update_layout(height=400, margin=dict(l=0, r=0, t=0, b=0))
    st.plotly_chart(fig4, use_container_width=True)

st.divider()

# --- SELLER TABLE ---
st.subheader("High-Risk Sellers (≥20 orders)")
sellers = load_sellers()
st.dataframe(
    sellers.style.background_gradient(subset=["late_pct"], cmap="Reds")
                 .background_gradient(subset=["avg_review"], cmap="Greens"),
    use_container_width=True
)

st.divider()

# --- AI REPORT ---
st.subheader("🤖 AI-Generated Business Report")

col_btn, col_status = st.columns([1, 3])
with col_btn:
    run_report = st.button("▶ Run AI Report", type="primary")

if run_report:
    with st.spinner("Running AI agents... (~30s)"):
        subprocess.run([sys.executable, "crew/pipeline_crew.py"], check=True)
    st.success("Report generated!")
    st.cache_data.clear() 

report = load_report()
if report:
    st.markdown(report)
else:
    st.info("No report yet. Click 'Run AI Report' to generate.")