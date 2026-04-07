# =============================================================================
# 🛠️ MODULE: EZSIGN AUTOMATED FILE WATCHER (THE "SATPAM" ENGINE)
# =============================================================================
# TUGAS UTAMA:
# 1. Monitoring Real-time: Memantau folder staging secara terus-menerus.
# 2. Automated Ingestion: Mendeteksi PDF baru dan memicu proses ekstraksi secara otomatis.
# 3. Stability Guard: Menangani issue "Race Condition" saat file sedang di-copy.

# ALASAN TEKNIS (FOR DEVELOPERS):
# - Mengapa PollingObserver? Docker/Network Drive sering gagal mengirim event 'inotify'
#   native. Polling memastikan deteksi tetap jalan di environment container.
# - Mengapa Sleep 2s? Mencegah 'File Permission Error' karena library mencoba membaca
#   PDF yang proses copy-nya belum selesai 100%.

# ALUR KERJA:
# File Masuk -> Trigger event_handler -> Validasi Ekstensi -> Wait 2s -> Extractor
# =============================================================================

import time
import os
# Menggunakan PollingObserver (Bukan Observer biasa) karena sistem file di Docker/Network 
# sering kali tidak mengirimkan event 'inotify' secara native.
from watchdog.observers.polling import PollingObserver as Observer
from watchdog.events import FileSystemEventHandler
from extractor import process_metadata

class EzSignHandler(FileSystemEventHandler):
    def on_modified(self, event):
        # Trigger saat file yang sudah ada di-update atau ditimpa (misal: re-upload)
        self.process(event)

    def on_created(self, event):
        # Trigger saat ada file baru yang baru saja masuk ke folder
        self.process(event)
    
    def process(self, event):
        """
        LOGIKA INGESTION: Memastikan hanya file PDF/JSON yang diproses.
        """
        # Print log untuk kebutuhan debugging setiap ada aktivitas file system
        print(f"🔍 [DEBUG] Ada gerakan di: {event.src_path}")

        # Validasi: Pastikan objek bukan direktori dan memiliki ekstensi yang diizinkan
        if not event.is_directory and event.src_path.lower().endswith(('.pdf', '.json')):
            print(f"🆕 [WATCHER] File valid terdeteksi: {os.path.basename(event.src_path)}")

            # RACE CONDITION PROTECTION:
            # Memberikan jeda 2 detik agar proses copy file dari luar kontainer selesai sempurna
            # sebelum file tersebut dibuka oleh library extractor (mencegah error 'File in Use').
            time.sleep(2) 

            try:
                # Memanggil core logic untuk ekstraksi metadata TTE
                process_metadata(event.src_path)
                print(f"✅ [WATCHER] Sukses proses: {os.path.basename(event.src_path)}")
            except Exception as e:
                # Error Catching agar satpam (watcher) tidak 'pingsan' saat satu file korup
                print(f"❌ [WATCHER] Error pas eksekusi extractor: {e}")

if __name__ == "__main__":
    # Paksa pake path Docker yang kita tau tadi 'ls'-nya ada
    # DIRECTORY CONFIGURATION:
    WATCH_DIRECTORY = "/data/staging"

    # Inisialisasi Satpam ezSign (Polling Mode)
    print(f"🕵️‍♂️ Satpam ezSign (Polling Mode) mantau: {WATCH_DIRECTORY}")
    
    event_handler = EzSignHandler()

    # Timeout=1: Melakukan scanning folder setiap 1 detik secara konsisten.
    observer = Observer(timeout=1) # Cek tiap 1 detik
    observer.schedule(event_handler, WATCH_DIRECTORY, recursive=False)
    observer.start()
    
    try:
        # Menjaga script agar tetap running selamanya (Daemon-like)
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        # Shutdown sequence yang rapi saat user menekan Ctrl+C
        print("🛑 [WATCHER] Mematikan sistem monitoring...")
        observer.stop()
    observer.join()