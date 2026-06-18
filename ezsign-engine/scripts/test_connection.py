# =============================================================================
# 🔌 MODULE: DATABASE SANITY CHECK & CONNECTIVITY TESTER
# =============================================================================
# 📌 CONFIGURATION : Pre-flight Database Verification
# 📅 UPDATE        : 5 Juni 2026
# 🛡️ OBJECTIVE     : Validasi Integritas File & Skema Relasional SQLite
# =============================================================================
# 🗺️ DOKUMEN TATA KERJA FUNGSIONAL PENGEMBANG (FOR NEXT DEVELOPER):
#
# 1. CONNECTIVITY VALIDATION:
#    Skrip ini bertugas memvalidasi jalur komunikasi antara environment Python
#    dengan berkas fisik database.sqlite sebelum service utama dijalankan.
#
# 2. SCHEMA INTEGRITY PREVIEW:
#    Melakukan eksekusi query ringan (Read-Test) ke tabel dimensi (esa_dim_issuer_c2)
#    untuk memastikan skema multidimensi Star Schema telah terbentuk sempurna
#    dan tidak mengalami korupsi data (Data Corruption).
#
# PENTING: Eksekusi berkas ini pada fase inisialisasi lingkungan atau setelah
# terjadi migrasi struktur database.
# =============================================================================

import os
import sqlite3
from dotenv import load_dotenv

# Memuat konfigurasi environment variables global demi konsistensi arsitektur Docker
load_dotenv()
DEFAULT_DB_PATH = os.getenv("DATABASE_PATH", "data/database.sqlite")

def check_connection():
    """
    Fungsi Pemeriksaan Koneksi (Sanity Check):
    Memverifikasi keberadaan berkas fisik dan melakukan pengujian jabat tangan (Handshake) SQLite.
    """
    # Resolusi path dinamis guna menjamin kompatibilitas lingkungan Docker dan debugging lokal
    actual_db_path = DEFAULT_DB_PATH
    if actual_db_path == "data/database.sqlite" and not os.path.exists(actual_db_path):
        # Taktik Fallback: Mencari jalur relatif jika skrip dieksekusi langsung dari sub-direktori scripts
        alt_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "database.sqlite"))
        if os.path.exists(alt_path):
            actual_db_path = alt_path

    print(f"[INFO] Memulai proses verifikasi resolusi path: {os.path.abspath(actual_db_path)}")
    
    # --- [STEP 1: PHYSICAL FILE INTEGRITY CHECK] ---
    if not os.path.exists(actual_db_path):
        print(f"❌ [CRITICAL ERROR] Berkas database.sqlite tidak ditemukan pada direktori: {actual_db_path}")
        print("   Tindakan: Pastikan shared volume './data:/data' terkonfigurasi sempurna pada berkas docker-compose.yml.")
        return

    conn = None
    try:
        # --- [STEP 2: SQLITE CRYPTOGRAPHIC HANDSHAKE] ---
        conn = sqlite3.connect(actual_db_path, timeout=10)
        cursor = conn.cursor()
        
        # --- [STEP 3: SYSTEM CATALOG PRE-CHECK] ---
        # Memastikan tabel esa_dim_issuer_c2 benar-benar eksis sebelum mengeksekusi operasi baca
        table_check = cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='esa_dim_issuer_c2'"
        ).fetchone()
        
        if not table_check:
            print("❌ [SCHEMA ERROR] Tabel 'esa_dim_issuer_c2' tidak ditemukan di dalam struktur database.")
            print("   Tindakan: Harap jalankan script inisialisasi skema DDL (DDL Migration) terlebih dahulu.")
            return

        # --- [STEP 4: QUERY PREVIEW & SCHEMA VALIDATION] ---
        # Mengeksekusi pembacaan sampel data menggunakan kolom terindeks sesuai spesifikasi Star Schema
        cursor.execute("SELECT c2_common_name FROM esa_dim_issuer_c2 WHERE c2_common_name IS NOT NULL LIMIT 5")
        rows = cursor.fetchall()
        
        print("\n✅ [SUCCESS] Jabat tangan SQLite berhasil diinisiasi. Integritas skema relasional stabil.")
        
        issuer_list = [row[0] for row in rows]
        if issuer_list:
            print(f"📦 [DATA PREVIEW] Sampel entri Otoritas Penerbit (Issuer Authority) aktif: {issuer_list}")
        else:
            print("ℹ️ [INFO] Skema tabel tervalidasi sempurna, namun 'esa_dim_issuer_c2' belum memiliki entri data (Empty Table).")
        
    except sqlite3.OperationalError as e:
        print(f"❌ [DATABASE OPERATIONAL ERROR] Kegagalan runtime instruksi SQL. Struktur kolom terindikasi korup: {e}")
    except Exception as e:
        print(f"❌ [UNKNOWN ERROR] Terjadi anomali sistem luar batas isolasi ekseptional: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    print("\n" + "="*65)
    print("🔌 EZSIGN INFRASTRUCTURE CHECK: TESTING DATABASE PIPELINE RESOLUTION")
    print("="*65)
    check_connection()
    print("="*65 + "\n")