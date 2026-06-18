# =============================================================================
# 🧹 MODULE: AUTOMATED DATA WRANGLING & CLEANSING PIPELINE
# =============================================================================
# 📌 CONFIGURATION : ETL Transformation & Privacy Masking Layer
# 📅 UPDATE        : 5 Juni 2026
# 🛡️ OBJECTIVE     : Normalisasi Teks, Penanganan Missing Values, & Data Anonymization
# ⚖️ REGULASI TI   : Kepatuhan UU PDP No. 27/2022 (Data Privacy & Masking)
# =============================================================================
# 🗺️ DOKUMEN TATA KERJA FUNGSIONAL PENGEMBANG (FOR NEXT DEVELOPER):
#
# 1. STANDARDISASI DATA MENTAH (DATA CLEANSING):
#    Memproses berkas log mentah (intel_dataset.csv) dari sub-mesin scraper.
#    Melakukan normalisasi penamaan entitas PSrE, penanganan nilai kosong (NaN),
#    serta penyeragaman label kegagalan server menggunakan ekspresi reguler (Regex).
#
# 2. PRIVACY ANONYMIZATION (DATA MASKING):
#    Sesuai mandat Etika Komputer dan Pelindungan Data Pribadi, fungsi ini 
#    memotong parameter query string (simbol '?') pada URL sumber. Hal ini 
#    bertujuan mencegah tereksposnya token otentikasi privat atau rute direktori 
#    internal milik kompetitor ke dalam basis data warehouse publik kita.
#
# 3. WAREHOUSE INGESTION:
#    Data yang telah melalui tahap wrangling secara otomatis dimuat ulang 
#    (replace) ke dalam tabel dimensi analitik 'esa_dim_competitor_intel' 
#    pada arsitektur SQLite persisten.
# =============================================================================

import os
import pandas as pd
import sqlite3
from datetime import datetime
from dotenv import load_dotenv

# Memuat konfigurasi environment variables global demi konsistensi arsitektur Docker
load_dotenv()
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
DEFAULT_CSV_PATH = os.path.join(BASE_DIR, "data", "staging", "intel_dataset.csv")
DEFAULT_DB_PATH = os.path.join(BASE_DIR, "data", "database.sqlite")

def run_data_wrangling():
    """
    Fungsi Orkestrasi Transformasi Data (Wrangling Pipeline):
    Mengeksekusi siklus pembersihan, ekstraksi fitur (feature engineering),
    dan masking privasi sebelum proses muat (loading) ke Data Warehouse.
    """
    print("\n" + "="*65)
    print("🧹 SYSTEM INITIATION: AUTOMATED DATA WRANGLING PIPELINE")
    print("="*65)
    
    # Resolusi path dinamis guna menjamin kompatibilitas lingkungan Docker dan debugging lokal
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    actual_csv_path = os.path.join(BASE_DIR, "data", "staging", "intel_dataset.csv")
    actual_db_path = os.path.join(BASE_DIR, "data", "database.sqlite")
    
    print(f"[DEBUG] Target CSV: {actual_csv_path}")

    if actual_csv_path == "data/staging/intel_dataset.csv" and not os.path.exists(actual_csv_path):
        # Taktik Fallback: Mencari jalur relatif jika skrip dieksekusi langsung dari sub-direktori scripts lokal
        alt_csv = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "staging", "intel_dataset.csv"))
        alt_db = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "database.sqlite"))
        if os.path.exists(alt_csv):
            actual_csv_path = alt_csv
            actual_db_path = alt_db

    if not os.path.exists(actual_csv_path):
        print(f"❌ [CRITICAL ERROR] Berkas dataset mentah tidak ditemukan pada path: {actual_csv_path}")
        print("   Tindakan Penyelesaian: Pastikan skrip akuisisi (scraper_v1.py) telah tereksekusi dengan sukses.")
        return

    # --- 1. FASE EKSTRAKSI (EXTRACT) ---
    df = pd.read_csv(actual_csv_path)
    if df.empty:
        print("ℹ️ [INFO] Dataset mentah terdeteksi kosong. Melewati tahapan transformasi data.")
        print("="*65 + "\n")
        return
    
    # --- 2. FASE NORMALISASI TEKS (TEXT CLEANSING) ---
    df['psre_name'] = df['psre_name'].astype(str).str.upper().str.strip()
    
    # --- 3. FASE PENANGANAN ANOMALI (MISSING VALUE & ERROR HANDLING) ---
    df['file_name'] = df['file_name'].fillna("N/A")
    # Mengonsolidasikan variasi pesan kegagalan menjadi satu metrik standar melalui skema regex
    df['status'] = df['status'].astype(str).str.replace("FAILED_.*", "FAILED_SERVER", regex=True)
    
    # --- 4. FASE EKSTRAKSI FITUR WAKTU & EKSTENSI (FEATURE ENGINEERING) ---
    df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
    df['fetch_date'] = df['timestamp'].dt.strftime('%Y-%m-%d')
    # Mengekstrak format ekstensi berkas untuk keperluan segmentasi tipe dokumen analitik
    df['file_type'] = df['file_name'].apply(lambda x: str(x).split('.')[-1].upper() if '.' in str(x) else 'UNKNOWN')

    # --- 5. FASE PROTEKSI PRIVASI (DATA ANONYMIZATION) ---
    # Sanitasi URL untuk mencegah penyimpanan parameter sensitif pihak ketiga (UU PDP Compliance)
    df['source_url'] = df['source_url'].apply(lambda x: str(x).split('?')[0] if isinstance(x, str) else x)

    # --- [SINKRONISASI TIPE DATA SQLITE ENGINE] ---
    # Mengonversi kembali objek datetime menjadi string format ISO murni YYYY-MM-DD HH:mm:ss 
    # guna mencegah kegagalan relasi sorting dan kueri rentang tanggal di Streamlit OLAP dashboard
    df['timestamp'] = df['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S').fillna(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

    # --- 6. FASE MUAT KE DATA WAREHOUSE (LOAD) ---
    print(f"[INFO] Memulai proses Ingestion menuju skema tabel 'esa_dim_competitor_intel' pada: {os.path.abspath(actual_db_path)}")
    
    try:
        with sqlite3.connect(actual_db_path) as conn:
            # Menggantikan entri lama secara utuh guna memastikan kemutakhiran data analitik (Full Load Sync)
            df.to_sql("esa_dim_competitor_intel", conn, if_exists="replace", index=False)
            conn.commit()
        print(f"✅ [PIPELINE SUCCESS] Wrangling Selesai: {len(df)} baris data steril berhasil ditransfer ke dalam arsitektur SQLite.")
    except Exception as e:
        print(f"❌ [INGESTION ERROR] Terjadi kegagalan transfer data menuju database: {e}")
    finally:
        print("="*65 + "\n")


if __name__ == "__main__":
    run_data_wrangling()