
# =============================================================================
# 🛠️ MODULE: EZSIGN ANALYTICS UTILITIES (THE DATA BRIDGE)
# =============================================================================
# TUGAS UTAMA:
# 1. Data Hybrid Ingestion: Jembatan konversi dari format JSON (API/Watcher) 
#    ke format DataFrame (Pandas) untuk kebutuhan analisis lanjut.
# 2. Integrity Auditing: Melakukan pengecekan cepat (profiling) ke Database 
#    untuk memastikan log yang masuk sudah sinkron dan valid.
# 3. Pre-processing Guard: Menangani anomali data (seperti typo spasi pada kolom) 
#    sebelum data masuk ke pipeline transformasi.

# ALUR KERJA:
# Raw Data -> utils.py (Cleaning & Structuring) -> Analysis/Database
# =============================================================================

import pandas as pd
import sqlite3

def convert_dump_to_dataframe(json_payload):
    """
    FUNGSI: CONVERT DUMP TO DATAFRAME
    ----------------------------------
    Tugas: Mengubah payload JSON mentah dari perusahaan menjadi objek 
    DataFrame Pandas yang siap diolah.
    
    Logic Khusus: 
    - Melakukan standardisasi kolom 'Signer ' (dengan trailing space) 
      menjadi 'Signer' agar tidak merusak proses Join/Filtering di tahap berikutnya.
    """
    # Mengubah list of dictionaries menjadi tabel (DataFrame)
    df = pd.DataFrame(json_payload)
    
    #--- HYBRID INGESTION CLEANING ---
    # Mendeteksi dan memperbaiki typo spasi yang sering muncul dari output engine verifikator.
    if "Signer " in df.columns:
        df.rename(columns={"Signer ": "Signer"}, inplace=True)
        
    return df

def audit_log_summary(conn):
    """
    FUNGSI: AUDIT LOG SUMMARY
    -------------------------
    Tugas: Melakukan profiling data singkat (Data Integrity Check).
    
    Logic: 
    - Mengambil ringkasan jumlah verifikasi berdasarkan status kepercayaan (f1_is_trusted).
    - Membantu tim audit untuk melihat rasio dokumen Trusted vs Untrusted secara cepat.
    """
    # Query SQL untuk agregasi data dari Fact Table (F1)
    query = "SELECT COUNT(*) as total, f1_is_trusted FROM esa_fact_verifications GROUP BY 2"
    # Mengembalikan hasil query langsung dalam bentuk DataFrame agar Slay saat ditampilkan
    return pd.read_sql(query, conn)