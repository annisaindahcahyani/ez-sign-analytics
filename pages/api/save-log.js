/**
 * =============================================================================
 * 🔄 MODULE: API INGESTION GATEWAY (STAR SCHEMA PERSISTENCE LAYER)
 * =============================================================================
 * 📌 CONFIGURATION : Next.js API Route for SQLite Persistence
 * 📅 UPDATE        : 5 Juni 2026
 * 🛡️ OBJECTIVE     : Ingesti Metadata TTE ke dalam Arsitektur Star Schema
 * =============================================================================
  * 🗺️ DOKUMEN TATA KERJA FUNGSIONAL PENGEMBANG (FOR NEXT DEVELOPER):
 *
 * 1. HYBRID DATA INGESTION:
 * Fungsi ini bertindak sebagai jembatan antara API Frontend Next.js dengan 
 * basis data SQLite (Persistence Layer). Mengonversi payload JSON verifikasi 
 * menjadi baris rekaman pada tabel Dimensi (C1-C5) dan tabel Fakta (F1).
 *
 * 2. REAL-TIME WIB TIME SYNC:
 * Mengimplementasikan 'Intl.DateTimeFormat' untuk memastikan sinkronisasi 
 * stempel waktu (Timestamp) ke zona waktu Asia/Jakarta (WIB) secara presisi, 
 * menghindari anomali UTC offset yang sering terjadi pada environment Node.js.
 *
 * 3. REFERENTIAL INTEGRITY (DATABASE TRANSACTION):
 * Setiap proses penyisipan (INSERT) wajib memperhatikan urutan ketergantungan 
 * Foreign Key (Tabel Dimensi -> Tabel Fakta). Kesalahan urutan akan 
 * mengakibatkan Constraint Violation (Foreign Key Error).
 * =============================================================================
 */

import initSqlJs from 'sql.js';
import fs from 'fs';
import path from 'path';
import { enrichMetadata } from './data-enricher';

