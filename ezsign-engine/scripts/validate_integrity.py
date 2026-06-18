# =============================================================================
# 🛡️ MODULE: PHYSICAL DATA INTEGRITY AUDIT (CROSS-VALIDATION PROTOCOL)
# =============================================================================
# 📌 CONFIGURATION : Log vs File System Consistency Check
# 📅 UPDATE        : 5 Juni 2026
# 🛡️ OBJECTIVE     : Memastikan konsistensi antara log akuisisi dan keberadaan fisik berkas
# =============================================================================
# 🗺️ DOKUMEN TATA KERJA FUNGSIONAL PENGEMBANG (FOR NEXT DEVELOPER):
#
# 1. MEKANISME AUDIT FORENSIK LEVEL 2:
#    Skrip ini berfungsi sebagai pengawas lapis kedua setelah proses web scraping.
#    Sistem akan mencocokkan setiap entri berstatus 'SUCCESS' pada berkas log 
#    (intel_dataset.csv) dengan ketersediaan berkas fisik kriptografi (PDF/CRT)
#    yang tersimpan di dalam direktori penyimpanan persisten (Vault/Staging Area).
#
# 2. MITIGASI DATA I/O ANOMALY:
#    Mencegah anomali sistem (Data Ghosting) di mana modul pencatat mengklaim 
#    keberhasilan unduhan, namun berkas fisik gagal tertulis di ruang penyimpanan 
#    akibat interupsi jaringan atau kegagalan Input/Output (I/O).
# =============================================================================

import os
import pandas as pd
from dotenv import load_dotenv

# Memuat konfigurasi environment variables global demi konsistensi arsitektur data
load_dotenv()
DEFAULT_LOG_FILE = os.getenv("INTEL_DATASET_PATH", "data/staging/intel_dataset.csv")
DEFAULT_FILES_DIR = os.getenv("PSRE_FILES_DIR", "data/staging/psre_files")

def run_physical_audit():
    """
    Fungsi Eksekusi Audit Fisik:
    Menjalankan komparasi silang antara dataset log intelijen dengan alokasi file sistem.
    """
    print("\n" + "="*65)
    print("🕵️ SYSTEM AUDIT: CROSS-VALIDATION PROTOCOL (PHYSICAL VS LOG)")
    print("="*65)
    
    # Resolusi path dinamis guna menjamin kompatibilitas lingkungan Docker dan debugging lokal
    actual_csv_path = DEFAULT_LOG_FILE
    actual_files_dir = DEFAULT_FILES_DIR
    
    if not os.path.exists(actual_csv_path):
        # Taktik Fallback: Mencari jalur relatif jika skrip dieksekusi langsung dari sub-direktori scripts lokal
        alt_csv = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "staging", "intel_dataset.csv"))
        alt_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "staging", "psre_files"))
        if os.path.exists(alt_csv):
            actual_csv_path = alt_csv
            actual_files_dir = alt_dir

    # Pre-flight check keberadaan berkas dataset sebelum pembacaan buffer
    if not os.path.exists(actual_csv_path):
        print(f"❌ [CRITICAL ERROR] Berkas log dataset tidak ditemukan pada path: {actual_csv_path}")
        print("   Tindakan Penyelesaian: Pastikan subsistem otomasi scraper telah dieksekusi sebelumnya.")
        return

    try:
        df = pd.read_csv(actual_csv_path)
    except Exception as e:
        print(f"❌ [READ ERROR] Gagal membaca berkas CSV: {e}")
        return
        
    if df.empty:
        print("ℹ️ STATUS: Berkas log intel_dataset.csv terdeteksi kosong (Zero Records).")
        print("="*65 + "\n")
        return

    # Memfilter data secara eksklusif pada entri yang diklaim berhasil diunduh (SUCCESS)
    # serta mengeliminasi baris kosong (NaN) pada kolom file_name guna mencegah False Ghosting Alert
    success_entries = df[df['status'] == 'SUCCESS'].dropna(subset=['file_name'])
    
    total = len(success_entries)
    valid = 0

    print(f"[INFO] Ditemukan {total} entri log berstatus SUCCESS. Memulai verifikasi fisik...")

    # Iterasi pengecekan eksistensi berkas fisik di ruang penyimpanan vault
    for _, row in success_entries.iterrows():
        file_name_str = str(row['file_name']).strip()
        
        # Pengamanan berlapis jika string "nan" tak sengaja lolos ke tahap eksekusi
        if not file_name_str or file_name_str.lower() == "nan" or file_name_str == "None":
            print(f"⚠️ [LOG CORRUPTION] {row['psre_name']}: Entri log cacat, file_name bernilai Null!")
            continue
            
        file_path = os.path.join(actual_files_dir, file_name_str)
        
        if os.path.exists(file_path):
            print(f"✅ [VALIDATED] {row['psre_name']}: Berkas '{file_name_str}' teridentifikasi di penyimpanan.")
            valid += 1
        else:
            print(f"❌ [FILE MISSING] {row['psre_name']}: Berkas '{file_name_str}' tidak ditemukan (Potensi I/O Anomaly)!")

    print("="*65)
    print(f"📊 HASIL AUDIT FINAL: {valid} dari total {total} berkas log terverifikasi secara fisik.")
    
    # Konklusi evaluasi integritas
    if valid == total and total > 0:
        print("🛡️ STATUS: KONSISTENSI DATA 100% TERJAMIN (INTEGRITY SECURED).")
    elif total == 0:
        print("ℹ️ STATUS: Tidak ada entri log berstatus SUCCESS dan valid untuk diaudit pada periode ini.")
    else:
        print("⚠️ STATUS: Ditemukan inkonsistensi data biner (Data Ghosting Terdeteksi). Diperlukan peninjauan ulang pada storage engine.")
    
    print("="*65 + "\n")


if __name__ == "__main__":
    run_physical_audit()