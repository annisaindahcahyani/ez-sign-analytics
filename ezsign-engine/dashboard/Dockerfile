# 1. Pake kasta Python yang ringan biar gak obesitas
FROM python:3.11-slim

# 2. Set working directory di dalem container
WORKDIR /app

# 3. Install dependencies sistem yang MINIMAL (Hapus yang bikin error!)
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 4. Copy requirements khusus buat Dashboard (Daftar belanjaan lo tadi)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy semua kodingan dashboard (app.py dll) ke container
COPY . .

# 6. Buka pintu (port) kasta Streamlit
EXPOSE 8501

# 7. Perintah sakti buat nyalain Streamlit
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]