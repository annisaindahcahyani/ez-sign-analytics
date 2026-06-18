# =============================================================================
# 🐳 DOCKERFILE: EZSIGN ANALYTICS ENGINE (CORE BACKEND SERVICE)
# =============================================================================
# 📌 CONFIGURATION : Python FastAPI & Extraction Engine Environment
# 📅 UPDATE        : 5 Juni 2026
# 🛡️ OBJECTIVE     : Isolasi Lingkungan Komputasi Berperforma Tinggi
# ⚙️ ARCHITECTURE  : Headless lightweight environment with Docker layer caching
# =============================================================================

# --- [1] BASE IMAGE LAYER ---
# Mengadopsi Python 3.11-slim untuk mereduksi footprint ukuran image kontainer
# serta meminimalisir area kerentanan keamanan (Vulnerability Attack Surface).
FROM python:3.11-slim

# --- [2] WORKING DIRECTORY INITIALIZATION ---
# Menetapkan direktori operasional utama di dalam ruang lingkup kontainer virtual.
WORKDIR /app

# --- [3] NATIVE SYSTEM DEPENDENCIES ---
# Instalasi pustaka native OS (sqlite3 & curl) guna mendukung stabilitas transaksi database 
# dan pre-flight healthcheck. Pembersihan cache APT dieksekusi seketika demi efisiensi space disk.
RUN apt-get update && apt-get install -y \
    sqlite3 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# --- [4] DEPENDENCY MANAGEMENT (CACHED LAYER OPTIMIZATION) ---
# Menyalin manifest berkas requirements.txt secara terisolasi guna memaksimalkan 
# fitur Docker Layer Caching dan mempercepat durasi Continuous Integration (CI).
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# --- [5] SOURCE CODE INGESTION LAYER ---
# Menginjeksi seluruh skrip aplikasi antarmuka, backend core API, dan engine ekstraktor forensik.
COPY . .

# --- [6] NETWORKING & PORT CONFIGURATION ---
# Mengekspos jalur komunikasi data kontainer secara eksklusif pada port internal default FastAPI.
EXPOSE 8000

# --- [7] DAEMON ENTRYPOINT EXECUTION ---
# Mengeksekusi ASGI gateway server (api.py) pada antarmuka jaringan global kontainer 
# guna mengaktifkan kapabilitas port forwarding tanpa hambatan Same-Origin Policy.
CMD ["python", "api.py"]