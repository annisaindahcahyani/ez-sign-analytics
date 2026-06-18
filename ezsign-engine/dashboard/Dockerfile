# =============================================================================
# 🐳 DOCKERFILE: EZSIGN ANALYTICS DASHBOARD SERVICE (VISUALIZER LAYER)
# =============================================================================
# 📌 CONFIGURATION : Streamlit Web Application Interface
# 📅 UPDATE        : 5 Juni 2026
# 🛡️ SPECIFICATION : Headless lightweight environment with Docker layer caching
# =============================================================================

# --- [1] BASE IMAGE INTERFACES ---
# Mengadopsi Python 3.11-slim untuk mereduksi footprint ukuran image kontainer
# serta meminimalisir area kerentanan keamanan (Vulnerability Attack Surface).
FROM python:3.11-slim

# --- [2] APPLICATION WORKING DIRECTORY ---
# Menetapkan direktori operasional utama di dalam ruang lingkup kontainer virtual.
WORKDIR /app

# --- [3] NATIVE SYSTEM DEPENDENCIES & UTILITIES ---
# Instalasi pustaka native OS (build-essential dan curl) untuk mendukung kompilasi
# internal C-extension. Pembersihan cache APT (apt-get clean-up) dieksekusi 
# dalam layer yang sama demi efisiensi kapasitas space image.
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# --- [4] DEPENDENCY MANAGEMENT (CACHED LAYER OPTIMIZATION) ---
# Menyalin manifest berkas requirements.txt secara terisolasi guna memaksimalkan 
# fitur Docker Layer Caching dan mempercepat durasi Continuous Integration (CI).
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# --- [5] SOURCE CODE INGESTION LAYER ---
# Menginjeksi seluruh struktur kode sumber antarmuka, modul visualisasi, 
# dan aset statis ke dalam lingkungan eksekusi kontainer.
COPY . .

# --- [6] NETWORKING & PORT CONFIGURATION ---
# Mengekspos jalur komunikasi data kontainer secara eksklusif pada port internal 
# default framework Streamlit.
EXPOSE 8501

# --- [7] DAEMON ENTRYPOINT EXECUTION ---
# Mengeksekusi framework Streamlit pada antarmuka jaringan global (0.0.0.0) 
# dalam mode headless guna mencegah interaksi prompt eksternal di dalam kontainer.
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true"]