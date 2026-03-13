# Pake base image Python yang ringan
FROM python:3.11-slim

# Set working directory di dalem kontainer
WORKDIR /app

# Install dependency sistem buat SQLite (biar makin stabil)
RUN apt-get update && apt-get install -y sqlite3 && rm -rf /var/lib/apt/lists/*

# Copy file requirements dulu biar build-nya cepet (Caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy semua script kodingan lo ke dalem kontainer
COPY . .

# Bikin folder buat mount volume (Tempat naruh PDF & DB)
RUN mkdir -p /data/staging /data/output

# Jalankan script watcher (atau extractor) pas kontainer nyala
CMD ["python", "api.py"]