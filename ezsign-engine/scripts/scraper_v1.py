import os
import time
import random
import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

# --- CONFIGURATION KASTA ELIT ---
TARGET_PSRE = {
    "Peruri": "https://www.peruri.co.id",
    "Privy": "https://privy.id",
    "Tilaka": "https://tilaka.id",
    "EzSign": "https://ezsign.id"
}

# Folder tempat nyimpen hasil rampokan data
DOWNLOAD_DIR = os.path.join("..", "data", "staging", "psre_files")

def init_driver():
    """Inisialisasi Driver kasta pro biar gak kena ban satpam Cloudflare"""
    if not os.path.exists(DOWNLOAD_DIR):
        os.makedirs(DOWNLOAD_DIR)

    chrome_options = Options()
    # chrome_options.add_argument("--headless") # Buka ini kalo mau mode siluman (tanpa jendela)
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36")
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def download_file(url, folder, psre_name):
    """Fungsi eksekutor buat download file CRL/CER secara beretika"""
    try:
        local_filename = f"{psre_name}_{url.split('/')[-1]}"
        path = os.path.join(folder, local_filename)
        
        response = requests.get(url, stream=True, timeout=10)
        with open(path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"   [DONE] File tersimpan di: {path}")
    except Exception as e:
        print(f"   [FAILED] Gagal download {url}: {e}")

def run_web_intelligence():
    """Otak utama Automated Web Intelligence Fase 3"""
    print("=== EZSIGN ANALYTICS: WEB INTELLIGENCE SCRAPER ACTIVE ===")
    driver = init_driver()
    
    try:
        for name, url in TARGET_PSRE.items():
            print(f"\n[*] Mengaudit PSrE: {name} ({url})")
            driver.get(url)
            
            # Ethical Delay sesuai Audit W12 (3-7 detik)
            delay = random.randint(3, 7)
            print(f"[!] Menunggu {delay} detik agar tidak membebani server...")
            time.sleep(delay)

            # --- LOGIKA DETEKTIF (Nyari Link CRL/CER) ---
            # Mencari semua link <a> yang punya ekstensi file sertifikat
            links = driver.find_elements(By.XPATH, "//a[contains(@href, '.crl') or contains(@href, '.cer') or contains(@href, '.crt')]")
            
            if not links:
                print(f"   [?] Tidak ada link CRL publik yang terdeteksi di landing page.")
            else:
                print(f"   [FOUND] Terdeteksi {len(links)} file intelijen!")
                for link in links:
                    file_url = link.get_attribute("href")
                    print(f"   [->] Mendownload: {file_url}")
                    download_file(file_url, DOWNLOAD_DIR, name)

    except Exception as e:
        print(f"[CRITICAL ERROR] Arsitektur Scraper meledak: {e}")
    finally:
        driver.quit()
        print("\n=== SCRAPING SESSION FINISHED. SLAY! ===")

if __name__ == "__main__":
    run_web_intelligence()