# =============================================================================
# 🏢 EZSIGN INTELLIGENT ANALYTICS DASHBOARD - CORE VISUAL INTERACTION LAYER
# =============================================================================
# 📌 VERSI        : 1.0.0 (Enterprise Gold Release)
# 📅 TANGGAL UPDATE: 5 Juni 2026
# 🎓 KONTEKS MATKUL: 1. Integrated CRM & Behavioral Analytics (Topik 3)
#                    2. OLAP Analytics Dashboard & Deployment (Topik 5)
#                    3. Web Intelligence & Automated Data Scraping (Topik 4)
# 🛡️ REGULASI TI   : Kepatuhan UU PDP No. 27/2022 & UU ITE (Information Privacy)
# =============================================================================
# 🗺️ CATATAN DEPLOYMENT & ARSITEKTUR ALIRAN DATA (FOR NEXT DEVELOPER):
#
# 1. ARSITEKTUR INFRASTRUKTUR (DOCKER):
#    Dashboard ini terorkestrasi via Docker Compose sebagai service 'dashboard'
#    dan bergantung sepenuhnya (depends_on) pada service 'engine' (FastAPI).
#    Pastikan pemetaan volume lokal (Shared Volume) './data:/data' terpasang
#    sempurna agar dashboard dapat membaca database 'database.sqlite' yang
#    di-update secara real-time oleh API Ingestion Layer Next.js (save-log.js).
#
# 2. ALUR MANIPULASI DATA (OLAP INTERFACE):
#    - Data Ingestion Internal: Dari hit API Web Verify -> Next.js Gate -> SQLite.
#    - Data Ingestion Eksternal: Dari scraper_v1.py (The Hunter) -> intel_dataset.csv
#      -> wrangling_engine.py -> SQLite (Tabel: esa_dim_competitor_intel).
#    - Dashboard ini murni bertindak sebagai Read-Only OLAP Engine yang melakukan
#      operasi Slice & Dice via filter rentang tanggal (DATE RANGE C3), kotak
#      pencarian dinamis, dan dropdown seleksi status di tingkat runtime FE.
#
# 3. CORE ANALYTICS ENGINE (HYBRID SPK):
#    Model Penilaian Risiko menggunakan pendekatan Hybrid Expert System. Perhitungan
#    dilakukan row-by-row secara real-time menggabungkan logika AI Heuristic
#    Pattern Matching (deteksi string fraud 'Self-Signed'/'Untrusted') dengan
#    nilai konsensus optimasi MADM (Multi-Attribute Decision Making) melalui
#    metode linear SAW (Simple Additive Weighting) dan multiplikatif WP (Weighted Product).
#
# 4. OPTIMASI DESAIN INTERFASE (USER-CENTERED DESIGN):
#    Untuk menjaga efisiensi memori server dan meminimalisir re-render visual, 
#    komponen Market Intelligence menggunakan dekorator '@st.fragment(run_every="10m")'.
#    Hal ini mengisolasi pembaruan grafik tren harian Plotly dari file CSV staging 
#    setiap 10 menit tanpa mengganggu jalannya transaksi log forensik di atasnya.
# =============================================================================


import os
import sqlite3
import time
from datetime import datetime, timedelta, timezone
from click import style
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st
from PIL import Image
from streamlit_option_menu import option_menu
from streamlit_plotly_events import plotly_events
import streamlit as st
# =============================================================================
# --- [1] CONFIG & DATA VALIDATION ENGINES ---
# =============================================================================
# Taruh ini SEBELUM st.set_page_config

icon = Image.open("assets/LogoSign.png")

if st.query_params.get("nav") == "Forensic":
    st.session_state['current_page'] = "Forensic Log System"
    # Hapus parameter agar URL bersih
    st.query_params.clear() 
    st.rerun()

st.set_page_config(
    page_title="EzSign Intelligent Analytics", 
    page_icon=icon, # Pake objek gambar, bukan path string
    layout="wide"
)

# --- [0] AUTHENTICATOR SETUP ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

query_params = st.query_params
if query_params.get("nav") == ["forensic_untrusted"]:
    st.session_state['current_page'] = "Forensic Log System"
    st.session_state['status_filter'] = "Untrusted"
    st.query_params.clear()

# 2. CEK LOGIN
if not st.session_state['logged_in']:
    col_l, col_m, col_r = st.columns([1, 2, 1])
    with col_m:
        with st.form("login_form"):
            st.markdown("### 🔐 Login Access")
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Login")
            if submit:
                if username == "admin" and password == "ezsign2026":
                    st.session_state['logged_in'] = True
                    st.rerun() 
                else:
                    st.error("Username atau password salah!")
    st.stop() # Hentikan eksekusi di sini jika belum login

