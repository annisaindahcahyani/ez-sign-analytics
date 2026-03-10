import time
import os
from watchdog.observers.polling import PollingObserver as Observer
from watchdog.events import FileSystemEventHandler
from extractor import process_metadata

class EzSignHandler(FileSystemEventHandler):
    def on_modified(self, event):
        self.process(event)
    def on_created(self, event):
        self.process(event)
    
    def process(self, event):
        # Print setiap ada gerakan sekecil apapun di folder
        print(f"🔍 [DEBUG] Ada gerakan di: {event.src_path}")
        
        if not event.is_directory and event.src_path.lower().endswith(('.pdf', '.json')):
            print(f"🆕 [WATCHER] File valid terdeteksi: {os.path.basename(event.src_path)}")
            time.sleep(2) 
            try:
                process_metadata(event.src_path)
                print(f"✅ [WATCHER] Sukses proses: {os.path.basename(event.src_path)}")
            except Exception as e:
                print(f"❌ [WATCHER] Error pas eksekusi extractor: {e}")

if __name__ == "__main__":
    # Paksa pake path Docker yang kita tau tadi 'ls'-nya ada
    WATCH_DIRECTORY = "/data/staging"
    
    print(f"🕵️‍♂️ Satpam ezSign (Polling Mode) mantau: {WATCH_DIRECTORY}")
    
    event_handler = EzSignHandler()
    observer = Observer(timeout=1) # Cek tiap 1 detik
    observer.schedule(event_handler, WATCH_DIRECTORY, recursive=False)
    observer.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()