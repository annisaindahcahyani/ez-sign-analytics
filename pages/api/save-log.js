import initSqlJs from 'sql.js';
import fs from 'fs';
import path from 'path';
import { enrichMetadata } from './data-enricher';

export default async function handler(req, res) {
    // --- 1. CORS CONFIGURATION ---
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

    if (req.method === 'OPTIONS') return res.status(200).end();

    try {
        const dbPath = path.resolve(process.cwd(), 'data/database.sqlite');
        const SQL = await initSqlJs();
        const fileBuffer = fs.readFileSync(dbPath);
        const db = new SQL.Database(fileBuffer);

        const { verification_result, status, fileName } = req.body;

        if (verification_result && Array.isArray(verification_result) && verification_result.length > 0) {
            
// --- 2. CORE TIME LOGIC (REAL WIB CLOCK) ---
const apiTimestamp = req.body.timestamp || Date.now();
// Kita buat date object asli (UTC/Lokal)
const d = new Date(apiTimestamp);

// Pake Intl.DateTimeFormat biar dapet objek waktu Jakarta yang rill 💅
const wibTime = new Intl.DateTimeFormat('sv-SE', {
  timeZone: 'Asia/Jakarta',
  year: 'numeric', month: '2-digit', day: '2-digit',
  hour: '2-digit', minute: '2-digit', second: '2-digit',
  hour12: false
}).formatToParts(d);

const parts = {};
wibTime.forEach(({type, value}) => parts[type] = value);

// Kita buat format manual YYYY-MM-DD HH:mm:ss pake locale Indonesia 
const isoDateOnly = `${parts.year}-${parts.month}-${parts.day}`;
const isoFullTime = `${isoDateOnly} ${parts.hour}:${parts.minute}:${parts.second}`; // Hasilnya: 2026-04-07 09:14:59

// Untuk Doc ID biar gak ada 'Z' dan tetep WIB
const docTimestamp = isoFullTime.replace(/[- :]/g, '');


            // --- 3. AGGREGATION LOGIC (PER DOKUMEN) 🛡️ ---
            const totalSignatures = verification_result.length;
            
            // Cek masalah LTV (Kalo ada "Not", Gak ada "Support", atau Self-Signed = RED FLAG 🚩)
            const hasLTVIssue = verification_result.some(sig => {
                const ltvText = sig.LTV || "";
                const isSelfSigned = sig.Certificate === "Self-Signed";
                return ltvText.includes("Not") || !ltvText.includes("Support") || isSelfSigned;
            });

            const finalLTVStatus = hasLTVIssue ? "LTV Not Supported" : "Support LTV";
            
            // Bikin alasan yang informatif buat Dashboard
            let aggregatedReason = `Found ${totalSignatures} signatures. `;
            if (verification_result.some(sig => sig.Certificate === "Self-Signed")) {
                aggregatedReason += "Untrusted Self-Signed Certificate detected. LTV invalid.";
            } else if (hasLTVIssue) {
                aggregatedReason += "Technical LTV Issues detected.";
            } else {
                aggregatedReason += "All signatures support LTV.";
            }

            // Pakai data signature PERTAMA sebagai wakil metadata Signer/Issuer
            const primarySig = verification_result[0];
            const enriched = enrichMetadata(primarySig, status);

            // Helper Regex
            const getVal = (str, key) => {
                const match = str?.match(new RegExp(`${key}=([^,]+)`));
                return match ? match[1].trim() : "Unknown";
            };

            const sDN = primarySig.SubjectDN || "";
            const iDN = primarySig.Issuer || "";

            // --- 4. DIMENSI DATE (C3) ---
            const monthNames = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];

            // 1. Masukin datanya ke Dimensi Date (Pake parts biar WIB 💅)
            db.run(`INSERT OR IGNORE INTO esa_dim_date_c3 (c3_full_date, c3_month_name, c3_year, c3_day, c3_hour) VALUES (?, ?, ?, ?, ?)`, 
            [
                isoDateOnly, 
                monthNames[parseInt(parts.month) - 1], 
                parts.year, 
                parts.day, 
                parts.hour
            ]);

            // 2. NAH INI DIA SI BIANG KEROK! Kita ambil ID-nya biar bisa dipake di Fact Table 🛡️
            const dateKeyQuery = db.exec(`SELECT c3_date_key FROM esa_dim_date_c3 WHERE c3_full_date = '${isoDateOnly}'`);
            const dateKey = dateKeyQuery[0].values[0][0]; // Sekarang dateKey SUDAH DEFINED! 💅

            // --- 5. DIMENSI SIGNER (C1) ---
            const signerCN = primarySig["Signer "] || primarySig["Signer"] || "Unknown";
            const serialNum = primarySig["Serial Number"] || "N/A";
            const signerOrg = getVal(sDN, "O") === "Unknown" ? "Personal" : getVal(sDN, "O");
            
            db.run(`INSERT OR IGNORE INTO esa_dim_signer_c1 (c1_common_name, c1_serial_number, c1_organization, c1_country, c1_sha1_fingerprint, c1_full_subject_dn) VALUES (?, ?, ?, ?, ?, ?)`, 
            [signerCN, serialNum, signerOrg, getVal(sDN, "C"), enriched.fingerprint, sDN]);
            const signerKey = db.exec(`SELECT c1_signer_key FROM esa_dim_signer_c1 WHERE c1_serial_number = '${serialNum}'`)[0].values[0][0];

            // --- 6. DIMENSI ISSUER (C2) ---
            const rawIssuerOrg = getVal(iDN, "O");
            const issuerName = (primarySig.Certificate === "Self-Signed") ? "Internal/Private CA" : getVal(iDN, "CN");
            db.run(`INSERT OR IGNORE INTO esa_dim_issuer_c2 (c2_common_name, c2_organization, c2_country, c2_sig_algo, c2_full_distinguished_name) VALUES (?, ?, ?, ?, ?)`, 
            [issuerName, rawIssuerOrg, getVal(iDN, "C"), primarySig["Signature Algorithm"] || "RSA/SHA256", iDN]);
            const issuerKey = db.exec(`SELECT c2_issuer_key FROM esa_dim_issuer_c2 WHERE c2_full_distinguished_name = '${iDN}'`)[0].values[0][0];

            // --- 7. DIMENSI CORPORATE (C4) ---
            const corpoName = (signerOrg === "Personal") ? "Personal" : signerOrg;
            db.run(`INSERT OR IGNORE INTO esa_dim_corporate_c4 (c4_corpo_name, c4_corpo_code) VALUES (?, ?)`, [corpoName, corpoName.substring(0,3).toUpperCase()]);
            const corpKey = db.exec(`SELECT c4_corpo_key FROM esa_dim_corporate_c4 WHERE c4_corpo_name = '${corpoName}'`)[0].values[0][0];

            // --- 8. DIMENSI INTEGRITY (C5) ---
            db.run(`INSERT INTO esa_dim_integrity_c5 (c5_status_type, c5_integrity_desc, c5_local_timestamp, c5_location, c5_reason, c5_status_code) VALUES (?, ?, ?, ?, ?, ?)`, 
            [status, "Aggregated Doc Check", isoFullTime, "Indonesia", aggregatedReason, 200]);
            const integrityKey = db.exec(`SELECT last_insert_rowid()`)[0].values[0][0];

            // --- 9. FACT TABLE (F1) - URUTAN KOLOM SUDAH FIX! 🛡️ ---
            const finalDocID = (req.body.fileName && !req.body.fileName.includes('T')) ? req.body.fileName : `DOC-${docTimestamp}`;
            const hashStatusFinal = (status.includes("ideal") || primarySig["File hash Validation"] === true) ? "File hash Valid" : "Hash Invalid";
            const infoTSAFinal = primarySig["timestamp signature"] === "verified" ? "eSign Timestamp Service" : "Not Provided";

            db.run(`
                INSERT INTO esa_fact_verifications (
                    c1_signer_key, c2_issuer_key, c3_date_key, c4_corpo_key, c5_integrity_key,
                    f1_doc_id, f1_chain_status, f1_is_trusted, f1_sig_status, f1_hash_status, 
                    f1_ltv_status, f1_tsa_status, f1_is_expired, f1_validity_days, f1_signing_time, f1_ingested_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            `, [
                signerKey, 
                issuerKey, 
                dateKey, 
                corpKey, 
                integrityKey, 
                finalDocID, 
                "Verified", 
                status.includes("ideal") ? 1 : 0, 
                "verified", 
                hashStatusFinal,  // f1_hash_status
                finalLTVStatus,   // f1_ltv_status 🛡️ (Gak ketuker lagi jirr!)
                infoTSAFinal,     // f1_tsa_status
                0, 365, 
                isoFullTime 
            ]);

            const responseWeb = { lokasi: "Indonesia", alasan: aggregatedReason, ltv: finalLTVStatus };
            const data = db.export();
            fs.writeFileSync(dbPath, Buffer.from(data));
            res.status(200).json({ message: 'Success!', dataWeb: responseWeb });

        } else {
            res.status(400).json({ error: "Empty Verification Result" });
        }

    } catch (error) {
        console.error("❌ ERROR:", error.message);
        res.status(500).json({ error: error.message });
    }
}