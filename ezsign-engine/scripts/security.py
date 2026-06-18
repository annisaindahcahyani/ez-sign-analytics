# =============================================================================
# 🛡️ MODULE: AUTOMATED DATA PURGE ENGINE (SECURITY & COMPLIANCE GUARD)
# =============================================================================
# 📌 CONFIGURATION : Data Minimization & Storage Optimization
# 📅 UPDATE        : 5 Juni 2026
# ⚖️ REGULASI TI   : Kepatuhan UU PDP No. 27 Tahun 2022 (Penghapusan Data Residu)
# =============================================================================
# 🗺️ DOKUMEN TATA KERJA FUNGSIONAL PENGEMBANG (FOR NEXT DEVELOPER):
#
# 1. PRINSIP DATA MINIMIZATION (ZERO-RETENTION PROTOCOL):
#    Skrip ini bertugas memusnahkan residu data mentah (berkas PDF/JSON) di
#    dalam direktori staging yang telah selesai diekstraksi oleh ETL Pipeline.
#    Hal ini menjamin tidak ada data sensitif klien yang mengendap secara ilegal 
#    di dalam infrastruktur server produksi.
#
# 2. MEKANISME EKSEKUSI WAKTU (THRESHOLD LOGIC):
#    Sistem memindai stempel waktu modifikasi terakhir (st_mtime) dari setiap
#    berkas. Jika umur berkas melebihi ambang batas (Default: 3600 detik / 1 Jam),
#    perintah os.remove() akan dieksekusi untuk melakukan Hard Delete (Pemusnahan).
#
# 3. IMPLEMENTASI LINGKUNGAN PRODUKSI:
#    Skrip ini dirancang untuk dijalankan sebagai Background Daemon Process atau
#    Cron Job Task yang tereksekusi secara berkala di dalam lingkungan kontainer Docker.
# =============================================================================

import os
import glob
import time
from dotenv import load_dotenv

# Memuat konfigurasi environment variables global
load_dotenv()
DEFAULT_STAGING = os.getenv("STAGING_PATH", "data/staging")

def auto_purge_raw_files(staging_path, threshold_seconds=3600):
    """
    Fungsi Pembersihan Otomatis (Auto-Purge):
    Mengeliminasi berkas fisik pada direktori staging yang telah melewati batas waktu retensi.

    Parameter Target:
    - staging_path (str): Jalur direktori tempat berkas mentah tersimpan.
    - threshold_seconds (int): Ambang batas toleransi retensi data dalam satuan detik (Default: 1 Jam).
    """
    if not os.path.exists(staging_path):
        print(f"ℹ️ [INFO] Direktori target tidak ditemukan di lokasi: {staging_path}. Melewati siklus pembersihan.")
        return 0

    now = time.time()
    
    # Memindai seluruh berkas secara komprehensif menggunakan pola wildcard global
    files = glob.glob(os.path.join(staging_path, "*"))
    
    purged_count = 0
    
    for f in files:
        # --- [BENTENG PROTEKSI SISTEM: IMMUTABLE FILES BYPASS] ---
        # Menjamin berkas .gitkeep atau folder structural staging tidak terhapus secara anomali
        basename = os.path.basename(f)
        if basename.startswith(".") or basename == "gitkeep" or os.path.isdir(f):
            continue
            
        try:
            # --- [FASE 1: INSPEKSI METADATA BERKAS] ---
            file_stat = os.stat(f)
            file_age = file_stat.st_mtime
            
            # --- [FASE 2: LOGIKA KEDALUWARSA (EXPIRATION CHECK)] ---
            if file_age < now - threshold_seconds:
                
                # --- [FASE 3: EKSEKUSI PEMUSNAHAN GLOBAL (HARD DELETE)] ---
                os.remove(f)
                purged_count += 1
                print(f"[SECURITY AUDIT LOG] Pemusnahan Preventif UU-PDP: Berkas residu '{basename}' berhasil dimusnahkan permanen.")
                
        except FileNotFoundError:
            # Mengatasi kondisi race condition jika file sudah dihapus duluan oleh proses paralel lain
            continue
        except PermissionError:
            print(f"⚠️ [SECURITY WARNING] Berkas '{basename}' gagal dimusnahkan akibat pembatasan akses / sedang terkunci oleh pipeline.")
        except Exception as e:
            print(f"⚠️ [CRITICAL WARNING] Anomali sistem pada pemusnahan berkas '{basename}'. Detail: {e}")
            
    return purged_count


if __name__ == "__main__":
    print("\n" + "="*65)
    print("🛡️ EZSIGN COMPLIANCE ENGINE: AUTOMATED DATA PURGE DAEMON STARTED")
    print("="*65)
    
    # Mengutamakan jalur variabel lingkungan Docker, dengan fallback ke direktori pengujian lokal
    STAGING_DIR = DEFAULT_STAGING
    if STAGING_DIR == "/data/staging" and not os.path.exists(STAGING_DIR):
        # Fallback taktis jika dijalankan di luar ekosistem container
        STAGING_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "staging"))
        
    print(f"[INFO] Mengunci Target Folder Pembersihan: {STAGING_DIR}")
    print("[UU-PDP COMPLIANCE] Menjalankan protokol pembersihan data residu otomatis...")
    
    # Eksekusi fungsi dengan batas retensi 1 jam (3600 detik)
    total_cleaned = auto_purge_raw_files(STAGING_DIR, threshold_seconds=3600)
    
    if total_cleaned > 0:
        print(f"✅ [SUCCESS] Audit Keamanan Selesai: Berhasil memusnahkan {total_cleaned} berkas dari ruang penyimpanan.")
    else:
        print("ℹ️ [INFO] Audit Keamanan Selesai: Penyimpanan steril. Tidak ditemukan data residu melewati batas retensi.")
    print("="*65 + "\n")