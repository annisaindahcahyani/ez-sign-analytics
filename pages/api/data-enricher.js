import crypto from 'crypto';

export function enrichMetadata(rawData, status) {
    // 🕵️‍♂️ 1. LOGIK FINGERPRINT (Cari yang Asli Dulu!)
    // Kita cek semua kemungkinan nama field yang dikirim Komdigi/Jasuindo
    const originalFingerprint = rawData["SHA-1 Fingerprint"] || 
                               rawData["sha1"] || 
                               rawData["Fingerprint"] || 
                               rawData["fingerprint"];

    let finalFingerprint;
    
    if (originalFingerprint) {
        // Kalau ada yang asli, pake yang asli! Slay!
        finalFingerprint = originalFingerprint.toUpperCase();
    } else {
        // Kalau beneran GAK ADA, baru kita simulasiin biar gak kosong
        const serial = rawData["Serial Number"] || rawData.serialNumber || "NOSERIAL";
        finalFingerprint = crypto.createHash('sha1')
                                  .update(serial)
                                  .digest('hex')
                                  .toUpperCase()
                                  .match(/.{1,2}/g)
                                  .join(':');
    }

    // 🕵️‍♂️ 2. LOGIK REASON (Cari yang beneran ada isinya)
    const reason = rawData["Reason "] || // Ada spasi di belakang (sering terjadi!)
                   rawData["Reason"] || 
                   rawData["reason"] || 
                   rawData["Alasan"] || 
                   null;

    // 🕵️‍♂️ 3. LOGIK LOCATION
    const location = rawData["Location"] || 
                     rawData["location"] || 
                     rawData["Lokasi"] || 
                     "Indonesia";

    // 🕵️‍♂️ 4. LOGIK ERROR MESSAGE
    let errorMessage = "No Error Detected";
    if (!status.includes("ideal")) {
        errorMessage = rawData["Error Message"] || "Validation Warning";
    }

    return { 
        fingerprint: finalFingerprint, 
        errorMessage, 
        reason: (reason && reason.trim() !== "") ? reason : null, 
        location 
    };
}