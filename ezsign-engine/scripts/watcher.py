# =============================================================================
# 📡 MODULE: AUTOMATED FILE INGESTION WATCHER (DAEMON PROCESS)
# =============================================================================
# 📌 CONFIGURATION : Staging Area Monitoring System
# 📅 UPDATE        : 5 Juni 2026
# 🔬 CORE ENGINE   : Watchdog PollingObserver
# 🛡️ OBJECTIVE     : Mendeteksi masuknya berkas baru (PDF/JSON) dan memicu 
#                    eksekusi pipeline ekstraksi metadata secara otomatis.
# =============================================================================
# 🗺️ DOKUMEN TATA KERJA FUNGSIONAL PENGEMBANG (FOR NEXT DEVELOPER):
#
# 1. ARSITEKTUR POLLING OBSERVER:
#    Skrip ini tidak menggunakan observer native ('inotify'), melainkan mengadopsi 
#    PollingObserver. Hal ini dikarenakan lingkungan terisolasi seperti Docker Container 
#    atau Network Drive seringkali gagal mengirimkan sinyal perubahan berkas (file system events) 
#    secara native ke lapisan kernel Linux. Polling menjamin deteksi tetap konsisten.
#
# 2. MITIGASI RACE CONDITION (I/O DELAY):
#    Terdapat mekanisme penundaan eksekusi buatan (time.sleep(2)) setelah berkas baru 
#    dideteksi. Fungsi ini memberikan jeda kritis agar proses transfer/penyalinan I/O 
#    dari host menuju kontainer selesai dengan sempurna, mencegah munculnya galat 
#    'File in Use' atau 'Corrupted Stream' saat proses ekstraksi berlangsung.
#
# 3. KETAHANAN SISTEM (FAULT TOLERANCE):
#    Eksekusi modul ekstraktor (process_metadata) dibungkus dalam blok try-except absolut.
#    Tujuannya agar Daemon Process ini tidak mengalami crash (berhenti beroperasi) 
#    hanya karena menemukan satu berkas yang korup atau terenkripsi ganda.
# =============================================================================

import time
import os
from dotenv import load_dotenv

# Memanfaatkan PollingObserver untuk menjamin fungsionalitas deteksi di dalam Docker Volume
from watchdog.observers.polling import PollingObserver as Observer
from watchdog.events import FileSystemEventHandler
from extractor import process_metadata

# Memuat konfigurasi environment variables global
load_dotenv()
DEFAULT_WATCH_DIR = os.getenv("STAGING_PATH", "data/staging")

class EzSignHandler(FileSystemEventHandler):
    """
    Kelas Pendengar Aktivitas (Event Handler):
    Bertugas mendefinisikan respon sistem terhadap manipulasi berkas di ruang penyimpanan.
    """
    def __init__(self):
        super().__init__()
        # Cache internal untuk mencegah duplikasi eksekusi berkas dalam rentang waktu berdekatan (De-duplication Buffer)
        self.recent_processed = {}

    def on_created(self, event):
        """Memicu proses eksklusif saat alokasi berkas baru pertama kali tercipta."""
        self.process(event)
    
    def process(self, event):
        """
        Logika Pemrosesan Ingestion:
        Menyeleksi ekstensi berkas yang valid sebelum dialirkan menuju modul ekstraktor forensik.
        """
        # Eliminasi deteksi jika objek yang tertangkap adalah struktur direktori
        if event.is_directory:
            return

        src_path = event.src_path
        filename = os.path.basename(src_path)

        # --- [BENTENG PROTEKSI 1: TEMPORARY FILE BLOCKER] ---
        # Menolak berkas sampah sementara hasil sinkronisasi OS host / browser buffer
        if filename.startswith("~$") or filename.startswith(".") or filename.endswith(".tmp"):
            return

        # Validasi Skema: Memastikan file mematuhi ekstensi kriptografi dan log target
        if src_path.lower().endswith(('.pdf', '.json')):
            now = time.time()
            
            # --- [BENTENG PROTEKSI 2: DE-DUPLICATION COOLDOWN LAYER] ---
            # Jika berkas yang sama tertangkap dua kali dalam rentang 3 detik, abaikan trigger kedua
            if src_path in self.recent_processed:
                if now - self.recent_processed[src_path] < 3:
                    return
            
            self.recent_processed[src_path] = now
            print(f"🆕 [INGESTION ALERT] Berkas valid teridentifikasi: {filename}")

            # --- [RACE CONDITION PROTECTION PROTOCOL] ---
            # Jeda waktu kritis 2 detik untuk menjamin operasi write stream dari hulu I/O selesai sempurna (EOF)
            time.sleep(2) 

            try:
                # Mengeksekusi modul inti (Core Logic) untuk ekstraksi metadata kriptografi TTE
                result = process_metadata(src_path)
                print(f"✅ [PROCESS COMPLETED] Berkas '{filename}' berhasil diekstraksi ke warehouse.")
                
            except Exception as e:
                # Isolasi kegagalan agar tidak merusak keberlangsungan Daemon Process secara global
                print(f"❌ [EXTRACTION ERROR] Gagal melakukan ekstraksi forensik pada berkas '{filename}'. Detail: {e}")


if __name__ == "__main__":
    print("\n" + "="*65)
    print("📡 [DAEMON INITIALIZED] EZSIGN AUTOMATED FILE WATCHER ACTIVATED")
    print("="*65)
    
    # Sinkronisasi path otomatis yang adaptif terhadap mounting container Docker maupun lokal workstation
    WATCH_DIRECTORY = DEFAULT_WATCH_DIR
    if WATCH_DIRECTORY == "/data/staging" and not os.path.exists(WATCH_DIRECTORY):
        WATCH_DIRECTORY = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "staging"))

    print(f"[INFO] Lapisan Polling Aktif Mengawasi Direktori: {os.path.abspath(WATCH_DIRECTORY)}")
    
    event_handler = EzSignHandler()

    # Mengatur interval pooling pemindaian direktori setiap 1 detik demi efisiensi resource CPU
    observer = Observer(timeout=1) 
    observer.schedule(event_handler, WATCH_DIRECTORY, recursive=False)
    observer.start()
    
    try:
        # Loop tak berhingga (Infinite Loop Execution) untuk menjaga status keaktifan background service
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n🛑 [SYSTEM HALT] Menerima sinyal interupsi manual. Menghentikan Daemon Watcher...")
        observer.stop()
        
    # Menjamin seluruh antrean data diselesaikan secara bersih sebelum terminasi service (Graceful Shutdown)
    observer.join()
    print("[STATUS] Daemon Process Dihentikan Dengan Aman. Wilayah Staging Dilepas.")
    print("="*65 + "\n")