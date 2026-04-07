#=============================================================================
#🛠️ MODULE: DATABASE SANITY CHECK (THE CONNECTOR TESTER)
#=============================================================================
#TUGAS UTAMA:
#1. Connectivity Validation: Mastiin script Python bisa "ngobrol" sama file 
#   SQLite tanpa halangan akses atau permission.
#2. Path Verification: Mencegah error "Database Not Found" dengan melakukan 
#   pengecekan lokasi file secara absolut.
#3. Data Integrity Preview: Melakukan query ringan ke tabel dimensi untuk 
#   memastikan data tidak korup dan skema tabel sudah sesuai.

#PENTING: Jalankan file ini PERTAMA KALI sebelum running Dashboard atau Watcher!
#=============================================================================

import sqlite3
import os

# CONFIGURATION:
# Menggunakan relative path: naik satu level (..), masuk ke folder 'data', 
# lalu target file 'database.sqlite'.
db_path = os.path.join('..', 'data', 'database.sqlite')

def check_connection():
    """
    FUNGSI: CHECK CONNECTION
    ------------------------
    Tugas: Melakukan simulasi koneksi dan pengambilan data (Read-Test).
    """
    # Menampilkan path absolut agar developer tau persis di mana Python mencari file DB
    print(f"🔍 Mencoba menyambung ke: {os.path.abspath(db_path)}")
    
    # --- STEP 1: PHYSICAL FILE CHECK ---
    if not os.path.exists(db_path):
        print("❌ ERROR: File database.sqlite GAK KETEMU! Cek folder data/ ya Ca!")
        return

    try:
        # --- STEP 2: SQLITE HANDSHAKE ---
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # --- STEP 3: QUERY PREVIEW ---
        # Mencoba menarik data dari Dimensi Issuer (C2) untuk validasi skema.
        # Catatan: Sesuaikan nama tabel 'dim_issuer' dengan skema Star Schema terbaru.
        cursor.execute("SELECT issuer_name FROM dim_issuer")
        rows = cursor.fetchall()
        
        print("\n✅ KONEKSI BERHASIL, SLAY! ✨")
        # Ekstrak hasil query menjadi list sederhana
        issuer_list = [row[0] for row in rows]
        if issuer_list:
            print(f"📦 Data Terdeteksi (Issuer): {issuer_list}")
        else:
            print("📦 Database terkoneksi, tapi Tabel Issuer masih kosong (No Data).")
        
        conn.close()
        
    except sqlite3.OperationalError as e:
        print(f"❌ ERROR DATABASE: Tabel mungkin belum dibuat atau salah nama. Detail: {e}")
    except Exception as e:
        print(f"❌ WADUH ERROR UNKNOWN: {e}")

if __name__ == "__main__":
    check_connection()