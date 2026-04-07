# =================================================================
# 🐳 DOCKERFILE: EZSIGN ANALYTICS ENGINE
# =================================================================
# Mengisolasi seluruh environment Python agar sistem "Slay" di server mana pun.
# =================================================================

# --- [1] BASE IMAGE ---
# Menggunakan Python 3.11-slim agar ukuran image tetap ringan (Lightweight)
# dan meminimalisir celah keamanan (Vulnerability).
FROM python:3.11-slim

# --- [2] ENVIRONMENT SETUP ---
# Menentukan folder kerja utama di dalam kontainer.
WORKDIR /app

# --- [3] SYSTEM DEPENDENCIES ---
# Instalasi SQLite3 secara native di OS kontainer untuk menjamin stabilitas query.
# Clean-up dilakukan di baris yang sama untuk menjaga image tetap ramping.
RUN apt-get update && apt-get install -y sqlite3 && rm -rf /var/lib/apt/lists/*

# --- [4] DEPENDENCY MANAGEMENT (The Caching Trick) ---
# Copy requirements.txt secara terpisah agar Docker bisa melakukan "Caching Layer".
# Jika tidak ada perubahan di file requirements, proses build berikutnya akan super kencang!
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# --- [5] SOURCE CODE INGESTION ---
# Menyalin seluruh script kodingan (Logic Engine, API, & Enricher) ke dalam kontainer.
COPY . .

# --- [6] STORAGE STRUCTURE (Volume Preparation) ---
# Membuat direktori permanen untuk sinkronisasi data PDF & Database SQLite.
# Folder ini nantinya akan di-mount melalui docker-compose.yml.
RUN mkdir -p /data/staging /data/output

# --- [7] EXECUTION LAYER ---
# Perintah utama saat kontainer dijalankan. 
# Menjalankan api.py untuk membuka jalur Ingestion Data via FastAPI/Flask.
CMD ["python", "api.py"]