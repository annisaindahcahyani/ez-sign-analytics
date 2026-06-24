# =============================================================================
# 📡 MODULE: AUTOMATED COMPETITOR WEB INTELLIGENCE SCRAPER ENGINE
# =============================================================================
# 📌 CONFIGURATION : Selenium WebDriver Framework Architecture
# 📅 UPDATE        : 5 Juni 2026
# 🔬 CORE MODULE   : Selenium Headless Stealth Browser & Beautiful Soup 4
# 🛡️ VALIDASI TI   : Anti-Hoax Verification Protocol Level 3 (HTTP Header Audit)
# =============================================================================
# 🗺️ DOKUMEN TATA KERJA FUNGSIONAL PENGEMBANG (FOR NEXT DEVELOPER):
#
# 1. MEKANISME AGENT MONITORING (STEALTH HARVESTING):
#    Skrip ini merealisasikan target Capaian Silabus Kegiatan 4 (Web Intelligence).
#    Diberdayakan secara otomatis menggunakan WebDriver Microsoft Edge dalam mode 
#    siluman (--headless, --no-sandbox) untuk memindai repositori publik kompetitor.
#
# 2. PROTOKOL VALIDASI ANTI-HOAX LEVEL 3:
#    Sebelum mengeksekusi pengunduhan berkas kriptografi (PDF/CRL/CRT/CER), mesin 
#    wajib melakukan audit pre-flight HTTP HEAD request. Jika tipe konten 
#    mengembalikan rumpun 'text/html', berkas dinyatakan sebagai error page samaran 
#    dan dialirkan menuju status log 'VALIDATION_FAILED_HTML'.
#
# 3. STRATEGI REKAYASA PENYIMPANAN PERSISTEN:
#    Log hasil pemindaian langsung dimuat secara komprehensif ke dalam berkas 
#    'intel_dataset.csv' pada staging area lokal untuk disinkronisasikan menuju 
#    komponen real-time fragment dashboard analitik Streamlit.
# =============================================================================

import os
import time
import random
import requests
import csv
import json
import re
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import urljoin

# --- SELENIUM CORE LIBRARIES ---
from selenium import webdriver
from selenium.webdriver.common.by import By 
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.edge.options import Options as EdgeOptions 
from webdriver_manager.microsoft import EdgeChromiumDriverManager

# --- ARCHITECTURAL PATH CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__)) 
ROOT_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", ".."))

CONFIG_FILE = os.path.join(ROOT_DIR, "data", "config", "targets.json")
DOWNLOAD_DIR = os.path.join(ROOT_DIR, "data", "staging", "psre_files")
LOG_FILE = os.path.join(ROOT_DIR, "data", "staging", "intel_dataset.csv")

print(f"[INFO] Direktori Kerja Basis  : {BASE_DIR}")
print(f"[INFO] Direktori Kerja Utama  : {ROOT_DIR}")
print(f"[INFO] Jalur Dataset Log Log  : {LOG_FILE}")


def load_intelligence_targets():
    """Membaca daftar target URI PSrE dari berkas konvensional JSON agar sistem tidak bersifat hardcoded."""
    if not os.path.exists(CONFIG_FILE):
        # Fallback dinamis jika struktur direktori Docker mengalami pergeseran mounting volume
        alt_config = os.path.join(os.path.dirname(ROOT_DIR), "data", "config", "targets.json")
        if os.path.exists(alt_config):
            with open(alt_config, 'r') as f:
                data = json.load(f)
                return {item['name']: item['url'] for item in data['psre_list']}
        print(f"❌ [CONFIGURATION ERROR] Berkas targets.json absen total.")
        return {}
        
    try:
        with open(CONFIG_FILE, 'r') as f:
            data = json.load(f)
            return {item['name']: item['url'] for item in data['psre_list']}
    except Exception as e:
        print(f"❌ [CRITICAL SYSTEM ERROR] Gagal memuat komponen konfigurasi targets.json: {e}")
        return {}


def init_driver():
    """Inisialisasi lingkungan peramban Edge virtual dengan konfigurasi Argumen Keamanan Kontainer Headless."""
    if not os.path.exists(DOWNLOAD_DIR):
        os.makedirs(DOWNLOAD_DIR)
   
    edge_options = EdgeOptions()
    edge_options.add_argument("--headless=new")  # Menggunakan mesin headless modern yang kompatibel dengan kontainer Linux
    edge_options.add_argument("--no-sandbox")
    edge_options.add_argument("--disable-dev-shm-usage")
    edge_options.add_argument("--disable-gpu")
    edge_options.add_argument("--blink-features=AutomationControlled") # Penyamaran identitas bot (Anti-Bot Detection Bypass)
   
    try:
        service = EdgeService(EdgeChromiumDriverManager().install())
    except Exception:
        print("[WARNING] Konstruksi repositori driver eksternal terkendala. Mengaktifkan sistem lokal binary fallback.")
        service = EdgeService()
   
    print("[INFO] Meluncurkan Microsoft Edge Driver: Modul Stealth Hunter Berstatus Aktif.")
    return webdriver.Edge(service=service, options=edge_options)


def log_intelligence(psre_name, file_name, url, status):
    """Mencatat log forensik hasil aktivitas scanning market intelijen ke dalam dataset staging."""
    # Menjamin isolasi path log file mandiri sebelum penulisan buffer
    actual_log_file = LOG_FILE
    log_dir = os.path.dirname(actual_log_file)
    if not os.path.exists(log_dir): 
        os.makedirs(log_dir)
        
    file_exists = os.path.isfile(actual_log_file)
   
    with open(actual_log_file, mode='a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(['timestamp', 'psre_name', 'file_name', 'source_url', 'status'])
        writer.writerow([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), psre_name, file_name, url, status])
        f.flush()  # Paksa flush ke memori disk untuk mencegah korupsi pembacaan simultan oleh Streamlit


