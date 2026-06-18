# =============================================================================
# 🚀 MODULE: FASTAPI INGESTION GATEWAY (MICROSERVICE LAYER)
# =============================================================================
# 📌 CONFIGURATION : RESTful API Endpoint & Middleware Router
# 📅 UPDATE        : 5 Juni 2026
# 🛡️ OBJECTIVE     : Fasilitator Unggah Berkas & Orkestrasi Ekstraksi Forensik
# ⚙️ ARCHITECTURE  : Decoupled System (Pemisahan Frontend & Backend)
# =============================================================================
# 🗺️ DOKUMEN TATA KERJA FUNGSIONAL PENGEMBANG (FOR NEXT DEVELOPER):
#
# 1. ARSITEKTUR JARINGAN & MIDDLEWARE (CORS):
#    Berfungsi sebagai jembatan independen. Kebijakan Cross-Origin Resource 
#    Sharing (CORS) diatur menjadi Wildcard ('*') untuk memastikan antarmuka 
#    eksternal (seperti Next.js atau Streamlit) dapat melakukan pemanggilan
#    AJAX/Fetch tanpa terhalang restriksi Same-Origin Policy dari peramban.
#
# 2. STANDARDIZASI KONTRAK API (API CONTRACT):
#    Sistem mengadopsi standar respons JSON yang kaku (code, timestamp, message, 
#    reason, data, success). Hal ini mempermudah subsistem lain dalam melakukan 
#    parsing dan mencegah kegagalan aplikasi akibat perubahan struktur data.
#
# 3. PENANGANAN ANOMALI (FAULT TOLERANCE):
#    Dilengkapi dengan blok try-except global untuk menjamin agar server (Uvicorn)
#    tidak mengalami terminasi paksa (Crash) apabila terjadi kegagalan sistemik
#    saat proses pembedahan berkas biner PDF.
# =============================================================================

import os
import sys
import shutil
import time
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# =============================================================================
# 🛠️ SYSTEM PATH RESOLUTION CONFIGURATION
# =============================================================================
# Memuat konfigurasi environment variables global demi konsistensi arsitektur
load_dotenv()

# Menginjeksikan direktori tingkat root secara dinamis untuk mengamankan resolusi modul internal
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

# Melakukan fallback pencarian jika modul berada di hierarki monorepo tingkat atas
PARENT_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))
if PARENT_DIR not in sys.path:
    sys.path.append(PARENT_DIR)

try:
    # Memastikan pemetaan engine ekstraktor forensik TTE selaras tanpa ModuleNotFound Exception
    from scripts.extractor import process_metadata
except ModuleNotFoundError:
    from extractor import process_metadata

# --- [INISIALISASI INSTANS FASTAPI REST ENGINE] ---
app = FastAPI(
    title="EzSign Analytics Ingestion Gateway", 
    description="RESTful API Microservice Layer for Automated Cryptographic Forensic Extraction",
    version="2.0.0"
)

# =============================================================================
# 🛡️ CROSS-ORIGIN RESOURCE SHARING (CORS) MIDDLEWARE
# =============================================================================
# Implementasi kebijakan jaringan terbuka untuk memfasilitasi komunikasi 
# asinkron lintas domain pada arsitektur sistem yang terdekopel (Decoupled).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_methods=["*"],
    allow_headers=["*"],
)

# Penetapan direktori persisten alokasi penyimpanan sementara (Staging Area) dari file .env
STAGING_PATH = os.getenv("STAGING_PATH", os.path.join(BASE_DIR, "data", "staging"))

# =============================================================================
# 🚀 ENDPOINT OPERASIONAL: DOCUMENT VERIFICATION (/verify)
# =============================================================================
@app.post("/verify")
async def verify_document(file: UploadFile = File(...)):
    """
    Titik akses utama (Primary Endpoint) klien untuk menginisiasi pengiriman dokumen, 
    penulisan ke media penyimpanan, serta pendelegasian ekstraksi metadata.
    """
    current_ts = int(time.time() * 1000)
    
    # Validasi Dasar: Mencegah pengiriman muatan payload kosong atau tanpa nama berkas
    if not file.filename:
        raise HTTPException(status_code=400, detail="Invalid payload: File name is missing.")
        
    # Memastikan standarisasi pathing absolut adaptif di lingkungan Docker container
    actual_staging_path = STAGING_PATH
    os.makedirs(actual_staging_path, exist_ok=True)
    file_path = os.path.join(actual_staging_path, file.filename)
    
    try:
        # --- [FASE 1: FILE INGESTION WITH DESCRIPTOR PROTECTION] ---
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # --- [FASE 2: FORENSIC EXTRACTION DELEGATION] ---
        # Memicu engine extractor untuk membedah muatan biner ASN.1 sertifikat secara terisolasi
        result = process_metadata(file_path)

        # --- [FASE 3: STANDARDIZED API RESPONSE CONTRACT] ---
        if isinstance(result, dict) and result.get("status") != "error":
            # Ekstraksi muatan data internal dari hasil komit repositori warehouse
            extracted_data = result.get("data", []) if "data" in result else [result]
            return {
                "code": 200,
                "timestamp": int(time.time() * 1000),
                "message": "Success",
                "reason": "",
                "data": extracted_data,
                "success": True
            }
        else:
            return {
                "code": 500,
                "timestamp": int(time.time() * 1000),
                "message": "Failed",
                "reason": result.get("message") if isinstance(result, dict) else "Terjadi kegagalan ekstraksi manifes biner sertifikat.",
                "data": [],
                "success": False
            }

    except Exception as e:
        # --- [FASE 4: CATCH-ALL FAULT TOLERANCE CONTROL] ---
        return {
            "code": 500,
            "timestamp": int(time.time() * 1000),
            "message": "Failed",
            "reason": f"System Microservice Exception: {str(e)}",
            "data": [],
            "success": False
        }
    finally:
        # --- [FASE 5: GARBAGE COLLECTION & STORAGE FLUSH] ---
        # Memaksa penutupan penunjuk file (Stream Pointer) untuk mengeliminasi resiko Memory Leak di Docker
        await file.close()

# =============================================================================
# ⚡ DAEMON EXECUTION LAYER
# =============================================================================
if __name__ == "__main__":
    import uvicorn
    # Mengikat port internal kontainer pada port 8000 secara asinkron
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=False)