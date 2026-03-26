import pandas as pd
import sqlite3

def convert_dump_to_dataframe(json_payload):
    """
    Hybrid Ingestion Logic: Mengonversi payload data mentah dari perusahaan 
    menjadi DataFrame Pandas sebelum proses transformasi ke Star Schema.
    """
    df = pd.DataFrame(json_payload)
    
    # Pre-processing: Standardisasi kolom yang sering typo
    if "Signer " in df.columns:
        df.rename(columns={"Signer ": "Signer"}, inplace=True)
        
    return df

def audit_log_summary(conn):
    """Melakukan profiling data singkat untuk verifikasi integritas log."""
    query = "SELECT COUNT(*) as total, f1_is_trusted FROM esa_fact_verifications GROUP BY 2"
    return pd.read_sql(query, conn)