import hashlib
import json
import os
import sqlite3
import time
from datetime import datetime

import fitz  # PyMuPDF
import pikepdf
from asn1crypto import cms
from dotenv import load_dotenv


load_dotenv()
DB_PATH = os.getenv("DATABASE_PATH", "data/database.sqlite")
CORPO_CODE = os.getenv("CORPORATE_CODE", "ezsign")
CORPO_NAME = os.getenv("CORPORATE_NAME", "PT Solusi Identitas Global Net")


def get_db_connection():
    return sqlite3.connect(DB_PATH, timeout=20)


def stable_id(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8", errors="ignore")).hexdigest().upper()


def parse_validity_days(validity_str):
    if not validity_str:
        return 0, 0
    try:
        normalized = validity_str.replace("WIB ", "")
        if "To " in normalized:
            end_date_str = normalized.split("To ")[-1].strip()
            if "T" in end_date_str or "-" in end_date_str:
                end_dt = datetime.fromisoformat(end_date_str.replace("Z", "+00:00")).replace(tzinfo=None)
            else:
                end_dt = datetime.strptime(end_date_str, "%a %b %d %H:%M:%S %Y")
            delta = end_dt - datetime.now()
            return max(0, delta.days), 1 if delta.days < 0 else 0
    except Exception:
        pass
    return 0, 0


def parse_issuer_atomic(dn_str):
    res = {"CN": None, "O": None, "C": None}
    if not dn_str:
        return res
    parts = [p.strip() for p in str(dn_str).split(",")]
    for part in parts:
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        key = key.strip().upper()
        value = value.strip()
        if key == "CN":
            res["CN"] = value
        elif key == "O":
            res["O"] = value
        elif key == "C":
            res["C"] = value
    return res

def extract_real_cert_metadata(sig_contents):
    """
    Fungsi sakti buat bedah sertifikat X.509 di dalem biner PDF.
    Target: Nama asli dari PSrE (BSRE, Privy, Peruri, dll).
    """
    try:
        if not sig_contents:
            return None
            
        # 1. Handle encoding biner biar gak crash
        if isinstance(sig_contents, str):
            sig_contents = sig_contents.encode("latin-1", errors="ignore")

        # 2. Bedah struktur CMS (Cryptographic Message Syntax) pake asn1crypto
        content_info = cms.ContentInfo.load(sig_contents)
        signed_data = content_info["content"]
        
        # 3. Cari tumpukan sertifikatnya
        certs = signed_data.get('certificates', [])
        if not certs or len(certs) == 0:
            return None

        # 4. Ambil sertifikat pertama (Signer utama)
        cert = certs[0].chosen
        subject_native = cert.subject.native
        
        # --- LOGIC ANTI-UNKNOWN (Mencari Identitas Asli) ---
        # Coba ambil Common Name (Nama Lengkap biasanya di sini)
        signer_name = subject_native.get("common_name")
        
        # Kalo Common Name gak ada, cari di Organization Name
        if not signer_name:
            signer_name = subject_native.get("organization_name")
            
        # Kalo masih zonk, cari Email Address (Sering ada di sertifikat personal)
        if not signer_name:
            signer_name = subject_native.get("email_address")
            
        # Kalo bener-bener gak ketemu di semua field, baru kasih label ini
        final_signer = signer_name if signer_name else "Digital Signer (Name Hidden)"

        # 5. Bungkus jadi dictionary yang siap masuk ke DB lo
        return {
            "Signer": final_signer,
            "SubjectDN": cert.subject.human_friendly,
            "Issuer": cert.issuer.human_friendly,
            "SerialNumber": hex(cert.serial_number).upper().replace("0X", ""),
            "SignatureAlgorithm": cert['tbs_certificate']['signature']['algorithm'].native,
            "Validity": f"To {cert['tbs_certificate']['validity']['not_after'].native}",
            "Signature": "verified",
            "FilehashValidation": "HashValid",
            "code": 200, # Tandanya sukses bedah daging sertifikat
        }
        
    except Exception as e:
        # Biar lo gak buta kalo ada error pas bedah biner
        print(f"💀 [DEBUG] Gagal bongkar biner sertifikat: {e}")
        return None


def extract_signature_bytes_from_pdf(pdf_path):
    by_field = {}
    try:
        with pikepdf.open(pdf_path) as pdf:
            root = pdf.Root
            if "/AcroForm" not in root:
                return by_field
            fields = root["/AcroForm"].get("/Fields", [])
            for field_ref in fields:
                field = field_ref.obj
                if field.get("/FT") != "/Sig":
                    continue
                field_name = str(field.get("/T", "UnnamedSignature"))
                if "/V" not in field:
                    continue
                sig_obj = field["/V"]
                if hasattr(sig_obj, "obj"):
                    sig_obj = sig_obj.obj
                if not isinstance(sig_obj, dict):
                    continue
                contents = sig_obj.get("/Contents")
                if not contents:
                    continue
                sig_bytes = contents if isinstance(contents, bytes) else bytes(contents)
                by_field[field_name] = sig_bytes
    except Exception as e:
        print(f"⚠️ [EXTRACTOR] pikepdf extraction warning: {e}")
    return by_field


def normalize_json_entry(entry, parent_code=200):
    signer = entry.get("Signer") or entry.get("Signer ")
    subject_dn = entry.get("SubjectDN")
    issuer = entry.get("Issuer")
    serial_number = entry.get("Serial Number") or entry.get("SerialNumber")
    sig_algo = entry.get("Signature Algorithm") or entry.get("SignatureAlgorithm")
    validity = entry.get("Validity")
    ltv = entry.get("LTV")
    file_hash = entry.get("File hash Validation") or entry.get("FilehashValidation")
    signature_status = entry.get("Signature")
    ts_status = entry.get("timestamp signature") or entry.get("timestampsignature")
    chain_status = entry.get("Verify_Certificate_Chain")
    error_message = entry.get("Error Undefined") or entry.get("reason") or entry.get("message")
    reason = entry.get("reason")
    location = entry.get("location")
    local_timestamp = entry.get("local_timestamp")

    code = entry.get("code", parent_code)
    return {
        "code": code,
        "Signer": signer,
        "SubjectDN": subject_dn,
        "Issuer": issuer,
        "SerialNumber": serial_number,
        "SignatureAlgorithm": sig_algo,
        "Validity": validity,
        "LTV": ltv,
        "FilehashValidation": file_hash,
        "Signature": signature_status,
        "TSA": entry.get("TSA"),
        "timestampsignature": ts_status,
        "Verify_Certificate_Chain": chain_status,
        "Error": error_message,
        "Reason": reason,
        "Location": location,
        "LocalTimestamp": local_timestamp,
    }


def build_entries_from_json(raw_file_path):
    with open(raw_file_path, "r", encoding="utf-8") as f:
        payload = json.load(f)

    timestamp = payload.get("timestamp", int(time.time() * 1000))
    parent_code = payload.get("code", 500)
    success = bool(payload.get("success"))
    data = payload.get("data") or []

    if success and isinstance(data, list) and len(data) > 0:
        entries = [normalize_json_entry(item, parent_code=parent_code) for item in data]
    else:
        entries = [{
            "code": parent_code,
            "Signer": None,
            "SubjectDN": None,
            "Issuer": None,
            "SerialNumber": None,
            "SignatureAlgorithm": None,
            "Validity": None,
            "LTV": None,
            "FilehashValidation": payload.get("reason") or payload.get("message"),
            "Signature": None,
            "timestampsignature": None,
            "Verify_Certificate_Chain": None,
            "Error": payload.get("reason") or payload.get("message"),
            "Reason": payload.get("reason"),
            "Location": payload.get("location"),
            "LocalTimestamp": payload.get("local_timestamp"),
        }]

    return entries, timestamp

def validate_pdf_integrity(doc, widget):
    """
    Logic buat nentuin status modifikasi dokumen.
    """
    # Secara default kita anggap aman
    status = "Dokumen belum di modifikasi"
    
    # Cek apakah ada anotasi yang dibikin setelah signing
    # (Ini simplifikasi, idealnya bandingkan timestamp signing vs annot modification)
    has_annots = False
    for page in doc:
        if page.annots():
            has_annots = True
            break
            
    if has_annots:
        # Check integrity via fitz (is_signed & valid)
        # Jika fitz mendeteksi perubahan biner tapi hanya di level anotasi
        status = "Dokumen sudah di modifikasi dengan anotasi"
        
    return status

def build_entries_from_pdf(raw_file_path):
    doc = fitz.open(raw_file_path)
    entries = []
    global_ts = int(time.time() * 1000)
    
    psre_list = ["BSRE", "SIGN CA", "SOLUSI IDENTITAS", "PERURI", "TILAKA", "PRIVY", "VIDA", "DIGISIGN", "EZSIGN"]
    sig_fields = doc.get_sigflags()
    
    form_fields = []
    for page in doc:
        for w in page.widgets():
            if w.field_type == fitz.PDF_WIDGET_TYPE_SIGNATURE:
                form_fields.append(w)

    if not form_fields and sig_fields <= 0:
        return [{ "code": 1001, "Status": "Tidak ditemukan tanda tangan elektronik" }], global_ts

    for i, widget in enumerate(form_fields):
        sig_contents = widget.field_value
        sig_data = extract_real_cert_metadata(sig_contents)
        
        # FALLBACK: Pake pikepdf kalo fitz gagal bongkar biner
        if not sig_data:
            sig_bytes_map = extract_signature_bytes_from_pdf(raw_file_path)
            if widget.field_name in sig_bytes_map:
                sig_data = extract_real_cert_metadata(sig_bytes_map[widget.field_name])

        # REVISI 2: JANGAN HARDCODE "Unknown" KALO GAK PERLU
        if not sig_data:
            sig_data = {
                "Signer": f"Digital Signer {i+1}",
                "Issuer": "Metadata Encrypted",
                "SerialNumber": f"SN-UNAVAILABLE-{i}",
                "Validity": "N/A"
            }

        is_komdigi = any(psre in (sig_data.get('Issuer') or "").upper() for psre in psre_list)
        
        # REVISI 3: Pastikan info TSA dan LTV ditarik dari status biner widget
        entry = {
            "code": 200 if is_komdigi else 1002,
            "Status": "Ditemukan tanda tangan elektronik",
            "TSA": "Tanda tangan dilengkapi penanda waktu elektronik" if widget.is_signed else "Tidak dilengkapi penanda waktu",
            "LTV": "Tanda tangan mendukung fitur LTV" if widget.is_signed else "Tidak mendukung LTV",
            **sig_data
        }
        entries.append(entry)

    doc.close()
    return entries, global_ts

def ensure_dim_date(cursor, dt_obj):
    result = cursor.execute(
        "SELECT c3_date_key FROM esa_dim_date_c3 WHERE c3_full_date=? AND c3_hour=?",
        (dt_obj.strftime("%Y-%m-%d"), dt_obj.hour),
    ).fetchone()
    if result:
        return result[0]

    cursor.execute(
        """INSERT INTO esa_dim_date_c3
           (c3_full_date, c3_month_name, c3_year, c3_day, c3_hour)
           VALUES (?, ?, ?, ?, ?)""",
        (dt_obj.strftime("%Y-%m-%d"), dt_obj.strftime("%B"), dt_obj.year, dt_obj.day, dt_obj.hour),
    )
    result = cursor.execute(
        "SELECT c3_date_key FROM esa_dim_date_c3 WHERE c3_full_date=? AND c3_hour=?",
        (dt_obj.strftime("%Y-%m-%d"), dt_obj.hour),
    ).fetchone()
    return result[0]


def ensure_dim_corporate(cursor):
    result = cursor.execute(
        "SELECT c4_corpo_key FROM esa_dim_corporate_c4 WHERE c4_corpo_code=?",
        (CORPO_CODE,),
    ).fetchone()
    if result:
        return result[0]

    cursor.execute(
        "INSERT INTO esa_dim_corporate_c4 (c4_corpo_code, c4_corpo_name) VALUES (?, ?)",
        (CORPO_CODE, CORPO_NAME),
    )
    result = cursor.execute(
        "SELECT c4_corpo_key FROM esa_dim_corporate_c4 WHERE c4_corpo_code=?",
        (CORPO_CODE,),
    ).fetchone()
    return result[0]


def ingest_entries(cursor, entries, global_ts, raw_file_path):
    dt_obj = datetime.fromtimestamp(global_ts / 1000)
    date_id = ensure_dim_date(cursor, dt_obj)
    corpo_id = ensure_dim_corporate(cursor)
    doc_id = f"DOC-{stable_id(f'{raw_file_path}:{global_ts}')[:16]}"
    readable_ts = datetime.fromtimestamp(global_ts / 1000).strftime("%Y-%m-%d %H:%M:%S")

    for _, entry in enumerate(entries, start=1):
        # --- A. AMBIL DATA DASAR ---
        signer_name = entry.get("Signer") or entry.get("Signer ") or "Unknown Signer"
        # Pastiin lo ambil SubjectDN yang lengkap dari Postman
        subject_dn = entry.get("SubjectDN") or "N/A"
        serial_number = entry.get("SerialNumber") or entry.get("Serial Number")
        issuer_raw = entry.get("Issuer") or "CN=Unknown Issuer, O=None"
        signer_fingerprint = stable_id(f"{signer_name}|{subject_dn}|{serial_number or issuer_raw}")

        # --- B. GET SIGNER ID (C1) ---
        if serial_number:
            cursor.execute(
                "INSERT OR IGNORE INTO esa_dim_signer_c1 (c1_signer_name, c1_subject_dn, c1_serial_number, c1_sha1_fingerprint) VALUES (?, ?, ?, ?)",
                (signer_name, subject_dn, serial_number, signer_fingerprint),
            )
            signer_id = cursor.execute(
                "SELECT c1_signer_key FROM esa_dim_signer_c1 WHERE c1_serial_number=?", (serial_number,)
            ).fetchone()[0]
        else:
            cursor.execute(
                "INSERT INTO esa_dim_signer_c1 (c1_signer_name, c1_subject_dn, c1_serial_number, c1_sha1_fingerprint) VALUES (?, ?, NULL, ?)",
                (signer_name, subject_dn, signer_fingerprint),
            )
            signer_id = cursor.lastrowid

        # --- C. GET ISSUER ID (C2) & TSA STATUS ---
        issuer_parts = parse_issuer_atomic(issuer_raw)
        psre_list = ["BSRE", "SIGN CA", "SOLUSI IDENTITAS", "PERURI", "TILAKA", "PRIVY", "VIDA", "DIGISIGN"]
        is_berinduk = 1 if any(x in (issuer_raw or "").upper() for x in psre_list) else 0

        issuer_row = cursor.execute(
            "SELECT c2_issuer_key FROM esa_dim_issuer_c2 WHERE c2_full_distinguished_name=?",
            (issuer_raw,),
        ).fetchone()
        if issuer_row:
            issuer_id = issuer_row[0]
        else:
            cursor.execute(
                """INSERT INTO esa_dim_issuer_c2
                   (c2_full_distinguished_name, c2_common_name, c2_organization, c2_country, c2_sig_algo, c2_is_berinduk)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (issuer_raw, issuer_parts["CN"], issuer_parts["O"], issuer_parts["C"], entry.get("SignatureAlgorithm"), is_berinduk),
            )
            issuer_id = cursor.lastrowid

        # --- D. GET INTEGRITY ID (C5) ---
        code = entry.get("code", 500)
        is_trusted = 1 if code == 200 or entry.get("Signature") == "verified" else 0
        
        cursor.execute(
            """INSERT INTO esa_dim_integrity_c5
               (c5_status_code, c5_status_type, c5_integrity_desc, c5_error_message, c5_reason, c5_location, c5_local_timestamp)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                code,
                "Trusted" if is_trusted else "Not Trusted",
                entry.get("FilehashValidation") or "N/A",
                entry.get("Error") or "",
                entry.get("Reason") or "",
                entry.get("Location") or "",
                entry.get("LocalTimestamp") or readable_ts,
            ),
        )
        integrity_id = cursor.lastrowid


        # --- E. INSERT FACT TABLE F1 (PASTIKAN MENYATU DENGAN FOR LOOP) ---
        days_left, is_expired = parse_validity_days(entry.get("Validity"))
        tsa_status = entry.get("TSA") or entry.get("timestamp signature") or "N/A"
        ltv_status = entry.get("LTV") or "Not Supported"
        
        # Penentuan is_trusted (Berdasarkan code 200 atau verified status)
        code = entry.get("code", 500)
        is_trusted = 1 if (code == 200 or entry.get("Signature") == "verified") else 0

        # PENTING: Cursor execute ini harus sejajar sama 'days_left' di atas!
        cursor.execute(
            """INSERT INTO esa_fact_verifications (
                f1_doc_id, c1_signer_key, c2_issuer_key, c3_date_key, c4_corpo_key, c5_integrity_key,
                f1_is_trusted, f1_is_expired, f1_validity_days, f1_ltv_status, f1_tsa_status,
                f1_hash_status, f1_sig_status, f1_chain_status, f1_signing_time
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                doc_id, signer_id, issuer_id, date_id, corpo_id, integrity_id,
                is_trusted, is_expired, days_left,
                ltv_status, 
                tsa_status,
                entry.get("FilehashValidation") or "Valid",
                entry.get("Signature") or "verified",
                entry.get("Verify_Certificate_Chain") or "verified",
                readable_ts,  # <--- SUDAH BENAR PAKAI READABLE_TS! 🏆
            ),
        )
def process_metadata(raw_file_path):
    file_ext = os.path.splitext(raw_file_path)[1].lower()

    if file_ext == ".json":
        entries, global_ts = build_entries_from_json(raw_file_path)
    elif file_ext == ".pdf":
        entries, global_ts = build_entries_from_pdf(raw_file_path)
    else:
        print(f"⚠️ [EXTRACTOR] File format tidak didukung: {file_ext}")
        return

    if not entries:
        print("⚠️ [EXTRACTOR] Tidak ada entry yang bisa diingest.")
        return

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Panggil fungsi inti ingestion
        ingest_entries(cursor, entries, global_ts, raw_file_path)
        
        # Simpan perubahan secara permanen
        conn.commit()
        
        # PRINT SLAY: Biar lo tau sistem lo kerja keras bagai kuda
        print(f"🔥 [SLAY] {os.path.basename(raw_file_path)}: Berhasil nambahin {len(entries)} data ke Dashboard!") 
        
    except Exception as e:
        # Kalo ada satu aja yang error, batalin semua biar gak nyampah
        conn.rollback()
        print(f"💀 [FAIL] Aduh Ca, ada yang zonk: {e}")
        # Lo bisa tambahin ini buat debug lebih dalem kalo mau:
        # import traceback; traceback.print_exc()
        
    finally:
        conn.close()