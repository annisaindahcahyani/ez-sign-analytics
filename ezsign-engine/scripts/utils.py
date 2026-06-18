# =============================================================================
# 🛠️ MODULE: EZSIGN ANALYTICS UTILITIES (THE DATA BRIDGE & PROFILING)
# =============================================================================
# 📌 CONFIGURATION : Pre-processing & Integrity Auditing Utilities
# 📅 UPDATE        : 5 Juni 2026
# 🛡️ OBJECTIVE     : Data Cleansing, Transformation, & Quick Insight Generation
# =============================================================================
# 🗺️ DOKUMEN TATA KERJA FUNGSIONAL PENGEMBANG (FOR NEXT DEVELOPER):
#
# 1. HYBRID INGESTION LAYER (convert_dump_to_dataframe):
#    Bertindak sebagai jembatan konversi format JSON payload (dari API/Watcher)
#    menjadi objek DataFrame (Pandas) guna memfasilitasi komputasi analitik.
#    Melakukan sanitasi anomali format (seperti trailing spaces pada metadata)
#    sebelum data didistribusikan ke pipeline transformasi lanjutan.
#
# 2. INTEGRITY AUDITING (audit_log_summary):
#    Menjalankan kueri agregasi tingkat tinggi langsung ke Database (Fact Table).
#    Berfungsi untuk memberikan ringkasan profil integritas (Trusted vs Untrusted)
#    secara cepat guna mendukung proses pelaporan audit operasional.
# =============================================================================

import pandas as pd
import sqlite3

def convert_dump_to_dataframe(json_payload):
    """
    Fungsi Konversi dan Pembersihan Data (Data Ingestion Bridge):
    Mengonversi muatan payload JSON eksternal menjadi objek DataFrame Pandas.
    
    Logika Pembersihan (Data Cleansing):
    Mendeteksi dan menormalisasi anomali pemformatan (seperti trailing space pada kunci 'Signer ') 
    yang dihasilkan oleh engine verifikator hulu, guna mencegah kegagalan proses relasi (Join) 
    dan penyaringan (Filtering) pada tahap agregasi skema data warehouse.
    """
    # [SAFETY NET LAYER] Proteksi mutlak jika payload kosong agar tidak merusak skema hulu pipeline
    if not json_payload:
        required_schema_cols = ['code', 'Signer', 'SubjectDN', 'Issuer', 'Serial Number', 'Validity', 'LTV']
        return pd.DataFrame(columns=required_schema_cols)

    # Transformasi struktur list of dictionaries menjadi kerangka operasional DataFrame
    df = pd.DataFrame(json_payload)
    
    # --- [HYBRID INGESTION CLEANING PROTOCOL] ---
    # Sanitasi dinamis untuk mengeliminasi spasi liar pada nama kolom (Trailing Space Trimming)
    df.columns = df.columns.str.strip()
        
    return df


def audit_log_summary(conn):
    """
    Fungsi Pemrofilan Integritas Data (Data Integrity Check):
    Menyajikan ringkasan kuantitatif mengenai proporsi dokumen terverifikasi 
    berdasarkan status kepercayaan (f1_is_trusted).
    
    Logika Operasional:
    Mengeksekusi kueri agregasi SQL langsung pada Tabel Fakta (esa_fact_verifications)
    untuk mengembalikan metrik rasio dokumen Trusted berbanding Untrusted, guna 
    memfasilitasi pemantauan cepat bagi tim audit (Compliance Officers).
    """
    # Standardisasi kueri eksplit dan rekayasa output string teks (Human-Readable Metrics Transformation)
    query = """
    SELECT 
        COUNT(*) as total_records,
        CASE f1_is_trusted 
            WHEN 1 THEN 'TRUSTED DOCK' 
            ELSE 'UNTRUSTED / FRAUD ATTEMPT' 
        END as integrity_status
    FROM esa_fact_verifications 
    GROUP BY f1_is_trusted
    ORDER BY total_records DESC
    """
    
    try:
        # Mengonversi hasil kueri ke dalam format DataFrame untuk optimalisasi visualisasi pelaporan
        return pd.read_sql(query, conn)
    except Exception as e:
        print(f"❌ [UTILS ERROR] Gagal merakit profil ringkasan integritas tabel fakta: {e}")
        return pd.DataFrame(columns=['total_records', 'integrity_status'])