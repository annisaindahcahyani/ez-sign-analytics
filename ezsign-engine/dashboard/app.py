import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# --- CONFIG & KONEKSI ---
st.set_page_config(page_title="EzSign Analytics Dashboard", layout="wide")
DB_PATH = "/data/database.sqlite" # Jalur di dalem kontainer Docker

def get_data(query):
    try:
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    except Exception as e:
        return pd.DataFrame()

# --- HEADER ---
st.title("🛡️ EzSign Intelligent Analytics Dashboard")
st.markdown("Monitoring Digital Trust & Document Integrity secara Real-Time.")
st.divider()

# --- 1. KEY METRICS ---
kpi_query = """
SELECT 
    COUNT(f1_id) as total,
    SUM(f1_is_trusted) as trusted,
    SUM(CASE WHEN f1_is_trusted = 0 THEN 1 ELSE 0 END) as untrusted,
    AVG(f1_validity_days) as avg_validity
FROM esa_fact_verifications
"""
df_kpi = get_data(kpi_query)

if not df_kpi.empty:
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Verifikasi", df_kpi['total'][0])
    col2.metric("Trusted Documents", f"{int(df_kpi['trusted'][0] or 0)} ✅")
    col3.metric("Anomali / Not Trusted", f"{int(df_kpi['untrusted'][0] or 0)} ❌", delta_color="inverse")
    col4.metric("Avg. Validity (Days)", f"{int(df_kpi['avg_validity'][0] or 0)} Days")
else:
    st.warning("Database belum terisi data. Selesaikan proses Ingestion dulu jirr! 💅")

st.divider()

# --- 2. ANALISIS VISUAL ---
left_col, right_col = st.columns(2)

with left_col:
    st.subheader("🔍 Integrity Status Breakdown")
    status_query = "SELECT c5_status_type, COUNT(*) as count FROM esa_dim_integrity_c5 GROUP BY 1"
    df_status = get_data(status_query)
    if not df_status.empty:
        fig_status = px.pie(df_status, values='count', names='c5_status_type', hole=0.4,
                             color_map={'Trusted':'#2ecc71', 'Not Trusted':'#e74c3c'})
        st.plotly_chart(fig_status, use_container_width=True)

with right_col:
    st.subheader("🏢 Top Issuer Performance")
    issuer_query = "SELECT c2_common_name, COUNT(*) as total FROM esa_dim_issuer_c2 GROUP BY 1 ORDER BY total DESC LIMIT 5"
    df_issuer = get_data(issuer_query)
    if not df_issuer.empty:
        fig_issuer = px.bar(df_issuer, x='total', y='c2_common_name', orientation='h', color='total')
        st.plotly_chart(fig_issuer, use_container_width=True)

# --- 3. DATA TABLE ---
st.subheader("📑 Raw Verifications Log (Audit Trail)")
raw_query = "SELECT * FROM esa_fact_verifications ORDER BY f1_ingested_at DESC LIMIT 10"
df_raw = get_data(raw_query)
st.dataframe(df_raw, use_container_width=True)