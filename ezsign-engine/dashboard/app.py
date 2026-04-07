import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
from datetime import datetime, timedelta
import time 
import os

# --- [1] CONFIG & STYLING SECTION ---
st.set_page_config(page_title="EzSign Intelligent Analytics", layout="wide")

# Injecting Cyber aesthetic (Slightly updated for better contrast)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Syne:wght@800&family=DM+Mono&family=Outfit:wght@300;600&display=swap');
    
    .stApp { background-color: #030d1a; color: #e8f4f0; font-family: 'Outfit', sans-serif; }
    
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

# Path dinamis database
DB_PATH = "data/database.sqlite" if os.path.exists("data/database.sqlite") else "/data/database.sqlite"

def get_data(query):
    """Fungsi kurir untuk ambil data dari SQLite"""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            return pd.read_sql_query(query, conn)
    except Exception as e:
        return pd.DataFrame()

# --- [2] REAL-TIME HEADER & GLOBAL FILTER ---
now_wib = datetime.utcnow() + timedelta(hours=7)
tgl_skrg = now_wib.strftime("%d %B %Y")
jam_skrg = now_wib.strftime("%H:%M:%S")

# SIDEBAR: Kasta Shadcn UI Date Range
st.sidebar.markdown("### 📅 DATE RANGE (C3)")

# --- FIX START ---
# Ganti default start ke 2024 biar data lama/baru keliatan semua
start_date_val = datetime(2024, 1, 1) 
# End date tetep 'now', tapi pastiin dapet data sampe detik ini
end_date_val = now_wib 
# --- FIX END ---

selected_dates = st.sidebar.date_input(
    "Select Period",
    value=[start_date_val, end_date_val],
    label_visibility="collapsed"
)

# Logic biar gak error kalo user baru klik satu tanggal
if isinstance(selected_dates, list) and len(selected_dates) == 2:
    start_dt, end_dt = selected_dates
else:
    start_dt, end_dt = start_date_val, end_date_val

col_h1, col_h2 = st.columns([2, 1])
with col_h1:
    st.markdown(f"""
        <div style="border-left: 4px solid #10b981; padding-left: 15px;">
            <h1 style="font-family: 'Syne'; margin:0;">EZSIGN <span style="color:#34d399;">ANALYTICS</span></h1>
            <p style="color:#8ab4a0; font-size:14px;">Monitoring Digital Trust & Integrity • {start_dt.strftime('%d %b')} - {end_dt.strftime('%d %b %Y')}</p>
        </div>
    """, unsafe_allow_html=True)

with col_h2:
    st.markdown(f"""
        <div style="text-align:right; font-family:'DM Mono'; color:#34d399; font-size:16px; padding-top:10px; font-weight:bold;">
            <span style="color:#4a7060; font-size:10px;">LIVE_FEED_ACTIVE</span><br>
            {jam_skrg} <span style="font-size:10px; color:#4a7060;">UTC+7</span>
        </div>
    """, unsafe_allow_html=True)

st.write("---")

# --- [3] KPI LOGIC ---
# Pake datetime(...,) biar filter DATE-nya sinkron sama jam Indo 🛡️
kpi_query = f"""
SELECT 
    COUNT(*) as total,
    SUM(f1_is_trusted) as trusted,
    SUM(CASE WHEN f1_is_trusted = 0 THEN 1 ELSE 0 END) as untrusted,
    AVG(f1_validity_days) as avg_validity
FROM esa_fact_verifications
WHERE DATE(f1_signing_time) BETWEEN '{start_dt}' AND '{end_dt}'
"""

df_kpi = get_data(kpi_query)

# Kita pastiin variabelnya ada isinya, kalo NULL kita kasih 0
total_v = int(df_kpi["total"][0] or 0)
trusted_v = int(df_kpi["trusted"][0] or 0)
untrusted_v = int(df_kpi["untrusted"][0] or 0)
avg_v = int(df_kpi["avg_validity"][0] or 0)

# KITA TETEP TAMPILIN KOTAKNYA, BIAR GAK SEPI KASTA NPC 💅
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(f'<div class="kpi-container"><div class="kpi-label">Total Verifications</div><div class="kpi-val">{total_v:,}</div></div>', unsafe_allow_html=True)
with c2:
    st.markdown(f'<div class="kpi-container" style="border-left: 4px solid #34d399;"><div class="kpi-label">Trusted Docs</div><div class="kpi-val" style="color:#34d399;">{trusted_v}</div></div>', unsafe_allow_html=True)
with c3:
    st.markdown(f'<div class="kpi-container" style="border-left: 4px solid #ef4444;"><div class="kpi-label">Untrusted Docs</div><div class="kpi-val" style="color:#ef4444;">{untrusted_v}</div></div>', unsafe_allow_html=True)
with c4:
    st.markdown(f'<div class="kpi-container" style="border-left: 4px solid #fbbf24;"><div class="kpi-label">Avg Validity</div><div class="kpi-val" style="color:#fbbf24;">{avg_v}d</div></div>', unsafe_allow_html=True)

if total_v == 0:
    st.info(f"Kagak ada data di rentang {start_dt} sampe {end_dt}, Ca! 💅 Coba cek tahunnya jirr!")


# --- [4] VISUAL INTELLIGENCE (SIMPLIFIED ISO QUERY) ---
l_col, r_col = st.columns(2)

with l_col:
    st.markdown("### 🔍 Integrity Status")
    # Pake DATE() langsung, gak usah SUBSTR lagi jirr! 💅
    status_query = f"""
    SELECT c5.c5_status_type, COUNT(*) as count 
    FROM esa_fact_verifications f
    JOIN esa_dim_integrity_c5 c5 ON f.c5_integrity_key = c5.c5_integrity_key
    WHERE DATE(f.f1_signing_time) BETWEEN '{start_dt}' AND '{end_dt}'
    GROUP BY 1
    """
    df_status = get_data(status_query)
    
    if not df_status.empty:
        fig_status = px.pie(
            df_status, values='count', names='c5_status_type', hole=0.5,
            color='c5_status_type',
            color_discrete_map={'Trusted': '#10b981', 'Untrusted': '#ef4444', 'Warning': '#fbbf24'}
        )
        fig_status.update_layout(
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            font_color="#e8f4f0", margin=dict(t=30, b=0, l=0, r=0), height=350,
            legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5)
        )
        st.plotly_chart(fig_status, use_container_width=True)
    else:
        st.write("No integrity data for this period. 🌊")