export default async function handler(req, res) {
    // --- [1] CORS MIDDLEWARE CONFIGURATION ---
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

    if (req.method === 'OPTIONS') return res.status(200).end();

    if (req.method !== 'POST') {
        return res.status(405).json({ error: 'Method Not Allowed' });
    }

    try {
        const dbPath = path.resolve(process.cwd(), 'data/database.sqlite');
        const SQL = await initSqlJs();
        const fileBuffer = fs.readFileSync(dbPath);
        const db = new SQL.Database(fileBuffer);

        const { verification_result, status, fileName } = req.body;

        if (verification_result && Array.isArray(verification_result) && verification_result.length > 0) {
            
            // --- [2] TIME SYNCHRONIZATION LOGIC (Jakarta Timezone Sync) ---
            const apiTimestamp = req.body.timestamp || Date.now();
            const d = new Date(apiTimestamp);

            const wibTime = new Intl.DateTimeFormat('sv-SE', {
                timeZone: 'Asia/Jakarta',
                year: 'numeric', month: '2-digit', day: '2-digit',
                hour: '2-digit', minute: '2-digit', second: '2-digit',
                hour12: false
            }).formatToParts(d);

            const parts = {};
            wibTime.forEach(({type, value}) => parts[type] = value);

            const isoDateOnly = `${parts.year}-${parts.month}-${parts.day}`;
            const isoFullTime = `${isoDateOnly} ${parts.hour}:${parts.minute}:${parts.second}`;
            const docTimestamp = isoFullTime.replace(/[- :]/g, '');

            // --- [3] INTEGRITY AGGREGATION LOGIC ---
            const totalSignatures = verification_result.length;
            
            const hasLTVIssue = verification_result.some(sig => {
                const ltvText = sig.LTV || "";
                const isSelfSigned = sig.Certificate === "Self-Signed";
                return ltvText.includes("Not") || !ltvText.includes("Support") || isSelfSigned;
            });

            const finalLTVStatus = hasLTVIssue ? "LTV Not Supported" : "Support LTV";
            
            let aggregatedReason = `Found ${totalSignatures} signatures. `;
            if (verification_result.some(sig => sig.Certificate === "Self-Signed")) {
                aggregatedReason += "Untrusted Self-Signed Certificate detected.";
            } else if (hasLTVIssue) {
                aggregatedReason += "Technical LTV Issues detected.";
            } else {
                aggregatedReason += "All signatures support LTV.";
            }

            const primarySig = verification_result[0];
            const enriched = enrichMetadata(primarySig, status);

            const getVal = (str, key) => {
                const match = str?.match(new RegExp(`${key}=([^,]+)`));
                return match ? match[1].trim() : "Unknown";
            };

            const sDN = primarySig.SubjectDN || "";
            const iDN = primarySig.Issuer || "";

            // --- [4] DATABASE INGESTION PROCESS (ETL LOAD PHASE) ---
            const monthNames = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];

            // 1. Ingest Dimensi Date (C3) - Idempotent
            db.run(`INSERT OR IGNORE INTO esa_dim_date_c3 (c3_full_date, c3_month_name, c3_year, c3_day, c3_hour) VALUES (?, ?, ?, ?, ?)`, 
                [isoDateOnly, monthNames[parseInt(parts.month) - 1], parseInt(parts.year), parseInt(parts.day), parseInt(parts.hour)]);
            
            const stmtDate = db.prepare(`SELECT c3_date_key FROM esa_dim_date_c3 WHERE c3_full_date = ? AND c3_hour = ?`);
            const resDate = stmtDate.getAsObject([isoDateOnly, parseInt(parts.hour)]);
            const dateKey = resDate.c3_date_key || 1;
            stmtDate.free();

            // 2. Ingest Dimensi Signer (C1) - Idempotent
            const signerCN = primarySig["Signer "] || primarySig["Signer"] || "Unknown";
            const serialNum = primarySig["Serial Number"] || "N/A";
            const signerOrg = getVal(sDN, "O") === "Unknown" ? "Personal" : getVal(sDN, "O");
            
            db.run(`INSERT OR IGNORE INTO esa_dim_signer_c1 (c1_common_name, c1_serial_number, c1_organization, c1_country, c1_sha1_fingerprint, c1_full_subject_dn) VALUES (?, ?, ?, ?, ?, ?)`, 
                [signerCN, serialNum, signerOrg, getVal(sDN, "C"), enriched.fingerprint, sDN]);
            
            // Mengubah acuan kueri dari serial_number ke sha1_fingerprint agar sinkron sempurna dengan arsitektur Python
            const stmtSigner = db.prepare(`SELECT c1_signer_key FROM esa_dim_signer_c1 WHERE c1_sha1_fingerprint = ?`);
            const resSigner = stmtSigner.getAsObject([enriched.fingerprint]);
            const signerKey = resSigner.c1_signer_key || 1;
            stmtSigner.free();

            // 3. Ingest Dimensi Issuer (C2) - Idempotent
            const rawIssuerOrg = getVal(iDN, "O");
            const issuerName = (primarySig.Certificate === "Self-Signed") ? "Internal/Private CA" : getVal(iDN, "CN");
            
            db.run(`INSERT OR IGNORE INTO esa_dim_issuer_c2 (c2_common_name, c2_organization, c2_country, c2_sig_algo, c2_full_distinguished_name) VALUES (?, ?, ?, ?, ?)`, 
                [issuerName, rawIssuerOrg, getVal(iDN, "C"), primarySig["Signature Algorithm"] || "RSA/SHA256", iDN]);
            
            const stmtIssuer = db.prepare(`SELECT c2_issuer_key FROM esa_dim_issuer_c2 WHERE c2_full_distinguished_name = ?`);
            const resIssuer = stmtIssuer.getAsObject([iDN]);
            const issuerKey = resIssuer.c2_issuer_key || 1;
            stmtIssuer.free();

            // 4. Ingest Dimensi Corporate (C4) - Idempotent
            const corpoName = (signerOrg === "Personal") ? "Personal" : signerOrg;
            db.run(`INSERT OR IGNORE INTO esa_dim_corporate_c4 (c4_corpo_name, c4_corpo_code) VALUES (?, ?)`, 
                [corpoName, corpoName.substring(0,3).toUpperCase()]);
            
            const stmtCorp = db.prepare(`SELECT c4_corpo_key FROM esa_dim_corporate_c4 WHERE c4_corpo_name = ?`);
            const resCorp = stmtCorp.getAsObject([corpoName]);
            const corpKey = resCorp.c4_corpo_key || 1;
            stmtCorp.free();

            // 5. Ingest Dimensi Integrity (C5) - Audit Trail Logging
            db.run(`INSERT INTO esa_dim_integrity_c5 (c5_status_type, c5_integrity_desc, c5_local_timestamp, c5_location, c5_reason, c5_status_code) VALUES (?, ?, ?, ?, ?, ?)`, 
                [status, "Aggregated Doc Check", isoFullTime, "Indonesia", aggregatedReason, 200]);
            
            const stmtRowId = db.prepare(`SELECT last_insert_rowid() as last_id`);
            const integrityKey = stmtRowId.getAsObject().last_id || 1;
            stmtRowId.free();

            // 6. Ingest Fact Table (F1)
            const finalDocID = (fileName && !fileName.includes('T')) ? fileName : `DOC-${docTimestamp}`;
            const hashStatusFinal = (status.includes("ideal") || primarySig["File hash Validation"] === true) ? "File hash Valid" : "Hash Invalid";
            const infoTSAFinal = primarySig["timestamp signature"] === "verified" ? "eSign Timestamp Service" : "Not Provided";

            db.run(`
                INSERT INTO esa_fact_verifications (
                    c1_signer_key, c2_issuer_key, c3_date_key, c4_corpo_key, c5_integrity_key,
                    f1_doc_id, f1_chain_status, f1_is_trusted, f1_sig_status, f1_hash_status, 
                    f1_ltv_status, f1_tsa_status, f1_is_expired, f1_validity_days, f1_signing_time, f1_ingested_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            `, [
                signerKey, issuerKey, dateKey, corpKey, integrityKey, 
                finalDocID, "Verified", status.includes("ideal") ? 1 : 0, 
                "verified", hashStatusFinal, finalLTVStatus, infoTSAFinal, 
                0, 365, isoFullTime, isoFullTime
            ]);

            // [Persistence Layer Sync] Komit pembaruan status memori biner ke storage fisik disk
            const data = db.export();
            fs.writeFileSync(dbPath, Buffer.from(data));
            
            return res.status(200).json({ 
                message: 'Success!', 
                dataWeb: { lokasi: "Indonesia", alasan: aggregatedReason, ltv: finalLTVStatus } 
            });

        } else {
            return res.status(400).json({ error: "Empty Verification Result" });
        }
    } catch (error) {
        console.error("❌ [SYSTEM ERROR] Transaksi database gagal: ", error.message);
        return res.status(500).json({ error: error.message });
    }
}