import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
from datetime import datetime

# --- CONFIG & STYLING ---
st.set_page_config(page_title="EzSign Intelligent Analytics", layout="wide")

# Injecting your Jaksel-Cyber aesthetic
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Syne:wght@800&family=DM+Mono&family=Outfit:wght@300;600&display=swap');
    
    .stApp { background-color: #030d1a; color: #e8f4f0; font-family: 'Outfit', sans-serif; }
    
    /* KPI Card Style */
    .kpi-container {
        background: rgba(6,22,40,0.7); border: 1px solid rgba(16,185,129,0.15);
        border-radius: 12px; padding: 20px; text-align: left;
        transition: 0.3s;
    }
    .kpi-container:hover { border-color: #34d399; transform: translateY(-2px); }
    .kpi-label { font-family: 'DM Mono'; font-size: 11px; color: #8ab4a0; text-transform: uppercase; }
    .kpi-val { font-family: 'Syne'; font-size: 32px; font-weight: 800; color: #e8f4f0; }
</style>
""", unsafe_allow_html=True)

DB_PATH = "/data/database.sqlite"

def get_data(query):
    try:
        # Use context manager biar koneksi ga gantung jirr
        with sqlite3.connect(DB_PATH) as conn:
            return pd.read_sql_query(query, conn)
    except Exception as e:
        # st.error(f"Error: {e}") # Debug only
        return pd.DataFrame()

# --- HEADER SECTION ---
col_h1, col_h2 = st.columns([2, 1])
with col_h1:
    st.markdown("""
        <div style="border-left: 4px solid #10b981; padding-left: 15px;">
            <h1 style="font-family: 'Syne'; margin:0;">EZSIGN <span style="color:#34d399;">ANALYTICS</span></h1>
            <p style="color:#8ab4a0; font-size:14px;">Monitoring Digital Trust & Integrity • Class of 2023 Pride</p>
        </div>
    """, unsafe_allow_html=True)
with col_h2:
    st.markdown(f"""
        <div style="text-align:right; font-family:'DM Mono'; color:#4a7060; font-size:12px; padding-top:10px;">
            LIVE_FEED_ACTIVE<br>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC
        </div>
    """, unsafe_allow_html=True)

st.write("---")

# --- 1. REAL KPI LOGIC ---
kpi_query = """
SELECT 
    COUNT(f1_id) as total,
    SUM(f1_is_trusted) as trusted,
    SUM(CASE WHEN f1_is_trusted = 0 THEN 1 ELSE 0 END) as untrusted,
    AVG(f1_validity_days) as avg_validity
FROM esa_fact_verifications
"""
df_kpi = get_data(kpi_query)

if not df_kpi.empty and df_kpi['total'][0] > 0:
    c1, c2, c3, c4 = st.columns(4)
    
    with c1:
        st.markdown(f'<div class="kpi-container"><div class="kpi-label">Total Verifications</div><div class="kpi-val">{df_kpi["total"][0]:,}</div></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="kpi-container" style="border-left: 4px solid #34d399;"><div class="kpi-label">Trusted Docs</div><div class="kpi-val" style="color:#34d399;">{int(df_kpi["trusted"][0] or 0)}</div></div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="kpi-container" style="border-left: 4px solid #ef4444;"><div class="kpi-label">Anomalies</div><div class="kpi-val" style="color:#ef4444;">{int(df_kpi["untrusted"][0] or 0)}</div></div>', unsafe_allow_html=True)
    with c4:
        st.markdown(f'<div class="kpi-container" style="border-left: 4px solid #fbbf24;"><div class="kpi-label">Avg Validity</div><div class="kpi-val" style="color:#fbbf24;">{int(df_kpi["avg_validity"][0] or 0)}d</div></div>', unsafe_allow_html=True)
else:
    st.warning("Database empty, Ca! Coba cek ingestion script lu, jangan sampe 'fumble the bag' ya! 💅")

st.write("")

# --- 2. VISUAL INTELLIGENCE ---
l_col, r_col = st.columns(2)

with l_col:
    st.markdown("### 🔍 Integrity Status")
    status_query = "SELECT c5_status_type, COUNT(*) as count FROM esa_dim_integrity_c5 GROUP BY 1"
    df_status = get_data(status_query)
    
    if not df_status.empty:
        fig_status = px.pie(
            df_status, values='count', names='c5_status_type', hole=0.5,
            color='c5_status_type',
            color_discrete_map={'Trusted': '#10b981', 'Not Trusted': '#ef4444', 'Warning': '#fbbf24'}
        )
        fig_status.update_layout(
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            font_color="#e8f4f0", margin=dict(t=0, b=0, l=0, r=0), height=300
        )
        st.plotly_chart(fig_status, use_container_width=True)

with r_col:
    st.markdown("### 🏢 Top Issuer Performance")
    issuer_query = "SELECT c2_common_name, COUNT(*) as total FROM esa_dim_issuer_c2 GROUP BY 1 ORDER BY total DESC LIMIT 5"
    df_issuer = get_data(issuer_query)
    
    if not df_issuer.empty:
        fig_issuer = px.bar(
            df_issuer, x='total', y='c2_common_name', orientation='h',
            color='total', color_continuous_scale='GnBu'
        )
        fig_issuer.update_layout(
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            font_color="#e8f4f0", margin=dict(t=20, b=0, l=0, r=0), height=300,
            xaxis_title=None, yaxis_title=None
        )
        st.plotly_chart(fig_issuer, use_container_width=True)

# --- 3. AUDIT TRAIL ---
st.markdown("### 📑 Transaction Log")
raw_query = "SELECT * FROM esa_fact_verifications ORDER BY f1_ingested_at DESC LIMIT 15"
df_raw = get_data(raw_query)

if not df_raw.empty:
    # Styling table biar ga hambar
    st.dataframe(
        df_raw.style.set_properties(**{'background-color': '#061628', 'color': '#8ab4a0', 'border-color': '#0a2040'}),
        use_container_width=True, hide_index=True
    )