import Database from 'better-sqlite3';
import path from 'path';
import fs from 'fs';

export default function handler(req, res) {
  res.setHeader('Access-Control-Allow-Credentials', true);
    res.setHeader('Access-Control-Allow-Origin', '*'); // Mengizinkan semua laptop (termasuk Cia)
    res.setHeader('Access-Control-Allow-Methods', 'GET,OPTIONS,PATCH,DELETE,POST,PUT');
    res.setHeader(
        'Access-Control-Allow-Headers',
        'X-CSRF-Token, X-Requested-With, Accept, Accept-Version, Content-Length, Content-MD5, Content-Type, Date, X-Api-Version'
    );

    // Handle Preflight Request (Salaman awal browser)
    if (req.method === 'OPTIONS') {
        res.status(200).end();
        return;
    }

  if (req.method !== 'POST') {
    return res.status(405).json({ message: 'Harus POST ya Ca! 💅' });
  }

  const dbPath = path.resolve(process.cwd(), 'data/database.sqlite');
  const db = new Database(dbPath);

  try {
    const { verification_result, status, timestamp } = req.body;
    const rawData = verification_result && verification_result[0] ? verification_result[0] : {};

    // ==========================================
    // 1. BEDAH DATA ISSUER (C2)
    // ==========================================
    const issuerCN = rawData.issuer?.commonName || 'Unknown';
    const issuerO = rawData.issuer?.organizationName || 'Unknown';
    const issuerC = rawData.issuer?.countryName || 'Unknown';
    const fullIssuerDN = `CN=${issuerCN}, O=${issuerO}, C=${issuerC}`;

    const insertIssuer = db.prepare(`
      INSERT OR IGNORE INTO esa_dim_issuer_c2 (c2_full_distinguished_name, c2_common_name, c2_organization, c2_country)
      VALUES (?, ?, ?, ?)
    `);
    insertIssuer.run(fullIssuerDN, issuerCN, issuerO, issuerC);
    const issuerKey = db.prepare('SELECT c2_issuer_key FROM esa_dim_issuer_c2 WHERE c2_full_distinguished_name = ?').get(fullIssuerDN).c2_issuer_key;

    // ==========================================
    // 2. BEDAH DATA SIGNER (C1)
    // ==========================================
    const signerCN = rawData.subject?.commonName || 'Unknown';
    const signerO = rawData.subject?.organizationName || 'Unknown';
    const signerC = rawData.subject?.countryName || 'Unknown';
    const serialNum = rawData.serialNumber || 'N/A';
    const fullSubjectDN = `C=${signerC}, O=${signerO}, CN=${signerCN}`;

    const insertSigner = db.prepare(`
      INSERT OR IGNORE INTO esa_dim_signer_c1 (c1_full_subject_dn, c1_common_name, c1_organization, c1_country, c1_serial_number)
      VALUES (?, ?, ?, ?, ?)
    `);
    insertSigner.run(fullSubjectDN, signerCN, signerO, signerC, serialNum);
    const signerKey = db.prepare('SELECT c1_signer_key FROM esa_dim_signer_c1 WHERE c1_serial_number = ?').get(serialNum).c1_signer_key;

    // ==========================================
    // 3. ISI DIMENSI INTEGRITY (C5) - Biar Detail!
    // ==========================================
    const integrityDesc = rawData.file_hash_validation || 'N/A';
    const insertIntegrity = db.prepare(`
      INSERT INTO esa_dim_integrity_c5 (c5_status_type, c5_integrity_desc)
      VALUES (?, ?)
    `);
    const integrityResult = insertIntegrity.run(status, integrityDesc);
    const integrityKey = integrityResult.lastInsertRowid;

    // ==========================================
    // 4. ISI TABEL FAKTA (F1) - Versi Full Sinkron
    // ==========================================
    const isTrusted = status === 'Trusted' ? 1 : 0; 

    const insertFact = db.prepare(`
      INSERT INTO esa_fact_verifications (
        c1_signer_key, 
        c2_issuer_key, 
        c5_integrity_key,
        f1_is_trusted, 
        f1_sig_status,
        f1_hash_status
      ) VALUES (?, ?, ?, ?, ?, ?)
    `);

    insertFact.run(
      signerKey, 
      issuerKey, 
      integrityKey, 
      isTrusted, 
      rawData.timestamp_signature || 'N/A',
      rawData.file_hash_validation || 'N/A'
    );

    // ==========================================
    // 5. IMPLEMENTASI AUTO-PURGE (UU PDP Safe)
    // ==========================================
    // Logika: Jika ada file PDF tersisa di staging, langsung musnahkan!
    if (rawData.fileName) {
        const tempFilePath = path.resolve(process.cwd(), `data/staging/${rawData.fileName}`);
        if (fs.existsSync(tempFilePath)) {
            fs.unlinkSync(tempFilePath);
            console.log(`🗑️ [PDP COMPLIANCE] File ${rawData.fileName} telah dimusnahkan secara permanen.`);
        }
    }

    return res.status(200).json({ 
      message: 'Star Schema Slay! Data tersimpan & file dimusnahkan (PDP Safe).',
      details: { signer: signerCN, issuer: issuerCN }
    });

  } catch (error) {
    console.error("❌ ERROR STAR SCHEMA:", error);
    return res.status(500).json({ error: error.message });
  }
}