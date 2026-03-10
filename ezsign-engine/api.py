from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import shutil
import os
import time
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.append(CURRENT_DIR)

from scripts.extractor import process_metadata

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_methods=["*"],
    allow_headers=["*"],
)

STAGING_PATH = os.getenv("STAGING_PATH", os.path.join("data", "staging"))

@app.post("/verify")
async def verify_document(file: UploadFile = File(...)):
    try:
        # 1. Simpan File (Standard Staging)
        os.makedirs(STAGING_PATH, exist_ok=True)
        file_path = os.path.join(STAGING_PATH, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # 2. Panggil Extractor (Output: list of dictionaries)
        result = process_metadata(file_path)
        current_ts = int(time.time() * 1000)

        # 3. Logic Response Handling
        if result.get("status") == "success":
            return {
                "code": 200,
                "timestamp": current_ts,
                "message": "Success",
                "reason": "",
                "data": result.get("data", []), # INI HARUS LIST ISI DETAIL SIGNER
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
        return {
            "code": 500,
            "timestamp": int(time.time() * 1000),
            "message": "Failed",
            "reason": str(e),
            "data": [],
            "success": False
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)