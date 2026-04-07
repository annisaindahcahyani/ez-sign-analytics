#=============================================================================
#🕵️‍♂️ MODULE: WEB INTELLIGENCE & PSRE SCRAPER (THE "HUNTER" ENGINE)
#=============================================================================
#TUGAS UTAMA:
#1. Automated Audit: Melakukan pemindaian otomatis ke situs kompetitor/PSrE 
#   untuk memantau ketersediaan file CRL (Certificate Revocation List).
#2. Intelligence Gathering: Mengumpulkan file .crl, .cer, dan .crt publik 
#   sebagai bahan perbandingan validitas sertifikat di Fase 3 (W12).
#3. Compliance Check: Memastikan EzSign tetap kompetitif dengan memantau 
#   transparansi infrastruktur PSrE lain secara berkala.

#ALASAN TEKNIS:
#- Menggunakan Selenium (Web Automation) untuk menangani situs yang menggunakan 
#  JavaScript rendering berat.
#- Implementasi "Ethical Delay" (3-7s) untuk menghindari deteksi bot dan 
#  menjaga agar tidak membebani server target (DDoS protection).
#=============================================================================

import os
import time
import random
import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

# --- CONFIGURATION: TARGET AUDIT PSRE ---
# Daftar URL landing page PSrE yang akan diaudit ketersediaan file sertifikatnya.
TARGET_PSRE = {
    "Peruri": "https://www.peruri.co.id",
    "Privy": "https://privy.id",
    "Tilaka": "https://tilaka.id",
    "EzSign": "https://ezsign.id"
}

# Direktori penyimpanan hasil "intelijen" (Staging Data)
DOWNLOAD_DIR = os.path.join("..", "data", "staging", "psre_files")

def init_driver():
    """
    FUNGSI: INITIALIZE DRIVER
    -------------------------
    Tugas: Menyiapkan browser Chrome dalam mode 'Stealth' agar tidak 
    terblokir oleh satpam Cloudflare atau WAF (Web Application Firewall).
    """
    if not os.path.exists(DOWNLOAD_DIR):
        os.makedirs(DOWNLOAD_DIR)

    chrome_options = Options()
    # chrome_options.add_argument("--headless") # Gunakan mode siluman untuk running di server/Docker
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    # User-Agent palsu biar dikira manusia beneran, bukan bot pusing.
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36")
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def download_file(url, folder, psre_name):
    """
    FUNGSI: FILE DOWNLOADER EXECUTIONER
    -----------------------------------
    Tugas: Mengunduh file biner (.crl/.cer) menggunakan library 'requests' 
    agar lebih stabil dibandingkan download via browser langsung.
    """
    try:
        # Menamai file berdasarkan PSrE asal agar tidak tertukar (Mapping Data)
        local_filename = f"{psre_name}_{url.split('/')[-1]}"
        path = os.path.join(folder, local_filename)
        
        # Stream=True digunakan untuk menangani file besar tanpa memakan RAM berlebih
        response = requests.get(url, stream=True, timeout=15)
        with open(path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"   [DONE] Intelijen tersimpan: {path}")
    except Exception as e:
        print(f"   [FAILED] Gagal mengunduh {url}: {e}")

def run_web_intelligence():
    """
    FUNGSI UTAMA: WEB INTELLIGENCE SCRAPER
    --------------------------------------
    Tugas: Menjalankan skenario audit otomatis Fase 3.
    """
    print("\n" + "="*50)
    print("🚀 EZSIGN ANALYTICS: WEB INTELLIGENCE ENGINE ACTIVE")
    print("="*50)
    
    driver = init_driver()
    
    try:
        for name, url in TARGET_PSRE.items():
            print(f"\n[*] Memulai Audit PSrE: {name} ({url})")
            driver.get(url)
            
            # --- ETHICAL DELAY (ANTI-BAN) ---
            # Meniru perilaku manusia yang membaca halaman selama 3-7 detik.
            delay = random.randint(3, 7)
            print(f"[!] Menerapkan Ethical Delay {delay} detik...")
            time.sleep(delay)

            # --- LOGIKA DETEKTIF (X-PATH SCANNING) ---
            # Mencari elemen <a> yang memiliki href dengan ekstensi sertifikat digital.
            xpath_query = "//a[contains(@href, '.crl') or contains(@href, '.cer') or contains(@href, '.crt')]"
            links = driver.find_elements(By.XPATH, xpath_query)
            
            if not links:
                print(f"   [?] Hasil: Tidak ada file sertifikat publik terdeteksi di landing page.")
            else:
                print(f"   [FOUND] Berhasil mendeteksi {len(links)} file intelijen!")
                for link in links:
                    file_url = link.get_attribute("href")
                    # Pastikan URL bersifat absolut
                    if file_url and file_url.startswith("http"):
                        print(f"   [->] Downloading: {file_url}")
                        download_file(file_url, DOWNLOAD_DIR, name)

    except Exception as e:
        print(f"\n[CRITICAL ERROR] Arsitektur Scraper Mengalami Kegagalan: {e}")
    finally:
        # Menutup browser secara bersih agar tidak ada proses 'chromedriver' yang menggantung (zombie process)
        driver.quit()
        print("\n" + "="*50)
        print("✅ SCRAPING SESSION FINISHED. DATA SECURED. SLAY! 💅")
        print("="*50)

if __name__ == "__main__":
    run_web_intelligence()