def download_file(url, psre_name):
    """Mengeksekusi pengunduhan berkas dengan implementasi Protokol Validasi Anti-Hoax Level 3."""
    try:
        # --- [LEVEL 3 VALIDATION PROTOCOL: HTTP HEAD PRE-FLIGHT CHECK] ---
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
        head_check = requests.head(url, headers=headers, timeout=10, allow_redirects=True)
        content_type = head_check.headers.get('Content-Type', '').lower()
       
        # Mencegah pengunduhan dokumen bayangan yang ternyata halaman HTML error samaran
        if 'text/html' in content_type:
            print(f"⚠️ [VALIDATION FAILED] Payload URL {url} terindikasi anomali non-kriptografi (Halaman Web/HTML Terdeteksi).")
            log_intelligence(psre_name, "N/A", url, "VALIDATION_FAILED_HTML")
            return

        pure_filename = url.split('/')[-1].split('?')[0]  # Menghilangkan parameter query URI agar ekstensi file bersih
        if not pure_filename:
            pure_filename = f"extracted_asset_{int(time.time())}.pdf"
            
        file_name = f"{psre_name}_{pure_filename}"
        file_name = "".join(x for x in file_name if x.isalnum() or x in "._-")
        path = os.path.join(DOWNLOAD_DIR, file_name)

        # SATPAM DEDUPLIKASI: Cek dulu barangnya udah ada apa belum!
        if os.path.exists(path):
            print(f"⏩ [DEDUPLICATION] Berkas {file_name} sudah eksis di lokal. Membatalkan pengunduhan berulang.")
            log_intelligence(psre_name, file_name, url, "SUCCESS_CACHED")
            return  # Langsung keluar, nggak usah lanjut download!

        # Pemrosesan stream unduhan biner
        response = requests.get(url, headers=headers, stream=True, timeout=15)
        if response.status_code == 200:
            pure_filename = url.split('/')[-1].split('?')[0]  # Menghilangkan parameter query URI agar ekstensi file bersih
            if not pure_filename:
                pure_filename = f"extracted_asset_{int(time.time())}.pdf"
                
            file_name = f"{psre_name}_{pure_filename}"
            file_name = "".join(x for x in file_name if x.isalnum() or x in "._-")
            path = os.path.join(DOWNLOAD_DIR, file_name)
           
            with open(path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
           
            print(f"✅ [ACQUISITION SUCCESS] Berkas Berhasil Diamankan: {file_name}")
            log_intelligence(psre_name, file_name, url, "SUCCESS")
        else:
            log_intelligence(psre_name, "N/A", url, f"FAILED_HTTP_{response.status_code}")
            
    except Exception as e:
        log_intelligence(psre_name, "N/A", url, f"ERROR_{type(e).__name__}")


def run_web_intelligence():
    """Fungsi Utama: Mengeksekusi iterasi pemindaian siber tertarget berdasarkan daftar instansi PSrE."""
    print("\n" + "="*65)
    print("🚀 EZSIGN ANALYTICS: TARGETED WEB INTELLIGENCE PIPELINE OPERATIONAL")
    print("="*65)
   
    TARGET_PSRE = load_intelligence_targets()
    if not TARGET_PSRE: 
        print("⚠️ [SYSTEM ALERT] Target akuisisi kosong. Membatalkan eksekusi pipeline.")
        return

    driver = init_driver()
    try:
        for name, base_url in TARGET_PSRE.items():
            try:
                print(f"\n[*] Mengunci Koordinat Target Akuisisi: {name} | Domain: {base_url}")
                driver.get(base_url)
               
                # Strategi Penundaan Acak (Polite Scraping / Human Mimicry Delay) guna menghindari IP Banning
                time.sleep(random.randint(4, 7))

                # Implementasi Evaluasi XPath Query untuk Menjaring Struktur Ekstensi Kriptografi & Kebijakan Cert
                xpath_query = "//a[contains(@href, '.pdf') or contains(@href, '.crt') or contains(@href, '.cer') or contains(@href, '.crl')]"
                elements = driver.find_elements(By.XPATH, xpath_query)
               
                if not elements:
                    print(f"ℹ️ [INFO] Tidak ditemukan eksposur dokumen kriptografi aktif pada domain {name}.")
                    log_intelligence(name, "None", base_url, "NO_FILES")
                else:
                    print(f"📥 [HARVESTING] Berhasil mengidentifikasi {len(elements)} tautan relevan. Memulai pre-flight validation...")
                    
                    # Mengamankan raw href string untuk mencegah StaleElementReferenceException runtime error
                    urls_to_download = []
                    for el in elements:
                        try:
                            raw_url = el.get_attribute("href")
                            if raw_url:
                                # Resolusi otomatis tautan relatif menjadi bentuk URI absolut mutlak
                                absolute_url = urljoin(base_url, raw_url)
                                urls_to_download.append(absolute_url)
                        except Exception:
                            continue
                            
                    # Eksekusi unduhan dari daftar antrean yang steril
                    for target_url in list(set(urls_to_download)):
                        download_file(target_url, name)
           
            except Exception as e:
                print(f"❌ [CONNECTION ERROR] Gagal melakukan penetrasi akses menuju target {name}. Detail: {e}")
                log_intelligence(name, "N/A", base_url, "CONNECTION_ERROR")
                continue
           
    finally:
        try:
            driver.quit()
        except Exception:
            pass
        print("\n" + "="*65)
        print("✅ PIPELINE COMPLETED: PROSES AKUISISI PASAR SELESAI PARIPURNA.")
        print("="*65 + "\n")


if __name__ == "__main__":
    run_web_intelligence()