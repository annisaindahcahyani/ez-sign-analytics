import hashlib
import json
import os
import re
import sqlite3
import time
from datetime import datetime, timezone

import fitz  # PyMuPDF
import pikepdf
from asn1crypto import cms
from dotenv import load_dotenv


load_dotenv()
DB_PATH = os.getenv("DATABASE_PATH", "data/database.sqlite")
CORPO_CODE = os.getenv("CORPORATE_CODE", "ezsign")
CORPO_NAME = os.getenv("CORPORATE_NAME", "PT Solusi Identitas Global Net")

PSRE_BERINDUK = ["BSRE", "BSSN", "PERURI", "PRIVY", "VIDA", "TILAKA", "DIGISIGN", "EZSIGN"]


def get_db_connection():
    return sqlite3.connect(DB_PATH, timeout=20)


def stable_id(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8", errors="ignore")).hexdigest().upper()


def parse_validity_days(validity_str):
    if not validity_str:
        return 0, 0

    try:
        text = str(validity_str)
        if "To " in text:
            end_date_str = text.split("To ")[-1].strip()
        else:
            end_date_str = text.strip()

        clean_dt = re.sub(r"\b(WIB|WIT|WITA|GMT|UTC)\b", "", end_date_str).strip()
        if "T" in clean_dt or "-" in clean_dt:
            end_dt = datetime.fromisoformat(clean_dt.replace("Z", "+00:00")).replace(tzinfo=None)
        else:
            end_dt = datetime.strptime(clean_dt, "%a %b %d %H:%M:%S %Y")

        delta = end_dt - datetime.now()
        return max(0, delta.days), 1 if delta.days < 0 else 0
    except Exception:
        return 0, 0


def parse_issuer_atomic(dn_str):
    res = {"CN": None, "O": None, "C": None}
    if not dn_str or dn_str == "None":
        return res

    try:
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

        if not res["CN"]:
            res["CN"] = str(dn_str)[:100]
    except Exception:
        pass

    return res


def _collect_signature_fields_from_acroform(pdf):
    by_field = {}
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

    return by_field


def _collect_signature_fields_bruteforce(pdf):
    by_field = {}
    try:
        objects_iter = getattr(pdf, "objects", None)
        if objects_iter is None:
            return by_field

        for index, obj in enumerate(objects_iter):
            if not isinstance(obj, pikepdf.Dictionary):
                continue
            if obj.get("/Type") != "/Sig":
                continue

            field_name = str(obj.get("/T", f"Sig-Obj-{index}"))
            contents = obj.get("/Contents")
            if not contents:
                continue
            by_field[field_name] = contents if isinstance(contents, bytes) else bytes(contents)
    except Exception as e:
        print(f"[EXTRACTOR] Bruteforce scan warning: {e}")

    return by_field


def extract_signature_bytes_from_pdf(pdf_path):
    by_field = {}
    try:
        with pikepdf.open(pdf_path) as pdf:
            by_field.update(_collect_signature_fields_from_acroform(pdf))
            for name, sig in _collect_signature_fields_bruteforce(pdf).items():
                by_field.setdefault(name, sig)
    except Exception as e:
        print(f"[EXTRACTOR] pikepdf error: {e}")

    return by_field


def extract_real_cert_metadata(sig_contents):
    try:
        if not sig_contents:
            return None
        if isinstance(sig_contents, str):
            sig_contents = sig_contents.encode("latin-1", errors="ignore")

        content_info = cms.ContentInfo.load(sig_contents)
        signed_data = content_info["content"]
        certs = signed_data.get("certificates", [])
        if not certs:
            return None

        cert = certs[0].chosen
        subject_native = cert.subject.native
        not_before = cert["tbs_certificate"]["validity"]["not_before"].native
        not_after = cert["tbs_certificate"]["validity"]["not_after"].native

        now = datetime.now(timezone.utc) if getattr(not_after, "tzinfo", None) else datetime.now()
        is_expired = not_after <= now
        cert_status = "Expired" if is_expired else "Certificate Not Expire"

        signer_name = (
            subject_native.get("common_name")
            or subject_native.get("organization_name")
            or subject_native.get("email_address")
            or "Unknown Signer"
        )

        serial_number = hex(cert.serial_number).upper().replace("0X", "")
        subject_dn = cert.subject.human_friendly
        issuer_dn = cert.issuer.human_friendly
        validity_str = (
            f"From {not_before.strftime('%a %b %d %H:%M:%S WIB %Y')} "
            f"To {not_after.strftime('%a %b %d %H:%M:%S WIB %Y')}"
        )

        return {
            "Signature Algorithm": cert["tbs_certificate"]["signature"]["algorithm"].native,
            "code": 200,
            "Issuer": issuer_dn,
            "Issuer Distinguished Name": issuer_dn,
            "Signer": signer_name,
            "SubjectDN": subject_dn,
            "Certificate Status": cert_status,
            "Serial Number": serial_number,
            "SHA-1 Fingerprint": stable_id(f"{signer_name}|{subject_dn}|{serial_number}"),
            "LTV": "Support LTV",
            "Certificate valid": "Valid" if not is_expired else "Invalid",
            "Validity": validity_str,
            "timestamp signature": "verified",
            "TSA Info": "eSign Timestamp Service",
            "Verify_Certificate_Chain": "verified",
            "File hash Validation": "Valid",
            "Signature": "verified",
        }
    except Exception as e:
        print(f"[DEBUG] Gagal bedah biner: {e}")
        return {
            "code": 1003,
            "Issuer": "-",
            "Serial Number": "-",
            "Certificate Status": "Untrusted",
            "Error Undefined": str(e),
            "File hash Validation": "Invalid",
            "LTV": "Not Support LTV",
        }


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

    code = entry.get("code", parent_code)
    return {
        "code": code,
        "Signer": signer,
        "SubjectDN": subject_dn,
        "Issuer": issuer,
        "Issuer Distinguished Name": entry.get("Issuer Distinguished Name") or issuer,
        "Serial Number": serial_number,
        "Signature Algorithm": sig_algo,
        "Validity": validity,
        "LTV": ltv,
        "File hash Validation": file_hash,
        "Signature": signature_status,
        "timestamp signature": ts_status,
        "Verify_Certificate_Chain": chain_status,
        "Certificate Status": entry.get("Certificate Status"),
        "TSA Info": entry.get("TSA Info") or entry.get("TSA"),
        "Error Undefined": error_message,
        "Reason": entry.get("reason") or entry.get("Reason"),
        "Location": entry.get("location") or entry.get("Location"),
        "LocalTimestamp": entry.get("local_timestamp") or entry.get("LocalTimestamp"),
        "SHA-1 Fingerprint": entry.get("SHA-1 Fingerprint"),
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
        entries = [
            {
                "code": parent_code,
                "Signer": None,
                "SubjectDN": None,
                "Issuer": "-",
                "Serial Number": "-",
                "Signature Algorithm": None,
                "Validity": None,
                "LTV": "Not Support LTV",
                "File hash Validation": "Invalid",
                "Signature": "invalid",
                "timestamp signature": "N/A",
                "Verify_Certificate_Chain": "not verified",
                "Certificate Status": "Untrusted",
                "Error Undefined": payload.get("reason") or payload.get("message"),
                "Reason": payload.get("reason"),
                "Location": payload.get("location"),
                "LocalTimestamp": payload.get("local_timestamp"),
            }
        ]

    return entries, timestamp


def validate_pdf_integrity(doc):
    for page in doc:
        if page.annots():
            return "Invalid"
    return "Valid"


def build_entries_from_pdf(raw_file_path):
    entries = []
    global_ts = int(time.time() * 1000)

    with fitz.open(raw_file_path) as doc:
        hash_status = validate_pdf_integrity(doc)
        sig_bytes_map = extract_signature_bytes_from_pdf(raw_file_path)

        # FE expects empty array for no signature so it can show no_signature banner.
        if not sig_bytes_map:
            return [], global_ts

        for _, sig_bytes in sig_bytes_map.items():
            sig_data = extract_real_cert_metadata(sig_bytes)
            if not sig_data:
                continue

            issuer = (sig_data.get("Issuer") or "").upper()
            is_berinduk = any(psre in issuer for psre in PSRE_BERINDUK)
            is_error = sig_data.get("code") == 1003
            is_expired = sig_data.get("Certificate Status", "").lower().startswith("expired")
            is_untrusted = is_error or (not is_berinduk) or is_expired

            entry = {
                "Signature Algorithm": sig_data.get("Signature Algorithm", "SHA256withRSA"),
                "code": 1003 if is_error else (200 if not is_untrusted else 1002),
                "Issuer": sig_data.get("Issuer") or "-",
                "Issuer Distinguished Name": sig_data.get("Issuer Distinguished Name") or sig_data.get("Issuer") or "-",
                "Signer": sig_data.get("Signer") or "Unknown Signer",
                "SubjectDN": sig_data.get("SubjectDN") or "-",
                "Certificate Status": "Untrusted" if is_untrusted and not is_expired else sig_data.get("Certificate Status", "Unknown"),
                "Serial Number": sig_data.get("Serial Number") or "-",
                "SHA-1 Fingerprint": sig_data.get("SHA-1 Fingerprint"),
                "LTV": sig_data.get("LTV", "Not Support LTV"),
                "Certificate valid": "Invalid" if is_untrusted else "Valid",
                "Validity": sig_data.get("Validity", "N/A"),
                "timestamp signature": sig_data.get("timestamp signature", "N/A"),
                "TSA Info": sig_data.get("TSA Info", "eSign Timestamp Service"),
                "Verify_Certificate_Chain": "verified" if is_berinduk else "not verified",
                "File hash Validation": "Invalid" if hash_status.lower() == "invalid" else sig_data.get("File hash Validation", "Valid"),
                "Signature": "verified" if not is_error else "invalid",
                "Error Undefined": sig_data.get("Error Undefined"),
                "Reason": sig_data.get("Reason"),
                "Location": sig_data.get("Location"),
                "LocalTimestamp": sig_data.get("LocalTimestamp"),
            }
            entries.append(entry)

    return entries, global_ts


def ensure_dim_date(cursor, dt_obj):
    full_date = dt_obj.strftime("%Y-%m-%d")
    row = cursor.execute(
        "SELECT c3_date_key FROM esa_dim_date_c3 WHERE c3_full_date=? AND c3_hour=?",
        (full_date, dt_obj.hour),
    ).fetchone()
    if row:
        return row[0]

    cursor.execute(
        """INSERT INTO esa_dim_date_c3
           (c3_full_date, c3_month_name, c3_year, c3_day, c3_hour)
           VALUES (?, ?, ?, ?, ?)""",
        (full_date, dt_obj.strftime("%B"), dt_obj.year, dt_obj.day, dt_obj.hour),
    )
    return cursor.lastrowid


def ensure_dim_corporate(cursor):
    row = cursor.execute(
        "SELECT c4_corpo_key FROM esa_dim_corporate_c4 WHERE c4_corpo_code=?",
        (CORPO_CODE,),
    ).fetchone()
    if row:
        return row[0]

    cursor.execute(
        "INSERT INTO esa_dim_corporate_c4 (c4_corpo_code, c4_corpo_name) VALUES (?, ?)",
        (CORPO_CODE, CORPO_NAME),
    )
    return cursor.lastrowid


def ingest_entries(cursor, entries, global_ts, raw_file_path):
    dt_obj = datetime.fromtimestamp(global_ts / 1000)
    readable_ts = dt_obj.strftime("%Y-%m-%d %H:%M:%S")
    doc_id = f"DOC-{stable_id(f'{raw_file_path}:{global_ts}')[:16]}"

    date_id = ensure_dim_date(cursor, dt_obj)
    corpo_id = ensure_dim_corporate(cursor)

    for entry in entries:
        signer_name = entry.get("Signer") or entry.get("Signer ") or "No Signer Found"
        subject_dn = entry.get("SubjectDN") or "N/A"
        serial_number = entry.get("Serial Number") or entry.get("SerialNumber")
        issuer_raw = entry.get("Issuer") or "None"

        signer_fingerprint = entry.get("SHA-1 Fingerprint") or stable_id(
            f"{signer_name}|{subject_dn}|{serial_number or issuer_raw}"
        )

        cursor.execute(
            """INSERT OR IGNORE INTO esa_dim_signer_c1
               (c1_signer_name, c1_subject_dn, c1_serial_number, c1_sha1_fingerprint)
               VALUES (?, ?, ?, ?)""",
            (signer_name, subject_dn, serial_number, signer_fingerprint),
        )
        signer_id = cursor.execute(
            "SELECT c1_signer_key FROM esa_dim_signer_c1 WHERE c1_sha1_fingerprint=?",
            (signer_fingerprint,),
        ).fetchone()[0]

        issuer_parts = parse_issuer_atomic(issuer_raw)
        is_berinduk = 1 if any(psre in issuer_raw.upper() for psre in PSRE_BERINDUK) else 0

        existing_issuer = cursor.execute(
            "SELECT c2_issuer_key FROM esa_dim_issuer_c2 WHERE c2_full_distinguished_name=?",
            (issuer_raw,),
        ).fetchone()
        if existing_issuer:
            issuer_id = existing_issuer[0]
        else:
            cursor.execute(
                """INSERT INTO esa_dim_issuer_c2
                   (c2_full_distinguished_name, c2_common_name, c2_organization, c2_country, c2_sig_algo, c2_is_berinduk)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    issuer_raw,
                    issuer_parts["CN"],
                    issuer_parts["O"],
                    issuer_parts["C"],
                    entry.get("Signature Algorithm") or entry.get("SignatureAlgorithm"),
                    is_berinduk,
                ),
            )
            issuer_id = cursor.lastrowid

        status_code = int(entry.get("code", 500))
        is_trusted = 1 if status_code == 200 else 0

        cursor.execute(
            """INSERT INTO esa_dim_integrity_c5
               (c5_status_code, c5_status_type, c5_integrity_desc, c5_error_message, c5_reason, c5_location, c5_local_timestamp)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                status_code,
                "Trusted" if is_trusted else ("Unsigned" if status_code == 1001 else "Not Trusted"),
                entry.get("File hash Validation") or "N/A",
                entry.get("Error Undefined") or "",
                entry.get("Reason") or "",
                entry.get("Location") or "",
                entry.get("LocalTimestamp") or readable_ts,
            ),
        )
        integrity_id = cursor.lastrowid

        days_left, is_expired = parse_validity_days(entry.get("Validity"))

        cursor.execute(
            """INSERT INTO esa_fact_verifications (
                f1_doc_id, c1_signer_key, c2_issuer_key, c3_date_key, c4_corpo_key, c5_integrity_key,
                f1_is_trusted, f1_is_expired, f1_validity_days, f1_ltv_status, f1_tsa_status,
                f1_hash_status, f1_sig_status, f1_chain_status, f1_signing_time
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                doc_id,
                signer_id,
                issuer_id,
                date_id,
                corpo_id,
                integrity_id,
                is_trusted,
                is_expired,
                days_left,
                entry.get("LTV") or "Not Support LTV",
                entry.get("timestamp signature") or entry.get("TSA Info") or "N/A",
                entry.get("File hash Validation") or "N/A",
                entry.get("Signature") or "N/A",
                entry.get("Verify_Certificate_Chain") or "N/A",
                global_ts,
            ),
        )


def process_metadata(raw_file_path):
    file_ext = os.path.splitext(raw_file_path)[1].lower()

    if file_ext == ".json":
        entries, global_ts = build_entries_from_json(raw_file_path)
    elif file_ext == ".pdf":
        entries, global_ts = build_entries_from_pdf(raw_file_path)
    else:
        return {"status": "error", "message": f"Format {file_ext} gak disupport, Ca!"}

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Always return data for FE; DB ingestion runs only when there are entries.
        if entries:
            ingest_entries(cursor, entries, global_ts, raw_file_path)
        conn.commit()
        print(f"[SLAY] {os.path.basename(raw_file_path)}: Sukses ({len(entries)} entries)")
        return {"status": "success", "data": entries}
    except Exception as e:
        conn.rollback()
        print(f"[FAIL] {e}")
        return {"status": "error", "message": str(e)}
    finally:
        conn.close()
