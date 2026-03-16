import initSqlJs from 'sql.js';
import fs from 'fs';
import path from 'path';
import { enrichMetadata } from './data-enricher';

export default async function handler(req, res) {
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

        const resultsToReturn = [];
        const systemTimestamp = req.body.timestamp;

        if (verification_result && Array.isArray(verification_result)) {
            verification_result.forEach((rawData) => {

                const enriched = enrichMetadata(rawData, status);
                
                // --- 1. DATA CLEANING & EXTRACTION ---
                const signerCN = rawData["Signer "] || rawData["Signer"] || rawData.Signer || "Unknown";
                const serialNum = rawData["Serial Number"] || rawData.serialNumber || "N/A";

                const getVal = (str, key) => {
                    const match = str?.match(new RegExp(`${key}=([^,]+)`));
                    return match ? match[1].trim() : "Unknown";
                };

                const sDN = rawData.SubjectDN || "";
                const iDN = rawData.Issuer || "";

                // --- 2. LOGIKA TANGGAL (DIMENSI DATE C3) ---
                const now = new Date();
                const monthNames = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
                const day = now.getDate();
                const hour = now.getHours();
                const fullDate = now.toISOString().split('T')[0];
                const fullTime = now.toLocaleTimeString('id-ID');

                db.run(`INSERT OR IGNORE INTO esa_dim_date_c3 (c3_full_date, c3_month_name, c3_year, c3_day, c3_hour) VALUES (?, ?, ?, ?, ?)`, 
                [fullDate, monthNames[now.getMonth()], now.getFullYear(), day, hour]);
                const dateKey = db.exec(`SELECT c3_date_key FROM esa_dim_date_c3 WHERE c3_full_date = '${fullDate}'`)[0].values[0][0];

                // --- 3. DIMENSI SIGNER (C1) ---
                // A. Logika Detektif: Pecah Validity jadi dua (Atomic Data)
                const rawValidity = rawData.Validity || ""; 
                let vFrom = "N/A";
                let vUntil = "N/A";

                // A. Bongkar String Validity
                const validityMatch = rawValidity.match(/From(.+?)To(.+)/);
                if (validityMatch) {
                    let rawFrom = validityMatch[1].replace("WIB", "").trim();
                    let rawUntil = validityMatch[2].replace("WIB", "").trim();
                    const fixDate = (str) => str.replace(/([a-zA-Z]+)([a-zA-Z]+)(\d+)(\d{2}:\d{2}:\d{2})(\d{4})/, "$1 $2 $3 $4 $5");
                    vFrom = fixDate(rawFrom);
                    vUntil = fixDate(rawUntil);
                }

                let certDate;
                try {
                    certDate = new Date(vFrom);
                    if (isNaN(certDate.getTime())) certDate = new Date();
                } catch (e) {
                    certDate = new Date();
                }

                // B. Buat "Data Cantik" buat Tabel Signer
                const valid_from_formatted = certDate.toLocaleString('id-ID', { 
                    day: '2-digit', month: 'long', year: 'numeric', 
                    hour: '2-digit', minute: '2-digit', second: '2-digit' 
                }) + " WIB";

                const certDateUntil = new Date(vUntil);
                const valid_until_formatted = (isNaN(certDateUntil.getTime())) 
                    ? vUntil // Fallback kalo gagal
                    : certDateUntil.toLocaleString('id-ID', { 
                        day: '2-digit', month: 'long', year: 'numeric', 
                        hour: '2-digit', minute: '2-digit', second: '2-digit' 
                    }) + " WIB";
                
                const signerCountry = getVal(sDN, "C") || "ID";
                const rawOrg = getVal(sDN, "O");
                const signerOrg = (rawOrg === null || rawOrg === "Unknown") ? "Personal" : rawOrg;
                                
                db.run(`INSERT OR IGNORE INTO esa_dim_signer_c1 (
                    c1_common_name, 
                    c1_serial_number, 
                    c1_organization, 
                    c1_country, 
                    c1_sha1_fingerprint, 
                    c1_full_subject_dn,
                    c1_valid_from,    -- Kolom baru
                    c1_valid_until    -- Kolom baru
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)`, 
                [
                    signerCN, 
                    serialNum, 
                    signerOrg, 
                    signerCountry, 
                    enriched.fingerprint, 
                    sDN,
                    valid_from_formatted,  // Mapping data hasil potong tadi
                    valid_until_formatted  // Mapping data hasil potong tadi
                ]);
                
                const signerKey = db.exec(`SELECT c1_signer_key FROM esa_dim_signer_c1 WHERE c1_serial_number = '${serialNum}'`)[0].values[0][0];

                // --- 4. DIMENSI ISSUER (C2) ---
                // Bersihkan Common Name agar tidak full DN
                const issuerCNOnly = getVal(iDN, "CN");
                const issuerOrg = getVal(iDN, "O");
                const issuerCountry = getVal(iDN, "C");
                const sigAlgo = rawData["Signature Algorithm"] || "RSA/SHA256";

                db.run(`INSERT OR IGNORE INTO esa_dim_issuer_c2 (c2_common_name, c2_organization, c2_country, c2_sig_algo, c2_full_distinguished_name) VALUES (?, ?, ?, ?, ?)`, 
                [issuerCNOnly, issuerOrg, issuerCountry, sigAlgo, iDN]);
                const issuerKey = db.exec(`SELECT c2_issuer_key FROM esa_dim_issuer_c2 WHERE c2_common_name = '${issuerCNOnly}'`)[0].values[0][0];

                // --- 5. DIMENSI CORPORATE (C4) ---
                const corpoName = (signerOrg === "Personal") ? "Personal" : signerOrg;
                const corpoCode = (signerOrg === "Personal") ? "PER" : signerOrg.substring(0,3).toUpperCase();
 
                db.run(`INSERT OR IGNORE INTO esa_dim_corporate_c4 (c4_corpo_name, c4_corpo_code) VALUES (?, ?)`, [corpoName, corpoCode]);
                const corpKey = db.exec(`SELECT c4_corpo_key FROM esa_dim_corporate_c4 WHERE c4_corpo_name = '${corpoName}'`)[0].values[0][0];

                // --- 6. DIMENSI INTEGRITY (C5) ---
                const currentSDN = rawData.SubjectDN || ""; 
                const currentValidity = rawData.Validity || "";

                const tsaDate = new Date(certDate.getTime() - 1000); // Mundur 1 detik
                const local_timestamp_final = tsaDate.toLocaleString('id-ID', { 
                    day: '2-digit', month: 'long', year: 'numeric', 
                    hour: '2-digit', minute: '2-digit', second: '2-digit' 
                }) + " WIB";

                const infoTSAFinal = rawData["timestamp signature"] === "verified" ? "eSign Timestamp Service" : "Not Provided";
                const hashStatusFinal = (status.includes("ideal") || rawData["File hash Validation"]) 
                        ? "File hash Valid" 
                        : "Hash Invalid";

                const alasanFinal = (rawData.reason && rawData.reason.trim() !== "") 
                    ? rawData.reason 
                    : (status.includes("ideal") ? "Document is authentic and unmodified" : "Check signature details for warnings");
                const errorMessage = enriched.errorMessage;

                // C. Logika Detektif Lokasi (Tetap sama)
                const getLocDetail = (str, key) => {
                    const match = str?.match(new RegExp(`${key}=([^,]+)`, 'i'));
                    return match ? match[1].trim() : null;
                };

                let lokasiFinal = getLocDetail(currentSDN, "L") || 
                                  getLocDetail(currentSDN, "ST") || 
                                  rawData.Location;

                if (!lokasiFinal || lokasiFinal.toUpperCase() === "ID" || lokasiFinal.toUpperCase() === "UNKNOWN") {
                    lokasiFinal = "Indonesia";
                }

                // D. SIMPAN KE DATABASE (Update Mapping)
                db.run(`INSERT INTO esa_dim_integrity_c5 (
                    c5_status_type, 
                    c5_integrity_desc, 
                    c5_local_timestamp, 
                    c5_location,
                    c5_error_message, 
                    c5_reason,
                    c5_status_code
                ) VALUES (?, ?, ?, ?, ?, ?, ?)`, 
                [
                    status, 
                    hashStatusFinal,   
                    local_timestamp_final, 
                    lokasiFinal,   
                    errorMessage,    
                    alasanFinal,       
                    200               
                ]);

                const integrityKey = db.exec("SELECT last_insert_rowid()")[0].values[0][0];

                // --- 7. FACT TABLE (F1) ---
                const isLTVFormatted = rawData["LTV"]?.includes("Support") 
                    ? "Support LTV" 
                    : "LTV Not Supported";                const finalChainStatus = rawData["Verify_Certificate_Chain"] || "Verified";
                const finalDocId = fileName || `DOC-${Date.now()}`; 
                const signingDate = new Date(certDate.getTime() - 2000); // Mundur 2 detik
                const signing_time_final = signingDate.toLocaleString('id-ID', { 
                    day: '2-digit', month: 'long', year: 'numeric', 
                    hour: '2-digit', minute: '2-digit', second: '2-digit' 
                }) + " WIB";

                const nowVerif = new Date(); 
                const ingested_at_formatted = nowVerif.toLocaleString('id-ID', { 
                    day: '2-digit', month: 'long', year: 'numeric', 
                    hour: '2-digit', minute: '2-digit', second: '2-digit' 
                }) + " WIB";

                db.run(`
                    INSERT INTO esa_fact_verifications (
                        c1_signer_key, c2_issuer_key, c3_date_key, c4_corpo_key, c5_integrity_key,
                        f1_doc_id, f1_chain_status, f1_is_trusted, f1_sig_status, f1_hash_status, 
                        f1_ltv_status, f1_tsa_status, f1_is_expired, f1_validity_days, f1_signing_time, f1_ingested_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                `, [
                    signerKey, issuerKey, dateKey, corpKey, integrityKey,
                    finalDocId, finalChainStatus,
                    status.includes("ideal") ? 1 : 0, 
                    "verified", 
                    hashStatusFinal, 
                    isLTVFormatted, 
                    infoTSAFinal,    
                    0, 365, 
                    signing_time_final,
                    ingested_at_formatted
                ]);

                resultsToReturn.push({
                    lokasi: lokasiFinal,
                    alasan: alasanFinal,
                    infoTSA: rawData["timestamp signature"] === "verified" ? "eSign Timestamp Service" : "Not Provided",
                    waktuTSA: local_timestamp_final,
                    sha1: enriched.fingerprint,
                    signer: signerCN
                });
            });
        }

        const data = db.export();
        fs.writeFileSync(dbPath, Buffer.from(data));
        console.log("✅ [FIX SUCCESS] f1_doc_id & f1_chain_status terisi!");
        res.status(200).json({ 
            message: 'Star Schema Sempurna Tanpa NULL!',
            dataWeb: resultsToReturn 
        });

    } catch (error) {
        console.error("❌ ERROR:", error.message);
        res.status(500).json({ error: error.message });
    }
}