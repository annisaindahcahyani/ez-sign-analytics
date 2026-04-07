#=============================================================================
#🛡️ MODULE: DATA PURGE ENGINE (THE SECURITY & COMPLIANCE GUARD)
#=============================================================================
#TUGAS UTAMA:
#1. Data Minimization: Menghapus residu data mentah (PDF/JSON) yang sudah 
#   selesai diproses agar tidak menumpuk di server.
#2. Compliance Strategy: Mematuhi prinsip UU PDP (Pelindungan Data Pribadi) 
#   dengan tidak menyimpan data sensitif lebih lama dari yang dibutuhkan.
#3. Storage Optimization: Mencegah pembengkakan penggunaan disk space pada 
#   folder staging/Docker volume.

#PENTING: Jalankan script ini secara berkala (Cron Job) untuk menjaga 
#kebersihan environment produksi.
#=============================================================================

import os
import glob
import time

def auto_purge_raw_files(staging_path, threshold_seconds=3600):
    """
    FUNGSI: AUTO PURGE RAW FILES
    ----------------------------
    Tugas: Menghapus file di folder staging yang umurnya sudah melebihi batas.
    
    Parameters:
    - staging_path: Path folder tempat PDF/JSON mentah berada.
    - threshold_seconds: Batas waktu (dalam detik). Default 3600s (1 Jam).
    """
    now = time.time()
    
    # Mencari seluruh file dengan berbagai ekstensi di directory staging
    # glob.glob membantu scanning file secara massal menggunakan wildcard (*.*)
    files = glob.glob(os.path.join(staging_path, "*.*"))
    
    purged_count = 0
    
    for f in files:
        try:
            # --- STEP 1: METADATA CHECK ---
            # Mengambil waktu modifikasi terakhir file (st_mtime)
            file_age = os.stat(f).st_mtime
            
            # --- STEP 2: EXPIRATION LOGIC ---
            # Jika umur file (sekarang - waktu modif) > batas waktu yang ditentukan
            if file_age < now - threshold_seconds:
                # --- STEP 3: EXECUTION (THE PURGE) ---
                os.remove(f)
                purged_count += 1
                print(f"🧹 [SECURITY] File kadaluwarsa dihapus: {os.path.basename(f)}")
                
        except Exception as e:
            print(f"⚠️ [SECURITY] Gagal menghapus {os.path.basename(f)}: {e}")
            
    return purged_count

if __name__ == "__main__":
    # CONFIGURATION:
    # Arahkan ke folder staging sesuai mount volume Docker.
    STAGING_DIR = "/data/staging"
    
    print(f"🛡️ [UU-PDP COMPLIANCE] Auto-purge active. Memulai pembersihan data residu...")
    
    # Menjalankan fungsi dengan threshold 1 jam (3600 detik)
    total_cleaned = auto_purge_raw_files(STAGING_DIR, threshold_seconds=3600)
    
    if total_cleaned > 0:
        print(f"✅ [SUCCESS] Berhasil membersihkan {total_cleaned} file dari server.")
    else:
        print("ℹ️ [INFO] Tidak ada file kadaluwarsa yang perlu dibersihkan.")