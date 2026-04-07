import crypto from 'crypto';
/**
 * ENRICHER METADATA FUNCTION
 * Fungsi ini bertugas untuk melakukan "Data Ingestion & Transformation".
 * Mengolah data mentah dari Backend menjadi metadata terstruktur yang siap masuk ke Star Schema.
 */
export function enrichMetadata(rawData, status) {
    // --- 🕵️‍♂️ 1. LOGIKA IDENTIFIKASI FINGERPRINT (SHA-1) ---
    // Mencari ketersediaan SHA-1 Fingerprint dari berbagai variasi nama field (Backward Compatibility)
    const originalFingerprint = rawData["SHA-1 Fingerprint"] || 
                               rawData["sha1"] || 
                               rawData["Fingerprint"] || 
                               rawData["fingerprint"];

    // Mencari data sertifikat mentah (Base64) untuk kebutuhan validasi rill
    const rawCert = rawData["RawCertificate"] || rawData["Certificate"] || rawData["hex_certificate"];

    let finalFingerprint;
    
    if (originalFingerprint && originalFingerprint.trim() !== "") {
        // [SCENARIO A]: Gunakan fingerprint yang sudah disediakan oleh sistem verifikator.
        finalFingerprint = originalFingerprint.toUpperCase();
    } else if (rawCert && rawCert.trim() !== "") {
        // [SCENARIO B]: 🔥 THE "REAL" CRYPTO WAY
        // Jika fingerprint absen tapi raw certificate ada, kita hitung manual hash SHA-1 nya.
        // Langkah: Base64 -> Buffer -> SHA-1 Hash -> Format Hex dengan separator ':'
        try {
            const certBuffer = Buffer.from(rawCert, 'base64');
            finalFingerprint = crypto.createHash('sha1')
                                     .update(certBuffer)
                                     .digest('hex')
                                     .toUpperCase()
                                     .match(/.{1,2}/g) // Pecah string per 2 karakter (XX:XX:XX)
                                     .join(':');
        } catch (e) {
            finalFingerprint = "ERROR_CALCULATING_HASH";
        }
    } else {
        // [SCENARIO C]: DETERMINISTIC FALLBACK
        // Jika data absen total, buat fingerprint simulasi berbasis Serial Number agar data tetap unik di DB.
        const serial = rawData["Serial Number"] || rawData.serialNumber || `FAKE-${Date.now()}`;
        finalFingerprint = crypto.createHash('sha1')
                                  .update(serial)
                                  .digest('hex')
                                  .toUpperCase()
                                  .match(/.{1,2}/g)
                                  .join(':');
    }

    // --- 🕵️‍♂️ 2. LOGIKA NORMALISASI REASON ---
    // Menangani variasi penulisan key "Reason" (Termasuk typo spasi di belakang dari sistem verifikator)
    const rawReason = rawData["Reason "] || 
                      rawData["Reason"] || 
                      rawData["reason"] || 
                      rawData["Alasan"];

    // --- 🕵️‍♂️ 3. LOGIKA ERROR MESSAGE (COMPLIANCE CHECK) ---
    // Jika status tidak 'ideal', tarik pesan error untuk kebutuhan audit forensik di Dashboard.
    let errorMessage = "No Error Detected";
    if (status && !status.includes("ideal")) {
        errorMessage = rawData["Error Message"] || rawData["error"] || "Validation Warning";
    }

    // --- 🕵️‍♂️ 4. DATA PACKAGING (OUTPUT) ---
    return { 
        fingerprint: finalFingerprint, 
        errorMessage: errorMessage, 
        // Mengembalikan reason yang sudah bersih (trim) atau string kosong untuk di-handle fallback-nya di save-log
        reason: (rawReason && rawReason.trim() !== "") ? rawReason.trim() : ""
    };
}