import time
import os
import sys
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from dotenv import load_dotenv
from extractor import process_metadata # Import otak ETL lo

# 1. Load Environment Variables
load_dotenv()

# 2. Konfigurasi Path yang Fleksibel (Laptop vs Docker)
# os.getenv bakal nyari STAGING_PATH di .env. Kalo ga ada, default ke 'data/staging' (Windows friendly)
WATCH_DIRECTORY = os.getenv('STAGING_PATH', 'data/staging')

class EzSignHandler(FileSystemEventHandler):
    """
    Si 'Satpam' yang bakal bereaksi kalo ada file baru di folder staging.
    """
    def on_created(self, event):
        # Cek apakah yang masuk itu beneran file dan formatnya .pdf atau .json
        if not event.is_directory and event.src_path.lower().endswith(('.pdf', '.json')):
            print(f"\n🆕 [WATCHER] Detect file baru: {os.path.basename(event.src_path)}")
            
            # Kasih jeda 1 detik biar file beres ke-copy sempurna (terutama di Docker/Network Drive)
            time.sleep(1) 
            
            try:
                # Panggil otak ETL lo buat proses filenya
                process_metadata(event.src_path)
                print(f"✅ [WATCHER] Sukses proses: {os.path.basename(event.src_path)}")
                
            except Exception as e:
                print(f"❌ [WATCHER] Error pas eksekusi extractor: {e}")

if __name__ == "__main__":
    # 3. Pastiin folder staging-nya ada secara fisik di laptop/container
    if not os.path.exists(WATCH_DIRECTORY):
        os.makedirs(WATCH_DIRECTORY)
        print(f"📁 Created directory: {os.path.abspath(WATCH_DIRECTORY)}")

    event_handler = EzSignHandler()
    observer = Observer()
    
    # Daftarkan folder yang mau dijagain
    observer.schedule(event_handler, WATCH_DIRECTORY, recursive=False)
    
    # 4. Kata-kata mutiara biar Satpam lo kelihatan Slay 💅
    print(f"🕵️‍♂️ Satpam ezSign mulai berjaga di: {os.path.abspath(WATCH_DIRECTORY)}")
    print(f"📢 Silakan masukkan file PDF/JSON ke folder staging untuk ngetes...")
    
    observer.start()
    
    try:
        while True:
            time.sleep(1) # Biar loop-nya gak makan CPU berlebihan
    except KeyboardInterrupt:
        observer.stop()
        print("\n🛑 Watcher dihentikan oleh user.")
    
    observer.join()