from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import shutil
import os
import time
import sys

# =================================================================
# 🛠️ SYSTEM PATH CONFIGURATION
# =================================================================
# Mendaftarkan directory utama ke sys.path agar Python bisa mengenali 
# modul-modul di dalam folder 'scripts' tanpa error "ModuleNotFound".
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.append(CURRENT_DIR)

from scripts.extractor import process_metadata

# --- [INIT] FASTAPI APP ---
app = FastAPI()

# =================================================================
# 🛡️ CORS MIDDLEWARE SETUP
# =================================================================
# Mengizinkan akses dari domain mana pun (Wildcard). 
# Penting agar Frontend Dashboard (Streamlit/Next.js) bisa fetch data tanpa isu CORS.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_methods=["*"],
    allow_headers=["*"],
)

# Konfigurasi folder penampungan PDF sementara (Staging)
STAGING_PATH = os.getenv("STAGING_PATH", os.path.join("data", "staging"))

# =================================================================
# 🚀 ENDPOINT: VERIFY DOCUMENT
# =================================================================
# Endpoint utama untuk mengunggah PDF, mengekstrak metadata TTE,
# dan mengembalikan hasil analisis dalam format JSON standar.
@app.post("/verify")
async def verify_document(file: UploadFile = File(...)):
    try:
        # --- 1. FILE INGESTION (Staging Phase) ---
        # Memastikan directory staging ada, lalu menyimpan file upload secara fisik.
        os.makedirs(STAGING_PATH, exist_ok=True)
        file_path = os.path.join(STAGING_PATH, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # --- 2. FORENSIC EXTRACTION ---
        # Memanggil modul extractor untuk membedah sertifikat digital di dalam PDF.
        # Output yang diharapkan: List of dictionaries berisi detail penandatangan.
        result = process_metadata(file_path)
        current_ts = int(time.time() * 1000)

        # --- 3. STANDARDIZED RESPONSE HANDLING ---
        # Mengikuti struktur response yang konsisten untuk memudahkan integrasi FE/BE.
        if result.get("status") == "success":
            return {
                "code": 200,
                "timestamp": current_ts,
                "message": "Success",
                "reason": "",
                "data": result.get("data", []), # List detail Signer (C1, C2 metadata)
                "success": True
            }
        else:
            return {
                "code": 500,
                "timestamp": current_ts,
                "message": "Failed",
                "reason": result.get("message", "Unknown error occurred"),
                "data": [],
                "success": False
            }

    except Exception as e:
        # Catch-all error handling untuk mencegah server crash total
        return {
            "code": 500,
            "timestamp": int(time.time() * 1000),
            "message": "Failed",
            "reason": str(e),
            "data": [],
            "success": False
        }

# --- [EXECUTION] ---
# Menjalankan server Uvicorn pada host 0.0.0.0 agar bisa diakses di dalam Container Docker.
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)