import crypto from 'crypto';

export function enrichMetadata(rawData, status) {
    // 🕵️‍♂️ 1. LOGIKA FINGERPRINT (Sudah Slay!)
    const originalFingerprint = rawData["SHA-1 Fingerprint"] || 
                               rawData["sha1"] || 
                               rawData["Fingerprint"] || 
                               rawData["fingerprint"];

    // Cek apakah ada sertifikat mentah (Base64) untuk dihitung rill
    const rawCert = rawData["RawCertificate"] || rawData["Certificate"] || rawData["hex_certificate"];

    let finalFingerprint;
    
    if (originalFingerprint && originalFingerprint.trim() !== "") {
        // A. Pake yang udah jadi (kalo BE udah pinter)
        finalFingerprint = originalFingerprint.toUpperCase();
    } else if (rawCert && rawCert.trim() !== "") {
        // B. 🔥 THE "REAL" WAY: Hitung dari sertifikat mentah PDF
        // Kita ubah Base64 jadi buffer, terus di-hash SHA-1
        try {
            const certBuffer = Buffer.from(rawCert, 'base64');
            finalFingerprint = crypto.createHash('sha1')
                                     .update(certBuffer)
                                     .digest('hex')
                                     .toUpperCase()
                                     .match(/.{1,2}/g)
                                     .join(':');
        } catch (e) {
            finalFingerprint = "ERROR_CALCULATING_HASH";
        }
    } else {
        // C. Fallback: Simulasi dari Serial Number (Deterministic Simulation)
        const serial = rawData["Serial Number"] || rawData.serialNumber || `FAKE-${Date.now()}`;
        finalFingerprint = crypto.createHash('sha1')
                                  .update(serial)
                                  .digest('hex')
                                  .toUpperCase()
                                  .match(/.{1,2}/g)
                                  .join(':');
    }

    // 🕵️‍♂️ 2. LOGIKA REASON (Cari semua variasi nama field)
    // Kita tambahkan pengecekan spasi di belakang ("Reason ")
    const rawReason = rawData["Reason "] || 
                      rawData["Reason"] || 
                      rawData["reason"] || 
                      rawData["Alasan"];

    // 🕵️‍♂️ 3. LOGIKA ERROR MESSAGE
    let errorMessage = "No Error Detected";
    if (status && !status.includes("ideal")) {
        errorMessage = rawData["Error Message"] || rawData["error"] || "Validation Warning";
    }

    // 🕵️‍♂️ 4. RETURN DATA (Pastikan Reason tidak me-return NULL yang merusak)
    return { 
        fingerprint: finalFingerprint, 
        errorMessage: errorMessage, 
        // Jika reason benar-benar kosong, kirim string kosong agar save-log yang ambil alih fallback-nya
        reason: (rawReason && rawReason.trim() !== "") ? rawReason.trim() : ""
    };
}