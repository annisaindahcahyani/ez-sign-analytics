# Pake base image Python yang ringan
FROM python:3.11-slim

# Set working directory di dalem kontainer
WORKDIR /app

# Install dependency sistem (build-essential buat library pandas/numpy)
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# --- INI TRIKNYA CA ---
# Kita asumsikan requirements.txt bakal dikirim dari folder utama
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy semua script dashboard lo
COPY . .

# Dashboard jalan di port 8501
EXPOSE 8501

# Jalankan Streamlit
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]