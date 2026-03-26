import os
import glob
import time

def auto_purge_raw_files(staging_path, threshold_seconds=3600):
    """
    Compliance Engine: Menghapus file dump mentah (JSON/PDF) setelah proses
    ingestion selesai guna mematuhi prinsip Data Minimization UU PDP.
    """
    now = time.time()
    # Cari semua file di folder staging
    files = glob.glob(os.path.join(staging_path, "*.*"))
    
    purged_count = 0
    for f in files:
        # Jika file lebih lama dari threshold (misal 1 jam)
        if os.stat(f).st_mtime < now - threshold_seconds:
            os.remove(f)
            purged_count += 1
            
    return purged_count

if __name__ == "__main__":
    print(f"[UU-PDP] Auto-purge active. Cleaning residual data...")