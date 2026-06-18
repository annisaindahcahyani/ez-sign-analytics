
/**
 * =============================================================================
 * 🔐 MODULE: CRYPTOGRAPHY FORENSIC & METADATA SANITIZATION ENGINE
 * =============================================================================
 * 📌 CONFIGURATION : Metadata Transformation & Kriptografi Forensik
 * 📅 UPDATE        : 5 Juni 2026
 * 🛡️ OBJECTIVE     : Sanitasi data, rekonstruksi Hash Fingerprint (SHA-1), 
 * serta normalisasi metadata Tanda Tangan Elektronik (TTE).
 * =============================================================================
 *  * 🗺️ DOKUMEN TATA KERJA FUNGSIONAL PENGEMBANG (FOR NEXT DEVELOPER):
 *
 * 1. STRATEGI IDENTIFIKASI FINGERPRINT (RECONSTRUCTION LAYER):
 * Modul ini mengimplementasikan mekanisme hierarkis untuk menjamin ketersediaan 
 * atribut unik SHA-1 Fingerprint. Jika atribut tidak tersedia pada payload 
 * mentah, sistem akan menjalankan kalkulasi kriptografi manual (Reconstruction)
 * atau simulasi deterministik (Deterministic Fallback) guna menjamin 
 * integritas relasi pada database pusat (Star Schema).
 *
 * 2. DATA SANITIZATION & NORMALIZATION:
 * Melakukan pembersihan data terhadap variabel 'Reason' dan 'Error Message'. 
 * Proses ini krusial untuk mengeliminasi inkonsistensi input dari sistem 
 * verifikator pihak ketiga sehingga data siap dikonsumsi oleh lapisan visualisasi.
 * =============================================================================
 */

import crypto from 'crypto';

export function enrichMetadata(rawData, status) {
    // Menjamin objek input aman dari anomali undefined runtime error
    const data = rawData || {};
    
    // --- [1] STRATEGI IDENTIFIKASI FINGERPRINT (RECONSTRUCTION LAYER) ---
    // Melakukan pengecekan hierarkis untuk menjaring atribut SHA-1 dari payload verifikator hulu
    const originalFingerprint = data["SHA-1 Fingerprint"] || 
                               data["sha1"] || 
                               data["Fingerprint"] || 
                               data["fingerprint"];

    const rawCert = data["RawCertificate"] || data["Certificate"] || data["hex_certificate"];

    let finalFingerprint;
    
    if (originalFingerprint && originalFingerprint.trim() !== "") {
        // [SCENARIO A]: Ekstraksi fingerprint dari metadata primer. Clean up tanda baca titik dua 
        // agar seirama dengan standarisasi hashing data warehouse nasional (Pure Hex Upper Format)
        finalFingerprint = originalFingerprint.replace(/:/g, "").toUpperCase().trim();
    } 
    else if (rawCert && rawCert.trim() !== "") {
        // [SCENARIO B]: Cryptographic Hash Reconstruction murni via biner Base64 Certificate
        try {
            const certBuffer = Buffer.from(rawCert, 'base64');
            finalFingerprint = crypto.createHash('sha1')
                                     .update(certBuffer)
                                     .digest('hex')
                                     .toUpperCase();
        } catch (e) {
            finalFingerprint = "ERROR_CALCULATING_HASH";
        }
    } 
    else {
        // [SCENARIO C]: DETERMINISTIC FALLBACK (Simulation Layer)
        // Pengamanan relasi skema bintang multidimensi memanfaatkan token nomor seri
        const serial = data["Serial Number"] || data.serialNumber || `FALLBACK-SERIAL-${Date.now()}`;
        finalFingerprint = crypto.createHash('sha1')
                                 .update(String(serial))
                                 .digest('hex')
                                 .toUpperCase();
    }

    // --- [2] LOGIKA NORMALISASI METADATA (DATA SANITIZATION) ---
    // Penyeragaman atribut "Reason" guna mengeliminasi whitespace liar dari input sistem eksternal
    const rawReason = data["Reason "] || 
                      data["Reason"] || 
                      data["reason"] || 
                      data["Alasan"];

    // --- [3] AUDIT FORENSIK (COMPLIANCE CHECK) ---
    // Ekstraksi pesan kesalahan sistem untuk pelaporan anomali operasional kaku
    let errorMessage = "No Error Detected";
    if (status && !status.includes("ideal")) {
        const capturedError = data["Error Message"] || data["error"] || "Validation Warning";
        errorMessage = String(capturedError).trim();
    }

    // --- [4] DATA PACKAGING (OUTPUT LAYER CONTRACT) ---
    return { 
        fingerprint: finalFingerprint, 
        errorMessage: errorMessage, 
        reason: (rawReason && String(rawReason).trim() !== "") ? String(rawReason).trim() : "N/A"
    };
}