with r_col:
    st.markdown("### 🏢 Top Issuer Performance")
    # Di sini juga bersihin SUBSTR-nya ya Ca! 🛡️
    issuer_query = f"""
    SELECT c2.c2_common_name, COUNT(*) as total 
    FROM esa_fact_verifications f
    JOIN esa_dim_issuer_c2 c2 ON f.c2_issuer_key = c2.c2_issuer_key
    WHERE DATE(f.f1_signing_time) BETWEEN '{start_dt}' AND '{end_dt}'
    GROUP BY 1 ORDER BY total DESC LIMIT 5
    """
    df_issuer = get_data(issuer_query)
    
    if not df_issuer.empty:
        fig_issuer = px.bar(
            df_issuer, x='total', y='c2_common_name', orientation='h',
            color='total', color_continuous_scale='GnBu'
        )
        fig_issuer.update_layout(
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            font_color="#e8f4f0", margin=dict(t=30, b=0, l=0, r=0), height=350,
            xaxis_title="Total Transactions", yaxis_title=None
        )
        st.plotly_chart(fig_issuer, use_container_width=True)
    else:
        st.write("No issuer data for this period. 🏢")

# --- [5] AUDIT TRAIL (THE SHADCN ULTIMATE) ---
st.markdown("### 📑 Forensic Transaction Log")

# Query sakti biar jam di tabel DAN filter tanggal sinkron WIB 🛡️
raw_query = f"""
SELECT 
    f.f1_doc_id as 'Doc ID',
    f.f1_is_trusted as 'StatusRaw',
    c2.c2_common_name as 'Issuer Authority',
    f.f1_ltv_status as 'LTV Status',
    c4.c4_corpo_name as 'Type',
    c5.c5_reason as 'Reasoning Analysis',
    f.f1_signing_time as 'Time' 
FROM esa_fact_verifications f
JOIN esa_dim_integrity_c5 c5 ON f.c5_integrity_key = c5.c5_integrity_key
JOIN esa_dim_issuer_c2 c2 ON f.c2_issuer_key = c2.c2_issuer_key
JOIN esa_dim_corporate_c4 c4 ON f.c4_corpo_key = c4.c4_corpo_key
WHERE DATE(f.f1_signing_time) BETWEEN '{start_dt}' AND '{end_dt}'
ORDER BY f.f1_id DESC
"""
df_all = get_data(raw_query)