else:
    # --- PINTU TERBUKA: DASHBOARD LO DI SINI ---
    # Taruh tombol logout di sidebar agar gak ganggu konten utama
    with st.sidebar:
        if st.button("Logout"):
            st.session_state['logged_in'] = False
            st.rerun()
    # --- [1] FUNCTIONS ---

    def get_min_date():
        DB_PATH = "/data/database.sqlite"
        try:
            with sqlite3.connect(DB_PATH) as conn:
                result = conn.execute("SELECT MIN(DATE(f1_signing_time)) FROM esa_fact_verifications").fetchone()
                if result and result[0]:
                    return datetime.strptime(result[0], "%Y-%m-%d").date()
        except Exception as e:
            print(f"Error getting min date: {e}")
        return datetime(2026, 5, 22).date()
        
    def go_to_forensic(filter_value):
        st.session_state['current_page'] = "Forensic Log System"
        st.session_state['status_filter'] = filter_value # Ini kunci filternya
        st.rerun()

    def check_alerts(trusted_v, untrusted_v, total_v):
        perc_untrusted = (untrusted_v / total_v * 100) if total_v > 0 else 0
        if untrusted_v > 10:
            st.toast(f"🚨 ALERT: Persentase dokumen Untrusted mencapai {perc_untrusted:.1f}%!", icon="⚠️")

    def get_intel_data():
        current_dir = os.path.dirname(os.path.abspath(__file__))    
        root_dir = os.path.abspath(os.path.join(current_dir, ".."))
        path = os.path.join(root_dir, "data", "staging", "intel_dataset.csv")
        
        try:
            if os.path.exists(path):
                if os.path.getsize(path) == 0: 
                    st.warning("[VALIDATION WARNING] Berkas intel_dataset.csv terdeteksi kosong.")
                    return pd.DataFrame()
                    
                df = pd.read_csv(path)
                required_columns = ['timestamp', 'psre_name', 'file_name', 'source_url', 'status']
                
                if not all(col in df.columns for col in required_columns):
                    st.error("[VALIDATION FAILED] Struktur kolom CSV tidak mematuhi skema.")
                    return pd.DataFrame()
                    
                if 'timestamp' in df.columns:
                    df = df.sort_values(by='timestamp', ascending=False)
                return df.drop_duplicates().reset_index(drop=True)
            else:
                return pd.DataFrame()
        except Exception as e:
            st.error(f"❌ [CRITICAL SYSTEM ERROR] Gagal mengeksekusi validasi internal: {e}")
            return pd.DataFrame()

    @st.cache_data(ttl=600)
    def get_data(query):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        root_dir = os.path.abspath(os.path.join(current_dir, ".."))
        DB_PATH = "/data/database.sqlite"
        
        try:
            with sqlite3.connect(DB_PATH) as conn:
                return pd.read_sql_query(query, conn)
        except Exception as e:
            st.error(f"❌ Terjadi kesalahan kueri database SQLite: {e}")
            return pd.DataFrame()
        
    # --- LOGIKA AUTO-ADJUST PAGE SIZE ---
    if 'total_clicked' in st.session_state:
        val = st.session_state['total_clicked']
        
        if val <= 10:
            st.session_state['forensic_size'] = 10
        elif val <= 25:
            st.session_state['forensic_size'] = 25
        elif val <= 50:
            st.session_state['forensic_size'] = 50
        else:
            st.session_state['forensic_size'] = 100
            
        # Hapus agar tidak terus-terusan ngereset kalau user ganti size manual
        del st.session_state['total_clicked']
        
    def render_paginated_dataframe(df, key_prefix, config=None):
        state_key_page = f"{key_prefix}_page"
        state_key_size = f"{key_prefix}_size" 
        
        # 1. Inisialisasi default
        if state_key_size not in st.session_state:
            st.session_state[state_key_size] = 10
        if state_key_page not in st.session_state:
            st.session_state[state_key_page] = 1

        # 2. Fungsi reset halaman saat size diganti
        def reset_page():
            st.session_state[state_key_page] = 1

        # 3. Selectbox dengan on_change
        page_size = st.selectbox(
            "Tampilkan per halaman:", 
            [10, 25, 50, 100], 
            key=state_key_size,
            on_change=reset_page  # <--- INI BIAR GAK BUGGY
        ) 
        
        # 4. Logika Halaman
        total_rows = len(df)
        total_pages = max((total_rows // page_size) + (1 if total_rows % page_size > 0 else 0), 1)
        
        # Validasi supaya halaman gak melebihi total
        if st.session_state[state_key_page] > total_pages:
            st.session_state[state_key_page] = total_pages
        
        # 5. Slice Data
        start_idx = (st.session_state[state_key_page] - 1) * page_size
        
        # 6. Render Tabel
        st.dataframe(
            df.iloc[start_idx : start_idx + page_size], 
            use_container_width=True, 
            hide_index=True, 
            column_config=config
        )
        
        # 7. Navigasi
        cols = st.columns([2, 3, 2], vertical_alignment="center")
        
        if cols[0].button("Sebelumnya", key=f"{key_prefix}_prev", disabled=(st.session_state[state_key_page] == 1), use_container_width=True):
            st.session_state[state_key_page] -= 1
            st.rerun()

        cols[1].markdown(f"<p style='text-align:center;'>Halaman {st.session_state[state_key_page]} dari {total_pages}</p>", unsafe_allow_html=True)

        if cols[2].button("Selanjutnya", key=f"{key_prefix}_next", disabled=(st.session_state[state_key_page] == total_pages), use_container_width=True):
            st.session_state[state_key_page] += 1
            st.rerun()    
    
    # --- [2] CSS STYLING ---
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Syne:wght@800&family=DM+Mono&family=Outfit:wght@300;600&display=swap');
                
        /* Background Utama */
        .stApp { background-color: #0B1120 !important; }
                
        /* 1. Global Reset */
        .stApp { background-color: #030d1a !important; }
        [data-testid="stContainer"] { background-color: transparent !important; border: none !important; padding: 0 !important; }
        
        /* Class untuk judul yang 1 baris (Ringkasan) */
        .section-header-single {
            height: auto !important;
            display: flex;
            align-items: center;/* Teks di tengah secara vertikal */
            justify-content: space-between;
            padding-top: 10px !important; /* Sesuaikan jarak ke atas box */
        }

        /* Class untuk judul yang 2 baris (Performa) */
        .section-header-double {
            height: 60px !important;
            display: flex;
            align-items: flex-start; /* Teks mulai dari atas biar gak nabrak ke bawah */
            justify-content: space-between;
            padding-top: 10px !important; /* Lebih kecil angkanya supaya box Performa turun sedikit */
        
        }
                
        /* Class untuk judul yang 3 baris (audit) */
        .section-header-triple {
            height: 60px !important;
            display: flex;
            align-items: flex-start; /* Teks mulai dari atas biar gak nabrak ke bawah */
            justify-content: space-between;
            margin-top: -5px !important; /* Lebih kecil angkanya supaya box Performa turun sedikit */
        }

        .section-title, h3 { 
            font-family !important; 
            font-size: 28px !important;      /* Ukuran font seragam */
            font-weight: 800 !important;     /* Ketebalan seragam */
            margin-bottom: 1px !important; 
        }

        .text-green { 
            color: #34d399 !important; 
        }
                
       .custom-border-container {
            background-color: #0F172A;
            border-radius: 12px;
            padding: 20px;
            height: 100% !important;
            border: 1px solid #334155 !important; 
            display: flow-root;
            overflow: hidden !important;
            box-sizing: border-box !important;
            /* GANTI JADI SATU NILAI AJA: */
            margin-bottom: 20px !important; 
            margin-top: 0px !important;
        }
        
        
               
        .kpi-card {
            background-color: #0F172A !important;
            border: 1px solid rgba(16, 185, 129, 0.2) !important;
            border-radius: 16px !important;
            /* Padding bawah digedein (30px) biar teks ada napas dari garis */
            padding: 24px 24px 30px 24px !important; 
            height: 190px !important; /* Digeedein dikit lagi biar proporsional */
            display: flex;
            flex-direction: column;
            justify-content: flex-start;
            margin-bottom: 5px !important;
            position: relative; /* Wajib! */
            padding-bottom: 40px !important; /* Kasih ruang ekstra di bawah */
        }
                         
        .kpi-header { 
            display: flex; 
            justify-content: space-between; 
            align-items: center; 
            margin-bottom: 20px; /* Jarak header ke angka digedein */
        }
        
        .kpi-val { 
            font-family: 'Syne'; 
            font-size: 37px !important; /* Digeedein drastis! */
            font-weight: 800; 
            color: #cbd5e1 !important;
            margin-top: auto;        /* Dorong angka ke tengah secara vertikal */
            margin-bottom: auto;     /* Dorong angka ke tengah secara vertikal */
            text-align: center;      /* Rata tengah horizontal */
            width: 100%;             /* Pastiin dia ngambil lebar penuh */
            display: flex;
            justify-content: center;
            align-items: baseline;   /* Biar teks "Hari" sejajar sama dasar angka */
        }
        
        .kpi-subtext { 
            font-family: 'Outfit'; 
            font-size: 12px !important; 
            color: #94a3b8 !important;
            position: absolute; /* Maksa dia di bawah */
            bottom: 20px;       /* Jarak dari garis bawah card */
            left: 20px;         /* Jarak dari garis kiri card */
            line-height: 1.2;
        }

        /* --- Tooltip HOVER Mode (Berlaku untuk semua) --- */
        .info-wrapper {
            position: relative;
            display: inline-block;
            margin-left: 6px;
            z-index: 9999;
        }
                
        /* Gabungin style biar KPI dan Chart sama-sama jadi tangan & nyala hijau */
        .info-icon, .info-btn {
            color: #9CA3AF !important; /* Warna default abu-abu */
            cursor: pointer !important; /* Biar jadi tangan pas di-hover */
            font-size: 15px !important;
            transition: color 0.2s ease !important;
        }

        /* Pas di-hover, dua-duanya bakal jadi hijau */
        .info-wrapper:hover .info-icon, 
        .info-wrapper:hover .info-btn {
            color: #34d399 !important; 
        }
                
        .info-btn {
            background: none !important;
            border: none !important;
            color: #9CA3AF !important;
            font-size: 15px !important;
            cursor: pointer !important;
            padding: 0 !important;
            outline: none !important;
            font-family: 'Outfit', sans-serif !important;
            transition: color 0.2s !important;
        }
        
        .info-btn:hover { color: #34d399 !important; }
                
        /* Box Penjelasan (Pop-up) */
        .info-popup {
            position: absolute !important;
            /* UBAH DARI BOTTOM KE TOP */
            top: 130% !important; 
            bottom: auto !important; 
            left: 50% !important;
            transform: translateX(-50%) translateY(0px) !important;
            width: 200px !important; 
            background-color: #020617 !important;
            color: #e8f4f0 !important;
            padding: 8px 12px !important;
            border-radius: 6px !important;
            font-size: 10px !important;
            line-height: 1.3 !important;
            border: 1px solid #334155 !important;
            box-shadow: 0 4px 12px rgba(0,0,0,0.5) !important;
            
            /* Animasi Hover */
            visibility: hidden;
            opacity: 0;
            pointer-events: none; 
            transition: opacity 0.2s ease, transform 0.2s ease !important;
            z-index: 99999 !important;
        }
        
        /* Trigger: Pas wrapper di-hover, popup muncul */
        .info-wrapper:hover .info-popup {
            visibility: visible !important;
            opacity: 1 !important;
            transform: translateX(-50%) translateY(0) !important;
        }
                
        .info-wrapper {
            position: relative;
            display: inline-flex !important; /* Ganti dari inline-block */
            align-items: center;
            vertical-align: middle;
            margin-left: 8px;
        }
        
        /* Biar container-nya gak motong tooltip */
        .custom-border-container {
            overflow: visible !important; 
            padding-top: 10px !important; /* Kurangi padding atas biar chart naik */
            margin-top: 0 !important;
        }
        
        /* Biar header lo nggak narik spasi ke bawah */
        .header-flex {
            margin-bottom: 5px !important; 
        }
                
        /* Stat Cards (Compact & Elegant) */
        .stat-card-green, .stat-card-red { 
            border-radius: 10px !important; 
            padding: 6px 10px !important;  /* Padding lebih tipis */
            margin-bottom: 8px !important;
            text-align: center !important;
            display: flex;
            flex-direction: column;
            justify-content: center;
            height: 90px; /* Dikecilin lagi biar makin kompak */
            width: 90px; /* Kasih lebar fix biar dia gak melar ke kanan */
            margin-left: -50px; /* Rata kanan di kolom stat */
        }
        
        .stat-card-green { 
            background: #0f1d18 !important; 
            border: 1px solid #10b981 !important; 
            color: #10b981 !important;
        }
        
        .stat-card-red { 
            background: #1e1111 !important; 
            border: 1px solid #ef4444 !important; 
            color: #ef4444 !important;
        }
        
        .stat-val { font-family: 'Syne'; font-size: 18px !important; font-weight: 800; line-height: 1;}
        .stat-label { font-family: 'Outfit'; font-size: 9px !important; color: #e8f4f0; margin-top: 2px; line-height: 1.1; }
                
        /* CSS buat ngeratain tinggi card */
        [data-testid="column"] {
            display: flex;
            flex-direction: column;
            padding-left: 10px !important;
            padding-right: 10px !important;
        }
        
        [data-testid="column"] > div {
            display: flex;
            flex: 1;
        }
        
        [data-testid="stDataFrame"] {
            font-family: 'Outfit', sans-serif !important;
        }

        /* Paksa juga font di dalam header tabel dan isi sel tabel */
        [data-testid="stDataFrame"] div, 
        [data-testid="stDataFrame"] span, 
        [data-testid="stDataFrame"] p {
            font-family: 'Outfit', sans-serif !important;
            font-size: 13px !important; /* Biar lebih lega */
            color: #f8fafc !important;
        }
                
        .kpi-card:hover {
    background-color: #1e293b !important; /* Pas di-hover, warna agak naik biar kerasa bedanya */
    border: 1px solid #34d399 !important; /* Border nyala hijau */
    transition: all 0.2s ease-in-out;
}

                .kpi-label {
    color: #e2e8f0 !important;
    font-weight: 600 !important;
}

        [data-testid="column"] [data-testid="stContainer"] {
            height: 100% !important;
            display: flex;
            flex-direction: column;
        }
        
        .equal-card {
            height: 100% !important; 
            display: flex;
            flex-direction: column;
            justify-content: flex-start; /* Judul tetap di atas */
            align-items: stretch;        /* Tabel tetep lebar */
        }
                
        /* 1. Paksa sidebar biar gak ada scroll */
        [data-testid="stSidebar"]* {
            overflow: hidden !important;
            font-family: 'sans-serif' !important;
            background-color: #0F172A !important;
        }

        /* 2. Compact-in elemen sidebar */
        [data-testid="stSidebar"] .block-container {
        padding-top: 1rem !important;
        padding-bottom: 0rem !important;
        }

        /* 3. Bikin date input lebih lega */
        [data-testid="stDateInput"] {
            margin-top: 8px !important; /* Kasih jarak sama teks */
            margin-bottom: 25px !important; /* Kasih jarak sama elemen bawahnya */
        }
        
        /* Bikin teks label lebih menonjol */
        .monitoring-label {
            color: #34d399 !important; 
            font-size: 11px !important; 
            font-weight: bold !important; 
            margin-top: 30px !important;
            margin-bottom: 5px !important;
            letter-spacing: 0.5px;
        }

        /* 4. Kecilin jarak antar elemen */
        [data-testid="stSidebar"] > div > div {
            gap: 5px !important;
                            
        /* Typography Modern */
        h3 { color: #34d399 !important; font-family: 'Syne' !important; font-size: 18px !important; margin-bottom: 20px !important; }

        /* 1. Reset semua button biar gak ada bentuk kotak default Streamlit */
        div[data-testid="stButton"] button {
            background-color: transparent !important;
            border: none !important;
            padding: 0 !important;
            margin: 0 !important;
            width: 100% !important;
            height: auto !important;
            display: block !important;
            box-shadow: none !important; /* Hilangin bayangan tombol */
            text-align: left !important;
            color: inherit !important; /* Biar warna teks ngikutin card */
        }

        /* 2. Hilangkan efek hover biru aneh */
        div[data-testid="stButton"] button:hover, 
        div[data-testid="stButton"] button:focus, 
        div[data-testid="stButton"] button:active {
            background-color: transparent !important;
            border: none !important;
            box-shadow: none !important;
            outline: none !important;
        }
                
        div[data-testid="stFormSubmitButton"] button p {
            color: transparent !important;
        }
        /* Biar tombol form tetap mengisi seluruh area card */
        div[data-testid="stFormSubmitButton"] button {
            background: transparent !important;
            border: none !important;
            width: 100% !important;
            height: 100% !important;
            position: absolute !important;
            top: 0 !important;
            left: 0 !important;
            z-index: 10 !important;
        }
                
        .sticky-header-container {
            position: sticky;
            top: 0;
            z-index: 9999;
            background-color: #0b111d;
            padding: 10px 0;
            border-bottom: 1px solid #1e293b;
            
            display: flex !important;
            align-items: flex-start !important; /* GANTI JADI FLEX-START BIAR NAMPEL DI ATAS */
            justify-content: space-between;
        }
        
        /* Biar konten di bawahnya gak ketutup header saat discroll */
        .block-container {
            padding-top: 120px !important;
        }
        /* Paksa background utama tetep gelap */
        .stApp {
            background-color: #030d1a !important;
        }
        /* Paksa teks jadi cerah */
        div, p, h1, h2, h3, h4, span, label {
            color: #e8f4f0 !important;
        }
                
        /* Wrapper biar ikon nempel */
        .info-wrapper {
            position: relative;
            display: inline-flex;
            align-items: center;
        }

        /* Ikon jadi tangan & bisa hijau */
        .info-btn {
            background: none !important;
            border: none !important;
            color: #9CA3AF !important;
            cursor: pointer !important;
            font-size: 16px !important;
            padding: 0 !important;
            transition: color 0.2s ease !important;
        }

        .info-btn:hover {
            color: #34d399 !important;
        }

        /* Popup yang nempel pas di bawah ikon */
        .info-popup {
            position: absolute;
            top: 130% !important; /* Pas banget di bawah ikon */
            right: 0 !important;
            width: 220px !important;
            background-color: #020617 !important;
            color: #e8f4f0 !important;
            padding: 10px 12px !important;
            border-radius: 6px !important;
            font-size: 11px !important;
            line-height: 1.4 !important;
            border: 1px solid #475569 !important;
            visibility: hidden;
            opacity: 0;
            z-index: 9999999 !important;
            pointer-events: none; 
            transition: opacity 0.2s ease, transform 0.2s ease !important;
        }

        .info-wrapper:hover .info-popup {
            visibility: visible !important;
            opacity: 1 !important;
        }
                  
    </style>
    """, unsafe_allow_html=True)

    now_wib = datetime.now(timezone.utc) + timedelta(hours=7)
    tgl_skrg = now_wib.strftime("%d %B %Y")
    jam_skrg = now_wib.strftime("%H:%M:%S")



    # =============================================================================
    # --- [2] SIDEBAR LAYER ---
    # =============================================================================
    with st.sidebar:
        # 1. CSS biar kolom dan logo beneran sejajar tengah
        st.markdown("""
            <style>
                .sidebar-logo-row { 
                    display: flex !important; 
                    align-items: center !important; 
                    justify-content: center !important; /* Biar ke-tengah */
                    gap: 10px !important; 
                    margin-bottom: 15px !important;
                }
                .logo-wrapper {
                    background: white !important;
                    border-radius: 6px !important; /* Dikit aja biar gak bulet */
                    padding: 4px !important;
                    width: 35px !important;
                    height: 35px !important;
                    display: flex !important;
                    align-items: center !important;
                    justify-content: center !important;
                }
                .sign-text { 
                    color: #e8f4f0 !important; 
                    font-family: sans-serif !important; /* Harus sama */
                    font-size: 24px !important; 
                    font-weight: 700 !important;
                    margin: 0 !important;
                }
                .date-box {
                    background: #0d1726 !important;
                    padding: 10px !important;
                    border-radius: 8px !important;
                    border: 1px solid #10b98120 !important;
                }
                [data-testid="stDateInput"] {
                    margin-top: 8px !important; /* Kasih jarak sama teks */
                    margin-bottom: 25px !important; /* Kasih jarak sama elemen bawahnya */
                }
                .monitoring-label {
                    color: #34d399 !important; 
                    font-size: 11px !important; 
                    font-weight: bold !important; 
                    margin-top: 30px !important;
                    margin-bottom: 5px !important;
                    letter-spacing: 0.5px;
                }
                    .stMarkdown, .stText, .stButton, .stSelectbox {
                    font-family: sans-serif !important;
                }
                    
                @keyframes blink-red {
                    0% { border: 2px solid #ef4444; box-shadow: 0 0 10px #ef4444; }
                    50% { border: 2px solid transparent; box-shadow: none; }
                    100% { border: 2px solid #ef4444; box-shadow: 0 0 10px #ef4444; }
                }
                    
                .alert-pulse {
                    animation: blink-red 2s infinite;
                }
            </style>
        """, unsafe_allow_html=True)

        # 2. Panggil HTML row-nya (Gak perlu pake st.columns, pake flexbox langsung lebih rapi)
        import base64
        def get_image_base64(path):
            with open(path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode()

        img_b64 = get_image_base64("assets/LogoSign.png")
        
        st.markdown(f"""
            <div class="sidebar-logo-row">
                <div class="logo-wrapper">
                    <img src="data:image/png;base64,{img_b64}" width="30">
                </div>
                <div class="sign-text">Sign</div>
            </div>
        """, unsafe_allow_html=True)
        
        # 3. Judul NAVIGATOR (tetap di bawah)
        st.markdown("""
            <div style='text-align: center; margin-top: 5px; margin-bottom: 20px;'>
                <h2 style='color: #34d399; font-family: "Syne"; font-size: 16px; margin: 0;'>NAVIGATOR</h2>
                <p style='color: #4a7060; font-family: "DM Mono"; font-size: 12px;'>INTELLIGENCE LAYER V1.0</p>
            </div>
        """, unsafe_allow_html=True)
        
        
        st.markdown("---")

        # 1. Tentukan index menu berdasarkan session_state
        menu_map = ["Dashboard Analytics", "Forensic Log System", "Competitor Intel"]

        # Ambil current_page dari session_state, default ke "Dashboard Analytics"
        current_page = st.session_state.get('current_page', "Dashboard Analytics")
        default_idx = menu_map.index(current_page) if current_page in menu_map else 0

        # 2. Update option_menu
        selected_menu = option_menu(
            menu_title=None,
            options=menu_map,
            icons=["house-door", "shield-lock", "radar"],
            menu_icon="cast",
            default_index=default_idx,
            styles={
                "container": {"padding": "0!important", "background-color": "transparent"},
                "icon": {"color": "white", "font-size": "18px"},
                "nav-link": {
                    "font-size": "14px",
                    "font-family": "sans-serif",
                    "text-align": "left",
                    "margin": "0px",
                    "--hover-color": "#1f2937",
                },
                "nav-link-selected": {
                    "background-color": "#10b981",
                    "color": "white"
                }
            }
        )

        # 3. Sinkronisasi session_state
        if selected_menu != st.session_state.get('current_page'):
            st.session_state['current_page'] = selected_menu
            st.rerun() # Penting buat nge-update tampilan sidebar & konten utama

        # --- [2] SIDEBAR LAYER ---
        st.markdown("---")
        with st.sidebar:
            st.markdown("<p class='monitoring-label'>📅 RENTANG WAKTU PEMANTAUAN</p>", unsafe_allow_html=True)
            

            min_db_date = get_min_date()
            
            if 'date_range' not in st.session_state:
                st.session_state.date_range = (min_db_date, now_wib.date())

            selected_dates = st.date_input(
                "Jangka Waktu",
                value=st.session_state.date_range,
                min_value=min_db_date,
                max_value=now_wib.date(),
                key="date_range",
                label_visibility="collapsed"
            )

            if isinstance(selected_dates, tuple) and len(selected_dates) == 2:
                start_dt, end_dt = selected_dates
            else:
                start_dt = selected_dates[0] if isinstance(selected_dates, (list, tuple)) else selected_dates
                end_dt = now_wib.date()
            # --------------------------------
   
            st.markdown("""
                <div style="border-top: 1px solid #10b98120; padding-top: 15px;">
                    <div style="display: flex; align-items: center; gap: 10px;">
                        <div style="width: 32px; height: 32px; background: #063826; border-radius: 50%; display: flex; align-items: center; justify-content: center; color: #34d399; font-weight: bold; font-size: 14px;">A</div>
                        <div style="display: flex; flex-direction: column;">
                            <span style="color: #e8f4f0; font-size: 12px; font-weight: 600;">Admin</span>
                            <span style="color: #64748b; font-size: 10px;">Analyst Intern</span>
                        </div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

    # --- [2.1] HEADER STICKY ---
    st.markdown('<div class="sticky-header-container">', unsafe_allow_html=True)

    col_h1, col_h2 = st.columns([2, 1])

    # --- FRAGMENT BIAR JAM UPDATE ---
    @st.fragment(run_every="1s") 
    def show_live_clock():
        import datetime
        wib_time = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=7))).strftime("%H:%M:%S")
        st.markdown(f"""
            <div style="text-align: right; font-family: 'DM Mono'; color: #34d399; font-size: 16px; font-weight: bold;">
                <span style="color: #4a7060; font-size: 10px;">LIVE FEED ACTIVE</span><br>
                {wib_time} <span style="font-size: 10px; color: #4a7060;">WIB (UTC+7)</span>
            </div>
        """, unsafe_allow_html=True)

    with col_h1:
        st.markdown(f"""<div style="border-left: 4px solid #10b981; padding-left: 15px; margin-top: 5px;">
        <h1 style="font-family: 'Syne'; margin:0; font-size: 36px; line-height: 1;">EZSIGN<span style="color: #34d399;"> ANALYTICS</span></h1>
        <p style="color:#8ab4a0; font-size:14px; margin-top: 8px;">Monitoring Digital Trust & Integrity • {start_dt.strftime('%d %b %Y')} - {end_dt.strftime('%d %b %Y')}</p>
        </div>""", unsafe_allow_html=True)

    with col_h2:
        # Panggil fungsi jam
        show_live_clock() 

        # Clean, functional, and efficient. 
        # Stop overcomplicating, sis.
        if st.button("🔄 Update Dashboard", use_container_width=True):
            with st.spinner("Fetching fresh data..."):
                # If you have a specific function to reload data, call it here
                # e.g., load_data.clear() 
                time.sleep(1) 
                st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)

    # =============================================================================
    # --- [3] LOGIC NAVIGASI MENU UTAMA ---
    # =============================================================================

    if selected_menu == "Dashboard Analytics":
        alert_query = f"""
            SELECT COUNT(*) as jumlah 
            FROM esa_fact_verifications f
            JOIN esa_dim_corporate_c4 c4 ON f.c4_corpo_key = c4.c4_corpo_key
            GROUP BY c4.c4_corpo_name 
            HAVING MAX(f.f1_signing_time) < datetime('now', '-7 days')
        """
        df_churn_check = get_data(alert_query)
        
        # Pake .iloc[0,0] buat ambil angkanya dari hasil COUNT
        if not df_churn_check.empty:
            jml_risiko = len(df_churn_check) # Atau df_churn_check.iloc[0,0]
            st.error(f"⚠️ **Perhatian:** Ada {jml_risiko} organisasi dengan risiko Churn tinggi dalam 7 hari! Cek tab **Competitor Intel** untuk detail mitigasi.")    

        # --- BREADCRUMB & HIGHLIGHT SUMMARY (Menjawab Prioritas 2) ---
        st.markdown("<p style='color:#9CA3AF; font-size:14px; margin-bottom:15px;'>Dashboard Analytics > <b>Overview</b></p>", unsafe_allow_html=True)

        # 1. KPI SECTION (Bungkus pake class 'kpi-card')
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

        if not df_kpi.empty:
            total_v = int(df_kpi["total"].iloc[0] or 0)
            trusted_v = int(df_kpi["trusted"].iloc[0] or 0)
            untrusted_v = int(df_kpi["untrusted"].iloc[0] or 0)
            avg_v = int(df_kpi["avg_validity"].iloc[0] or 0)

            perc_trusted = (trusted_v / total_v * 100) if total_v > 0 else 0
            perc_untrusted = (untrusted_v / total_v * 100) if total_v > 0 else 0

            is_untrusted_alert = untrusted_v > 10 # Threshold bisa disesuaikan
            if is_untrusted_alert:
                check_alerts(trusted_v, untrusted_v, total_v)

            c1, c2, c3, c4 = st.columns(4)

            def navigate_to_forensic(page, filter_key, filter_val, total=None):
                st.session_state['current_page'] = page
                st.session_state[filter_key] = filter_val
                if total is not None:
                    st.session_state['total_clicked'] = total
                st.rerun()

            st.markdown("""
                <style>
                /* CSS ini buat tombol tombol Streamlit "hilang" dan menutupi kartu */
                [data-testid="column"] button {
                    opacity: 0 !important;
                    position: absolute !important;
                    top: 0 !important;
                    left: 0 !important;
                    width: 100% !important;
                    height: 100% !important;
                    z-index: 10 !important;
                    cursor: pointer !important;
                    pointer-events: auto !important;
                }
                div[data-testid="column"] { position: relative !important; }
                        
                [data-testid="column"]:hover .kpi-card {
                    background-color: #1e293b !important;
                    border: 1px solid #34d399 !important;
                    box-shadow: 0 0 15px rgba(52, 211, 153, 0.2) !important;
                    transition: all 0.2s ease-in-out !important;
                </style>
            """, unsafe_allow_html=True)

            # DI DALAM COLUMN:docker-compose down
            with c1:
                if st.button(" ", key="btn_total", use_container_width=True, 
                        on_click=lambda: navigate_to_forensic("Forensic Log System", "status_filter", "Semua Status (All)", total=total_v)):
                    pass

                card_class = "kpi-card alert-pulse" if is_untrusted_alert else "kpi-card"
                st.markdown(f"""
                    <div style="margin-top: -65px; pointer-events: none;">
                        <div class={card_class}>
                            <div class="kpi-header">
                                <div class="kpi-label" style="display:flex; align-items:center;">
                                    Total Verifikasi
                                    <div class="info-wrapper" style="pointer-events: auto;">
                                        <button class="info-btn">ⓘ</button>
                                        <div class="info-popup">Total dokumen digital yang diproses sistem.<br><br>💡 <b>Action:</b> Klik kartu ini untuk mereset filter dan melihat seluruh log transaksi.</div>
                                    </div>
                                </div>
                                <div>📋</div>
                            </div>
                            <div class="kpi-val">{total_v:,}</div>
                            <div class="kpi-subtext">Jan 2024 - Jun 2026</div>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
                                

            with c2:
                if st.button(" ", key="btn_trusted", use_container_width=True, 
                        on_click=lambda: navigate_to_forensic("Forensic Log System", "status_filter", "TRUSTED", total=trusted_v)):
                    pass

                card_class = "kpi-card alert-pulse" if is_untrusted_alert else "kpi-card"
                st.markdown(f"""
                <div style="margin-top: -65px; pointer-events: none;">
                    <div class={card_class}>
                        <div class="kpi-header">
                            <div class="kpi-label" style="display:flex; align-items:center;">
                                Trusted
                                <div class="info-wrapper" style="pointer-events: auto;">
                                    <button class="info-btn" type="button" onclick="event.stopPropagation();">ⓘ</button>
                                    <div class="info-popup">Dokumen sah secara kriptografi.<br><br>💡 <b>Action:</b> Klik kartu ini untuk memfilter khusus dokumen berstatus aman.</div>
                                </div>
                            </div>
                            <div>✅</div>
                        </div>
                        <div class="kpi-val" style="color:#10b981;">{trusted_v:,}</div>
                        <div class="kpi-subtext">{perc_trusted:.1f}% dari total</div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

            with c3:
                if st.button(" ", key="btn_untrusted", use_container_width=True, 
                        on_click=lambda: navigate_to_forensic("Forensic Log System", "status_filter", "UNTRUSTED", total=untrusted_v)):
                    pass
                
                card_class = "kpi-card alert-pulse" if is_untrusted_alert else "kpi-card"
                st.markdown(f"""
                    <div style="margin-top: -65px; pointer-events: none;">
                        <div class="{card_class}" style="height: 100%;">
                            <div class="kpi-header">
                                <div class="kpi-label" style="display:flex; align-items:center;">
                                    Untrusted { "⚠️" if is_untrusted_alert else "❌" }
                                    <div class="info-wrapper" style="pointer-events: auto;">
                                        <button class="info-btn" type="button" onclick="event.stopPropagation();">ⓘ</button>
                                        <div class="info-popup">Dokumen gagal verifikasi / anomali.<br><br>💡 <b>Action:</b> Klik kartu ini untuk menginvestigasi log dokumen bermasalah.</div>
                                    </div>
                                </div>
                            </div>
                            <div class="kpi-val" style="color:#ef4444;">{untrusted_v:,}</div>
                            <div class="kpi-subtext">{perc_untrusted:.1f}% dari total</div>
                        </div>
                    </div>
                """, unsafe_allow_html=True)

            with c4:
                if st.button(" ", key="btn_validity", use_container_width=True,
                        on_click=lambda: [
                            st.session_state.update({'current_page': "Forensic Log System", 'validity_filter': "Expiring Soon", 'total_clicked': total_v}), 
                            st.rerun()
                        ]):
                    pass
                st.markdown(f"""
                <div style="margin-top: -65px; pointer-events: none;">
                    <div class="kpi-card" style="height: 100%;">
                        <div class="kpi-header">
                            <div class="kpi-label" style="display:flex; align-items:center;">
                                Validity
                                <div class="info-wrapper" style="pointer-events: auto;">
                                    <button class="info-btn" type="button" onclick="event.stopPropagation();">ⓘ</button>
                                    <div class="info-popup">Rata-rata sisa masa aktif sertifikat.<br><br>💡 <b>Action:</b> Klik kartu ini untuk memantau dokumen yang hampir <i>expired</i>.</div>
                                </div>
                            </div>
                            <div>⏱️</div>
                        </div>
                        <div class="kpi-val" style="color:#fbbf24;">{avg_v} <span style="font-size: 15px; font-weight: normal; margin-left: 5px;">Hari</span></div>
                        <div class="kpi-subtext">Rata-rata durasi validitas</div>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            if total_v == 0:
                st.info(f"Informasi: Tidak ditemukan data verifikasi transaksi pada rentang periode ini.")
    
        # 2. CHARTS SECTION
        l_col, r_col = st.columns(2)

        with l_col:
            with st.container(border=True):
                st.markdown('''
                    <div class="section-header-single">
                <h3 class="section-title">🔍 Ringkasan Status Integritas</h3>
                <div class="info-wrapper">
                    <span class="info-btn">ⓘ</span>
                    <div class="info-popup">Rasio dokumen valid vs tidak valid.<br><br>💡 <b>Pro-Tip:</b> Klik pada potongan donat warna merah/hijau untuk langsung memfilter tabel forensik di bawah.</div>
                </div>
            </div>
                ''', unsafe_allow_html=True)
                # --- Perhitungan Data --
                status_query = f"""
                SELECT c5.c5_status_type, COUNT(*) as count 
                FROM esa_fact_verifications f
                JOIN esa_dim_integrity_c5 c5 ON f.c5_integrity_key = c5.c5_integrity_key
                WHERE DATE(f.f1_signing_time) BETWEEN '{start_dt}' AND '{end_dt}'
                GROUP BY 1 
                """
                df_status = get_data(status_query)
                
                if not df_status.empty:
                    df_status['c5_status_type_clean'] = df_status['c5_status_type'].str.strip().str.lower()    

                    t_val = df_status.loc[df_status['c5_status_type_clean'] == 'valid_ideal', 'count'].sum()
                    u_val = df_status.loc[df_status['c5_status_type_clean'] == 'untrusted', 'count'].sum()
                    total_sum = df_status['count'].sum()
                    trusted_pct = (t_val / total_sum * 100) if total_sum > 0 else 0

                    col_chart, col_stats = st.columns([2, 1], vertical_alignment="center")

                    with col_chart:
                        fig_status = px.pie(
                            df_status, values='count', names='c5_status_type', hole=0.6,
                            color='c5_status_type',
                            color_discrete_map={'Valid & Ideal': '#10b981', 'Untrusted': '#ef4444', 'Warning': '#fbbf24'}
                        )
                        
                        # 2. Update layout & warna agar tidak hitam/gelap
                        fig_status.update_layout(
                            paper_bgcolor='rgba(0,0,0,0)',
                            plot_bgcolor='rgba(0,0,0,0)',
                            font_color="#e8f4f0",
                            margin=dict(t=30, b=38, l=1, r=10),
                            height=300,
                            showlegend=False
                        ) 

                        
                        # Urutan ini harus SESUAI dengan urutan kategori di df_status lo
                        fig_status.update_traces(
                            marker=dict(colors=['#ef4444', '#10b981', '#fbbf24f']), # Marker cuma buat warna
                            hole=0.6,                                             # hole ditaruh di luar marker
                            domain=dict(x=[0, 0.7], y=[0, 1]),        # domain juga di luar marker
                            automargin=True,

                            # KUNCI 1: Custom isi tulisan biar gak ada "c5_status_type="
                            hovertemplate="Status: %{label}<br>Total: %{value}<extra></extra>",
                            
                            # KUNCI 2: Custom warna box biar gak nabrak warna donat
                            hoverlabel=dict(
                                bgcolor="#1e293b", # Warna background box (misal abu-abu gelap)
                                font_color="white", # Warna tulisan
                                bordercolor="#334155" # Warna garis pinggir box
                            )
                        )
                        
                        fig_status.add_annotation(
                            text=f"{int(trusted_pct)}%<br>TRUSTED", 
                            x=0.35,              # Titik tengah domain x=[0, 0.7] adalah 0.35
                            y=0.5,               # Titik tengah domain y=[0, 1] adalah 0.5
                            showarrow=False, 
                            font=dict(size=16, color='white')
                        )

                        # 4. Panggil plotly_events
                        selected_points = plotly_events(fig_status, click_event=True, select_event=False, override_height=300)

                        # 5. Filter Logic (TETAP SAMA, karena mapping status nama gak berubah)
                        # 5. Filter Logic (Update bagian ini di bawah plotly_events)
                    if selected_points:
                        try:
                            clicked_idx = selected_points[0]['pointNumber']
                            status_terpilih = df_status.iloc[clicked_idx]['c5_status_type']
                            total_data = df_status.iloc[clicked_idx]['count'] # <--- AMBIL TOTAL DATA DARI SINI
                            
                            # Mapping status yang lebih aman
                            if "untrusted" in status_terpilih.lower():
                                target_status = "UNTRUSTED"
                            elif "valid" in status_terpilih.lower():
                                target_status = "TRUSTED"
                            else:
                                target_status = "Semua Status (All)"
                                
                            # Kirim ke Forensic
                            st.session_state['status_filter'] = target_status
                            st.session_state['total_clicked'] = int(total_data) # <--- KIRIM TOTALNYA
                            st.session_state['current_page'] = "Forensic Log System"
                            st.rerun()
                            
                        except Exception as e:
                            st.error(f"Error saat klik: {e}")
                            

                    with col_stats:
                        st.markdown(f'''<div class="stat-card-green">
                            <div class="stat-val">{t_val}</div>
                            <div class="stat-label">Valid & Ideal</div>
                        </div>''', unsafe_allow_html=True)
                        st.markdown(f'''<div class="stat-card-red">
                            <div class="stat-val">{u_val}</div>
                            <div class="stat-label">Untrusted</div>
                        </div>''', unsafe_allow_html=True)
                else:
                    st.write("Data ringkasan integritas tidak tersedia untuk periode ini.")


        with r_col:
             with st.container(border=True):
                st.markdown('''
                    <div class="section-header-double">
                        <h3 class="section-title">🏢 Performa Volume Penerbit Sertifikat</h3>
                        <div class="info-wrapper">
                            <span class="info-btn">ⓘ</span>
                            <div class="info-popup">Top 5 Issuer Authority tertinggi.<br><br>💡 <b>Pro-Tip:</b> Klik salah satu batang grafik untuk menelusuri riwayat transaksi khusus dari vendor tersebut.</div>
                        </div>
                    </div>
                ''', unsafe_allow_html=True)
                issuer_query = f"""
                SELECT c2.c2_common_name, COUNT(*) as total 
                FROM esa_fact_verifications f
                JOIN esa_dim_issuer_c2 c2 ON f.c2_issuer_key = c2.c2_issuer_key
                WHERE DATE(f.f1_signing_time) BETWEEN '{start_dt}' AND '{end_dt}'
                GROUP BY 1 ORDER BY total DESC LIMIT 5
                """
                df_issuer = get_data(issuer_query)
                
                if not df_issuer.empty:
                    # Rename DataFrame khusus untuk Plotly agar aman
                    df_issuer_clean = df_issuer.copy()
                    df_issuer_clean = df_issuer_clean.rename(columns={'total': 'Value'})

                    fig_issuer = px.bar(
                        df_issuer_clean, 
                        x='Value', 
                        y='c2_common_name', 
                        orientation='h',
                        color='Value', 
                        color_continuous_scale='GnBu', 
                        color_continuous_midpoint=df_issuer['total'].mean(), 
                        height=200,
                        labels={'Value': 'Total'} 
                    )
                    
                    # 1. Update Traces cukup untuk hovertemplate
                    fig_issuer.update_traces(
                        hovertemplate="<b>%{y}</b><br>Total: %{x}<extra></extra>"
                    )
                    
                    # 2. Update Layout
                    fig_issuer.update_layout(
                        paper_bgcolor='rgba(0,0,0,0)', 
                        plot_bgcolor='rgba(0,0,0,0)',
                        font_color="#e8f4f0",
                        autosize=True,
                        margin=dict(t=60, b=50, l=180, r=20),
                        height=300, 
                        showlegend=False,
                        bargap=0.1,
                        dragmode=False,
                        # ATUR COLORBAR DI SINI (Karena px.bar otomatis pakai coloraxis)
                        coloraxis_colorbar=dict(
                            title='Total', 
                            thickness=15, 
                            len=0.5, 
                            x=1.1,      # x=1.1 bikin dia ada di luar grafik, pas di samping kanan
                            y=0.5       # y=0.5 bikin dia rata tengah vertikal
                        ),
                        xaxis=dict(
                            tickfont=dict(size=14),
                            showgrid=False, 
                            zeroline=False,
                            automargin=True,
                            title="" 
                        ),
                        yaxis=dict(
                            tickfont=dict(size=14),
                            title="" 
                        ),
                        hoverlabel=dict(
                            bgcolor="#0f172a",    
                            font_color="white",   
                            bordercolor="#334155" 
                        ),
                    )
                    
                    selected_issuer = plotly_events(fig_issuer, click_event=True, select_event=False, override_height=300,)

                    if selected_issuer:
                        try:
                            # PAKE NAMA (y) BUKAN INDEX (pointNumber)
                            issuer_terpilih = selected_issuer[0].get('y')
                            
                            # Cari row berdasarkan nama di dataframe ASLI (df_issuer)
                            row = df_issuer[df_issuer['c2_common_name'] == issuer_terpilih]
                            
                            if not row.empty:
                                total_data = int(row.iloc[0]['total'])
                                
                                # RESETING FILTER LAMA
                                st.session_state['status_filter'] = None 
                                st.session_state['validity_filter'] = None
                                
                                # SET FILTER BARU
                                st.session_state['issuer_filter'] = issuer_terpilih
                                st.session_state['total_clicked'] = total_data
                                st.session_state['current_page'] = "Forensic Log System"
                                st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")
                    st.markdown('</div>', unsafe_allow_html=True)

        with st.container(border=True):
            st.markdown('''
                <div class="section-header-triple">
                    <h3 style="margin: 0;">⚖️ Audit Etika AI: Analisis Potensi Bias Vendor</h3>
                    <div class="info-wrapper">
                        <button class="info-btn">ⓘ</button>
                        <div class="info-popup">Komparasi rasio Trusted vs Untrusted tiap vendor.<br><br>💡 <b>Pro-Tip:</b> Klik segmen batang grafik untuk melakukan audit silang pada vendor spesifik.</div>
                    </div>
                </div>
            ''', unsafe_allow_html=True)
            bias_query = f"""
            SELECT 
                c2.c2_common_name as 'Vendor',
                SUM(CASE WHEN f.f1_is_trusted = 1 THEN 1 ELSE 0 END) as 'Trusted',
                SUM(CASE WHEN f.f1_is_trusted = 0 THEN 1 ELSE 0 END) as 'Untrusted'
            FROM esa_fact_verifications f
            JOIN esa_dim_issuer_c2 c2 ON f.c2_issuer_key = c2.c2_issuer_key
            WHERE DATE(f.f1_signing_time) BETWEEN '{start_dt}' AND '{end_dt}'
            GROUP BY 1 
            ORDER BY (SUM(CASE WHEN f.f1_is_trusted = 0 THEN 1 ELSE 0 END) * 1.0 / COUNT(*)) DESC 
            """
            df_bias = get_data(bias_query)
                
            if not df_bias.empty:
                df_melted = df_bias.melt(id_vars='Vendor', value_vars=['Trusted', 'Untrusted'], 
                                            var_name='Status', value_name='Count')
                            
                    # 1. BUAT GRAFIKNYA
                fig_bias = px.bar(df_melted, x='Count', y='Vendor', color='Status', 
                                orientation='h', barmode='stack',
                                color_discrete_map={'Trusted': '#10b981', 'Untrusted': '#ef4444'})
                
                fig_bias.update_traces(
                    # Kita buat sependek mungkin biar gak perlu miring buat muat teks
                    hovertemplate="Status: %{fullData.name}<br>Total: %{x}<extra></extra>",
                    
                    hoverlabel=dict(
                        bgcolor="#1e293b",
                        font_color="#ffffff",
                        bordercolor="#334155",
                        # KUNCI: Paksa align-nya biar nggak miring
                        align="left" 
                    )
                )
                
                fig_bias.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)', 
                    plot_bgcolor='rgba(0,0,0,0)',
                    font_color="#e8f4f0",
                    height=500, 
                    hovermode="closest",
                    yaxis=dict(tickfont=dict(size=14, family="Arial, sans-serif")), 
                    xaxis=dict(
                        tickfont=dict(size=14),
                        showgrid=False,       # <--- INI MENGHILANGKAN GARIS TEGAK
                        zeroline=False,       # <--- INI MENGHILANGKAN GARIS NOL
                        automargin=True,
                        title=""
                    ),
                    bargap=0.2, 
                    bargroupgap=0, 
                    margin=dict(t=30, b=50, l=200, r=20),
                    legend=dict(
                        orientation="h", 
                        yanchor="top", y=-0.25, 
                        xanchor="center", x=0.5,
                        title="",
                        font=dict(size=14)
                    )
                )
                            
                fig_bias.update_xaxes(title="") 
                fig_bias.update_yaxes(title="")
                            
                selected_bias = plotly_events(fig_bias, click_event=True, select_event=False, override_height=500)
                if selected_bias:
                    try:
                        # 1. Ambil Nama Vendor
                        vendor_terpilih = str(selected_bias[0].get('y')).strip()
                        
                        # 2. Ambil Status dengan AMAN (Fallback ke string kosong jika None)
                        full_data = selected_bias[0].get('fullData', {})
                        status_klik = full_data.get('name', 'Semua Status (All)') 
                        
                        # 3. Cari baris vendor di df_bias
                        mask = df_bias['Vendor'].str.strip() == vendor_terpilih
                        row = df_bias[mask].iloc[0]
                        
                        # 4. SET FILTER KE SESSION STATE
                        st.session_state['issuer_filter'] = vendor_terpilih
                        
                        # 5. Logika Total & Status yang PINTAR
                        # Cek apakah status_klik ada di kolom df_bias (Case Insensitive)
                        status_kolom = next((col for col in df_bias.columns if col.lower() == status_klik.lower()), None)
                        
                        if status_kolom:
                            st.session_state['status_filter'] = status_kolom.title()
                            total_data = int(row[status_kolom])
                        else:
                            # Jika klik di luar legend/batang, reset ke total semua status
                            st.session_state['status_filter'] = "Semua Status (All)"
                            total_data = int(row['Trusted'] + row['Untrusted'])
                            
                        st.session_state['total_clicked'] = total_data
                        st.session_state['current_page'] = "Forensic Log System"
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"Error saat klik audit: {e}")
            else:
                st.write("Data audit etika vendor tidak tersedia untuk periode ini.")

    elif selected_menu == "Forensic Log System":
        st.markdown('''
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px;">
                <h3 style="margin: 0;">📑 Log Forensik Transaksi Dokumen</h3>
                <div class="info-wrapper">
                    <button class="info-btn">ⓘ</button>
                    <div class="info-popup">Log audit dengan skor risiko komposit MADM & AI.<br><br>💡 <b>Pro-Tip:</b> Gunakan kotak pencarian atau <i>dropdown</i> filter di bawah untuk investigasi spesifik.</div>
                </div>
            </div>
        ''', unsafe_allow_html=True)

        raw_query = f"""
        SELECT 
            f.f1_doc_id as 'Doc ID',
            f.f1_is_trusted as 'StatusRaw',
            c2.c2_common_name as 'Issuer Authority',
            f.f1_ltv_status as 'LTV Status',
            c4.c4_corpo_name as 'Type',
            c5.c5_reason as 'Reasoning Analysis',
            f.f1_signing_time as 'Time',
            f.f1_is_expired as 'IsExpiredRaw', 
            f.f1_validity_days as 'DaysRaw'
        FROM esa_fact_verifications f
        JOIN esa_dim_integrity_c5 c5 ON f.c5_integrity_key = c5.c5_integrity_key
        JOIN esa_dim_issuer_c2 c2 ON f.c2_issuer_key = c2.c2_issuer_key
        JOIN esa_dim_corporate_c4 c4 ON f.c4_corpo_key = c4.c4_corpo_key
        WHERE DATE(f.f1_signing_time) BETWEEN '{start_dt}' AND '{end_dt}'
        ORDER BY f.f1_id DESC
        """
        df_all = get_data(raw_query)

        # --- DEBUG: TARUH DI SINI ---
        #st.write("--- DEBUG: CEK DATA ---")
        #st.write("Jumlah data kosong (NaN) di DaysRaw:", df_all['DaysRaw'].isna().sum())
        # Cek tipe data biar kita tau kenapa dia 'nan'
        #st.write("Tipe data DaysRaw:", df_all['DaysRaw'].dtype)
        #st.write("5 baris pertama data:", df_all.head())

        # --- FIX: CUCI DATA ---
        df_all['DaysRaw'] = pd.to_numeric(df_all['DaysRaw'], errors='coerce').fillna(0)

        def calculate_saw(row):
            matrix = np.array([
                1 if row['StatusRaw'] == 0 else 0, 
                1 if row['IsExpiredRaw'] == 1 else 0, 
                (365 - min(row['DaysRaw'], 365)) / 365
            ])
            return np.dot(matrix, np.array([0.5, 0.3, 0.2]))

        def calculate_wp(row):
            c1 = max(1 if row['StatusRaw'] == 0 else 0, 0.001) ** 0.5
            c2 = max(1 if row['IsExpiredRaw'] == 1 else 0, 0.001) ** 0.3
            c3 = max((365 - min(row['DaysRaw'], 365)) / 365, 0.001) ** 0.2
            return c1 * c2 * c3

        def calculate_final_risk(row):
            reason = row['Reasoning Analysis'] or ""
            ai_score = 1.0 if ("Untrusted" in reason or "Self-Signed" in reason) else (0.6 if "Technical" in reason else 0.0)
            madm_avg = (row['Risk_Score_SAW'] + row['Risk_Score_WP']) / 2
            return (ai_score * 0.4) + (madm_avg * 0.6)
        
        def get_risk_label(score):
            if score >= 0.7: return "🔴 CRITICAL"
            if score >= 0.4: return "🟡 MODERATE"
            return "🟢 LOW/SAFE"

        if not df_all.empty:
            # 1. Hitung-hitungan (SAW, WP, Risk)
            df_all['Risk_Score_SAW'] = df_all.apply(calculate_saw, axis=1)
            df_all['Risk_Score_WP'] = df_all.apply(calculate_wp, axis=1)
            if df_all['Risk_Score_WP'].sum() > 0:
                df_all['Risk_Score_WP'] = df_all['Risk_Score_WP'] / df_all['Risk_Score_WP'].max()
            df_all['Final_Integrity_Risk'] = df_all.apply(calculate_final_risk, axis=1)
            df_all['Status'] = df_all['StatusRaw'].apply(lambda x: "TRUSTED" if x == 1 else "UNTRUSTED")
            df_all['Urgensi'] = df_all['Final_Integrity_Risk'].apply(get_risk_label)


            # 2. Render Search & Selectbox
            saved_filter = st.session_state.get('status_filter', "Semua Status (All)")
            col_search, col_filter = st.columns([2, 1])
            with col_search:
                search_query = st.text_input("", placeholder="🔍 Cari Berdasarkan ID Dokumen...", label_visibility="collapsed")
            with col_filter:
                status_options = ["Semua Status (All)", "TRUSTED", "UNTRUSTED"]
                current_index = status_options.index(saved_filter) if saved_filter in status_options else 0
                selectbox_val = st.selectbox("", options=status_options, index=current_index, label_visibility="collapsed")

            # 1. Pastikan state terinisialisasi dengan benar
            if 'issuer_filter' not in st.session_state:
                st.session_state['issuer_filter'] = None
            if 'status_filter' not in st.session_state:
                st.session_state['status_filter'] = None

            # 2. Blok Filter yang BERSIH & TIDAK DUPLIKAT
            if st.session_state['issuer_filter']:
                filter_val = st.session_state['issuer_filter']
                st.sidebar.info(f"Filter aktif: {filter_val}")
                
                # Tombol Reset dengan key unik dan hanya ada SATU
                if st.sidebar.button(f"Reset Filter Issuer: {filter_val}", key="unique_reset_btn"):
                    st.session_state['issuer_filter'] = None
                    st.rerun()

            # 1. Filter Paling Keras (Issuer) - Kalau ada, ini wajib difilter duluan
            if st.session_state['issuer_filter']:
                df_all = df_all[df_all['Issuer Authority'].str.strip() == st.session_state['issuer_filter'].strip()]

            # 2. Filter Validity (Opsional) - Kalau user klik/pilih filter ini
            if st.session_state.get('validity_filter') == "Expiring Soon":
                df_temp = df_all[df_all['DaysRaw'] < 999]
                if not df_temp.empty:
                    df_all = df_temp
                else:
                    st.info("Info: Tidak ada data Expired.")
            # Filter Status
            final_filter = saved_filter if st.session_state.get('status_filter') is not None else selectbox_val
            if final_filter != "Semua Status (All)":
                df_all = df_all[df_all['Status'].str.strip().str.upper() == final_filter.strip().upper()]

            # Filter Search
            if search_query:
                df_all = df_all[df_all['Doc ID'].str.contains(search_query, case=False) | 
                                df_all['Issuer Authority'].str.contains(search_query, case=False)]
            # 4. RESET SESI (Ditaruh di akhir proses filter)
            st.session_state['status_filter'] = None
            st.session_state['validity_filter'] = None

            # 5. RENDER TABEL (Hanya jika data masih ada setelah semua filter)
            if not df_all.empty:
                df_display = df_all.drop(columns=['StatusRaw', 'IsExpiredRaw']).copy()
                
                df_display['Anomali Score'] = df_display['Reasoning Analysis'].apply(
                    lambda r: "🔴 DANGER" if ("Untrusted" in str(r) or "Self-Signed" in str(r)) 
                    else ("🟡 WARNING" if ("Technical" in str(r) or "LTV Not" in str(r)) else "🟢 SAFE")
                )
                df_display['Urgensi'] = df_display['Final_Integrity_Risk'].apply(get_risk_label)
                
                col_order = ["Doc ID", "Urgensi", "Status", "Final_Integrity_Risk", "DaysRaw", "Time", "Issuer Authority", "Type", "LTV Status", "Anomali Score", "Reasoning Analysis", "Risk_Score_SAW", "Risk_Score_WP"]
                df_display = df_display[col_order]

                forensic_config = {
                    "Doc ID": st.column_config.TextColumn("Doc ID", width="small"),
                    "Urgensi": st.column_config.TextColumn("Urgensi", width="small"),
                    "Status": st.column_config.TextColumn("Putusan", width="small"),
                    "Final_Integrity_Risk": st.column_config.ProgressColumn("🛡️ Risiko", format="%.2f"),
                    "Time": st.column_config.DatetimeColumn("Waktu", format="D MMM, HH:mm"),
                    "Issuer Authority": st.column_config.TextColumn("Issuer", width="medium"),
                    "DaysRaw": st.column_config.NumberColumn("DaysRaw", format="%d"),
                    "Anomali Score": st.column_config.TextColumn("AI Status", width="small"),
                    "Reasoning Analysis": st.column_config.TextColumn("Reasoning", width="large"),
                    "Risk_Score_SAW": st.column_config.NumberColumn("Skor SAW", format="%.3f"),
                    "Risk_Score_WP": st.column_config.NumberColumn("Skor WP", format="%.3f"),
                }
                
                render_paginated_dataframe(df_display, "forensic", config=forensic_config)
            else:
                st.warning("Data tidak ditemukan setelah difilter.")
        else:
            st.warning("Data tidak ditemukan di database.")

    elif selected_menu == "Competitor Intel":
        # 1. KOTAK UTAMA (Membungkus semua konten Competitor Intel)
        with st.container(border=True):
            st.markdown('''
                <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 25px;">
                    <h3 style="margin: 0;">🧬 Analisis Perilaku Pelanggan (Behavioral Intelligence)</h3>
                    <div class="info-wrapper">
                        <button class="info-btn">ⓘ</button>
                        <div class="info-popup">Analisis mendalam mengenai perilaku transaksi klien untuk memprediksi loyalitas dan risiko churn.</div>
            ''', unsafe_allow_html=True)

            # 2. Card Loyalitas
                # CABUT HEIGHT DARI SINI
            with st.container(border=True):
                    st.markdown('''
                        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 15px;">
                            <h4 style="margin: 0; color: #e8f4f0; font-family: 'Outfit';">🏆 Loyalitas Organisasi</h4>
                            <div class="info-wrapper">
                                <button class="info-btn">ⓘ</button>
                                <div class="info-popup">Organisasi disegmentasikan berdasarkan frekuensi transaksi (Aktivitas >= 3 dianggap Loyalis).</div>
                            </div>
                        </div>
                    ''', unsafe_allow_html=True)
                    loyalty_query = f"""
                    SELECT 
                        COALESCE(c4.c4_corpo_name, 'Uncategorized/Personal') as 'Organisasi', 
                        COUNT(f.f1_id) as 'Aktivitas'
                    FROM esa_fact_verifications f
                    LEFT JOIN esa_dim_corporate_c4 c4 ON f.c4_corpo_key = c4.c4_corpo_key
                    WHERE DATE(f.f1_signing_time) BETWEEN '{start_dt}' AND '{end_dt}'
                    GROUP BY 1 ORDER BY 2 DESC
                    """
                    # ----------------------------------------
                    df_loyalty = get_data(loyalty_query)
                    
                    if not df_loyalty.empty:
                        df_loyalty['Segmen'] = df_loyalty['Aktivitas'].apply(lambda c: "👑 Segment A (Loyalist)" if c >= 3 else "🌱 Segment B (Regular)")
                        loyalty_config = {
                            "Organisasi": st.column_config.TextColumn("Organisasi", width="medium"),
                            "Aktivitas": st.column_config.NumberColumn("Total Aktivitas", format="%d Transaksi"),
                            "Segmen": st.column_config.TextColumn("Segmen")
                        }
                        
                        # --- PANGGIL FUNGSI PAGINATOR ---
                        # Key prefix "loyalty" harus unik biar gak bentrok sama tabel lain
                        render_paginated_dataframe(df_loyalty, "loyalty", config=loyalty_config)
                    else:
                        st.write("Data tidak tersedia.")
                    st.markdown('</div>', unsafe_allow_html=True)

            # 3. Card Churn
            with st.container(border=True):
                    st.markdown('''
                        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 15px;">
                            <h4 style="margin: 0; color: #e8f4f0; font-family: 'Outfit';">🚩 Risiko Churn Pelanggan</h4>
                            <div class="info-wrapper">
                                <button class="info-btn">ⓘ</button>
                                <div class="info-popup">Mendeteksi organisasi yang berpotensi churn. <br><br>💡 <b>Pro-Tip:</b> Geser slider <i>'Batas Inaktif'</i> di bawah untuk mengubah rentang toleransi hari secara interaktif.</div>
                            </div>
                        </div>
                    ''', unsafe_allow_html=True)
                    
                    inactivity_days = st.slider("Batas Inaktif (Hari)", 1, 60, 7, key="churn_slider")
                    
                    churn_query = f"""
                    SELECT 
                        c4.c4_corpo_name as 'Organisasi', 
                        MAX(f.f1_signing_time) as 'Terakhir Dilihat'
                    FROM esa_fact_verifications f
                    JOIN esa_dim_corporate_c4 c4 ON f.c4_corpo_key = c4.c4_corpo_key
                    GROUP BY 1 
                    HAVING MAX(f.f1_signing_time) < datetime('now', '-{inactivity_days} days') 
                    """
                    df_churn = get_data(churn_query)
            
                    if not df_churn.empty:
                        df_churn['Status'] = "🔥 AT RISK"
                        st.warning(f"Sistem mendeteksi {len(df_churn)} organisasi dengan risiko churn tinggi.")
                        
                        churn_config = {
                            "Organisasi": st.column_config.TextColumn("Organisasi", width="medium"),
                            "Terakhir Dilihat": st.column_config.TextColumn("Terakhir Dilihat", width="medium"),
                            "Status": st.column_config.TextColumn("Status", width="small")
                        }
                        
                        render_paginated_dataframe(df_churn, "churn", config=churn_config)
                    else:
                        st.success("Seluruh organisasi pelanggan terdeteksi aktif.")
                    
                    st.markdown('</div>', unsafe_allow_html=True)
                            
                            

        # --- COMPETITOR WEB INTELLIGENCE MONITORING LAYER ---
        @st.fragment(run_every="10m") 
        def render_intelligence_section():

            # 1. THE MASTER CONTAINER (Sekarang membungkus judul section juga)
            with st.container(border=True):
                st.markdown('''
                    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 25px; position: relative; z-index: 99999;">
                        <h3 style="margin: 0;">📡 Pemantauan Tren Kompetitor (Market Intelligence)</h3>
                        <div class="info-wrapper">
                            <button class="info-btn">ⓘ</button>
                            <div class="info-popup">Pemantauan real-time aktivitas penemuan berkas kriptografi dari root CA kompetitor (mesin 'The Hunter').<br><br>💡 <b>Pro-Tip:</b> Data pada panel intelijen ini diperbarui otomatis secara terisolasi setiap 10 menit tanpa perlu me-reload seluruh halaman.</div>
                        </div>
                    </div>
                ''', unsafe_allow_html=True)
                
                df_intel = get_intel_data()
                if not df_intel.empty:
                    # 2. Kotak untuk Chart Tren (Sub-container)
                    with st.container(border=True):
                        st.markdown('''
                            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 15px;">
                                <h4 style="margin: 0; color: #e8f4f0; font-family: 'Outfit';">📈 Lini Masa Penemuan Aset (Harian)</h4>
                                <div class="info-wrapper">
                                    <button class="info-btn">ⓘ</button>
                                    <div class="info-popup">Volume harian berkas CA yang berhasil dikumpulkan oleh scraper.<br><br>💡 <b>Pro-Tip:</b> Arahkan kursor ke titik grafik untuk melihat detail harian, atau klik nama PSrE di area legenda untuk menyembunyikan/menampilkan garis tren kompetitor spesifik.</div>
                                </div>
                            </div>
                        ''', unsafe_allow_html=True)
                        df_intel['Date'] = pd.to_datetime(df_intel['timestamp']).dt.date
                        df_trends = df_intel[df_intel['status'] == 'SUCCESS'].groupby(['Date', 'psre_name']).size().reset_index(name='Assets Harvested')
                        
                        fig = px.line(df_trends, x='Date', y='Assets Harvested', color='psre_name', markers=True, color_discrete_sequence=px.colors.sequential.GnBu_r)
                        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="#e8f4f0", margin=dict(t=20, b=0, l=0, r=0), height=300, showlegend=True)
                        st.plotly_chart(fig, use_container_width=True)
                        st.markdown('</div>', unsafe_allow_html=True)
                    
                    # 3. Kotak Bawah (Volume & Log)
                    col_intel_1, col_intel_2 = st.columns(2)

                    # Naikkan height ke 400 atau sesuai kebutuhan lo
                    container_height = 384 

                    with col_intel_1:
                        with st.container(border=True):
                            st.markdown('''
                                <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 15px;">
                                    <h4 style="margin: 0; color: #e8f4f0; font-family: 'Outfit';">📊 Volume Berkas Terkumpul</h4>
                                    <div class="info-wrapper">
                                        <button class="info-btn">ⓘ</button>
                                        <div class="info-popup">Total akumulasi berkas unik yang ditemukan dari masing-masing kompetitor.<br><br>💡 <b>Pro-Tip:</b> Gunakan fitur navigasi halaman di bagian bawah tabel untuk melihat seluruh data volume instansi.</div>
                                    </div>
                                </div>
                            ''', unsafe_allow_html=True)
                            
                            df_success = df_intel[df_intel['status'] == 'SUCCESS']
                            intel_summary = df_success.groupby('psre_name')['file_name'].nunique().reset_index(name='Files Found')
                            intel_summary.columns = ['Nama Instansi PSrE', 'Berkas Ditemukan']
                            
                            # Konfigurasi kolom
                            intel_config = {
                                "Nama Instansi PSrE": st.column_config.TextColumn("Nama Instansi PSrE", width="medium"),
                                "Berkas Ditemukan": st.column_config.NumberColumn("Berkas Ditemukan", width="small")
                            }
                            
                            # Panggil fungsi paginator
                            render_paginated_dataframe(intel_summary, "intel_volume", config=intel_config)
                            st.markdown('</div>', unsafe_allow_html=True)

                    with col_intel_2:
                        # 1. Hapus height di container
                        with st.container(border=True): 
                            st.markdown('''
                                <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 15px;">
                                    <h4 style="margin: 0; color: #e8f4f0; font-family: 'Outfit';">🕵️ Log Aktivitas Scraper</h4>
                                    <div class="info-wrapper">
                                        <button class="info-btn">ⓘ</button>
                                        <div class="info-popup">Log riwayat aktivitas scraping dari root CA kompetitor secara mendetail.<br><br>💡 <b>Pro-Tip:</b> Pantau indikator pada kolom 'Status' untuk memastikan mesin scraper (The Hunter) tidak mengalami kegagalan (FAILED) saat mengakuisisi data.</div>
                                    </div>
                                </div>
                            ''', unsafe_allow_html=True)
                            
                            # Pake SEMUA data dari df_intel (jangan di-head 10 biar paginasi jalan)
                            df_recent = df_intel[['timestamp', 'psre_name', 'status', 'file_name']].copy() 
                            
                            log_config = {
                                "timestamp": st.column_config.TextColumn("Waktu", width="medium"),
                                "psre_name": st.column_config.TextColumn("PSrE", width="medium"),
                                "status": st.column_config.TextColumn("Status", width="small"),
                                "file_name": st.column_config.TextColumn("Berkas", width="large")
                            }
                            
                            # Panggil fungsi paginator (Ini otomatis ngerender tabel dengan config di atas)
                            render_paginated_dataframe(df_recent, "scraper_log", config=log_config)
                            st.markdown('</div>', unsafe_allow_html=True)

        render_intelligence_section()