if not df_all.empty:
    # Transformasi Status untuk filtering
    df_all['Status'] = df_all['StatusRaw'].apply(lambda x: "TRUSTED" if x == 1 else "UNTRUSTED")
    
    # --- UI SEARCH & FILTER BAR ---
    col_search, col_filter = st.columns([2, 1])
    
    with col_search:
        search_query = st.text_input("", placeholder="🔍 Search Doc ID or Issuer...", label_visibility="collapsed")
    
    with col_filter:
        status_filter = st.selectbox("", ["All Status", "TRUSTED", "UNTRUSTED"], label_visibility="collapsed")

    # --- FILTERING LOGIC ---
    # Filter by Search
    if search_query:
        df_all = df_all[
            df_all['Doc ID'].str.contains(search_query, case=False) | 
            df_all['Issuer Authority'].str.contains(search_query, case=False)
        ]
    
    # Filter by Status
    if status_filter != "All Status":
        df_all = df_all[df_all['Status'] == status_filter]

    # --- PAGINATION LOGIC ---
    rows_per_page = 10
    total_rows = len(df_all)
    total_pages = max((total_rows // rows_per_page) + (1 if total_rows % rows_per_page > 0 else 0), 1)
    
    if 'current_page' not in st.session_state: st.session_state.current_page = 1
    # Reset page kalau hasil filter lebih dikit dari page sekarang
    if st.session_state.current_page > total_pages: st.session_state.current_page = 1

    start_idx = (st.session_state.current_page - 1) * rows_per_page
    end_idx = min(start_idx + rows_per_page, total_rows)
    df_paged = df_all.iloc[start_idx:end_idx].drop(columns=['StatusRaw']).copy()

    # --- STYLING & RENDER ---
    def style_row(row):
        is_trusted = row['Status'] == 'TRUSTED'
        status_style = 'color: #10b981; font-weight: bold;' if is_trusted else 'color: #ef4444; font-weight: bold;'
        reason_style = 'color: #e8f4f0;' if is_trusted else 'color: #fbbf24; font-style: italic;'
        return ['', status_style, '', 'color: #34d399;', '', reason_style, '']

    st.dataframe(
        df_paged.style.apply(style_row, axis=1)
                     .set_properties(**{'background-color': '#030d1a', 'border-bottom': '1px solid #1e293b'}),
        use_container_width=True, hide_index=True
    )

    # --- SHADCN FOOTER ---
    st.write("")
    f_info, f_nav = st.columns([1, 1])
    with f_info:
        st.markdown(f"<p style='color: #64748b; font-size: 14px; margin-top: 10px;'>Showing {start_idx + 1}-{end_idx} of {total_rows} row(s)</p>", unsafe_allow_html=True)
    with f_nav:
        _, btn1, btn2 = st.columns([2, 1, 1])
        with btn1:
            if st.button("Previous", disabled=(st.session_state.current_page == 1), use_container_width=True):
                st.session_state.current_page -= 1
                st.rerun()
        with btn2:
            if st.button("Next", disabled=(st.session_state.current_page == total_pages), use_container_width=True):
                st.session_state.current_page += 1
                st.rerun()

# --- [W10] BEHAVIORAL & LOYALTY ANALYTICS 📈 ---
st.write("---")
st.markdown("### 🧬 Behavioral Intelligence ")

col_loyalty, col_churn = st.columns(2)

with col_loyalty:
    st.markdown("#### 🏆 Loyalty Score (By Frequency)")
    # Query buat ngitung siapa yang paling rajin verifikasi
    loyalty_query = f"""
    SELECT c4.c4_corpo_name as 'Organization', COUNT(f.f1_id) as 'Activity_Count'
    FROM esa_fact_verifications f
    JOIN esa_dim_corporate_c4 c4 ON f.c4_corpo_key = c4.c4_corpo_key
    WHERE DATE(f.f1_signing_time) BETWEEN '{start_dt}' AND '{end_dt}'
    GROUP BY 1 ORDER BY 2 DESC LIMIT 5
    """
    df_loyalty = get_data(loyalty_query)
    if not df_loyalty.empty:
        st.dataframe(df_loyalty, use_container_width=True, hide_index=True)
    else:
        st.write("No behavioral data yet. 🌊")

with col_churn:
    st.markdown("#### 🚩 Churn Risk (By Recency)")
    churn_query = f"""
    SELECT c4.c4_corpo_name as 'Organization', MAX(f.f1_signing_time) as 'Last_Seen'
    FROM esa_fact_verifications f
    JOIN esa_dim_corporate_c4 c4 ON f.c4_corpo_key = c4.c4_corpo_key
    GROUP BY 1
    HAVING Last_Seen < datetime('now', '-7 days') 
    """
    df_churn = get_data(churn_query)
    if not df_churn.empty:
        st.warning(f"Detected {len(df_churn)} Organizations at risk of Churn! 📉")
        st.dataframe(df_churn, use_container_width=True, hide_index=True)
    else:
        st.success("All users are actively engaged! ✨")                
# --- [6] THE MAGIC LOOP ---
time.sleep(2) # Kasih napas dikit jirr, biar nggak keberatan refresh
st.rerun()