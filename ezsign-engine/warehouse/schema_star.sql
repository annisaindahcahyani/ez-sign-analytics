-- =============================================
-- REBUILD TOTAL: STAR SCHEMA EZSIGN ANALYTICS
-- Version: 2.0 (Updated: Office & UI Figma Requirements)
-- =============================================

-- 1. Dimensi Signer (C1): Informasi Identitas & Sertifikat Digital
CREATE TABLE esa_dim_signer_c1 (
    c1_signer_key INTEGER PRIMARY KEY AUTOINCREMENT,
    c1_full_subject_dn TEXT,       -- Contoh: CN=TARADIVA NOVIA, O=PT SIG, C=ID
    c1_common_name TEXT,           -- Nama Penandatangan (Pemberi Tanda Tangan)
    c1_organization TEXT,          -- Nama Instansi/Organisasi
    c1_country TEXT,               -- Kode Negara (e.g., ID)
    c1_serial_number TEXT UNIQUE,  -- Nomor unik CA (Identitas Utama)
    c1_sha1_fingerprint TEXT,      -- Sidik Jari Digital Sertifikat (RILL KOMDIGI)
    c1_valid_from TEXT,            -- Tanggal Mulai Sertifikat (Timestamp)
    c1_valid_until TEXT            -- Tanggal Berakhir Sertifikat (Timestamp)
);

-- 2. Dimensi Issuer (C2): CA Provider (Penerbit Sertifikat)
CREATE TABLE esa_dim_issuer_c2 (
    c2_issuer_key INTEGER PRIMARY KEY AUTOINCREMENT,
    c2_full_distinguished_name TEXT, -- Identitas Lengkap CA (Issuer DN)
    c2_common_name TEXT,             -- Nama CA (e.g., e Sign CA Class 1)
    c2_organization TEXT,            -- Organisasi CA
    c2_country TEXT,                 -- Negara CA
    c2_sig_algo TEXT,                -- Signature Algorithm (Contoh: SHA256withRSA)
    c2_is_berinduk INTEGER DEFAULT 1 -- Status Sertifikat Berinduk Kominfo
);

-- 3. Dimensi Date/Time (C3): Analisis Tren Waktu Ingest
CREATE TABLE esa_dim_date_c3 (
    c3_date_key INTEGER PRIMARY KEY AUTOINCREMENT,
    c3_full_date DATE,
    c3_month_name TEXT,
    c3_year INTEGER,
    c3_day INTEGER,
    c3_hour INTEGER
);

-- 4. Dimensi Corporate (C4): Mapping Tenant/Vendor
CREATE TABLE esa_dim_corporate_c4 (
    c4_corpo_key INTEGER PRIMARY KEY AUTOINCREMENT,
    c4_corpo_code TEXT,              -- Kode Perusahaan (e.g., SIG)
    c4_corpo_name TEXT               -- Nama Lengkap Perusahaan
);

-- 5. Dimensi Integrity (C5): Detail Keaslian & Bukti Fisik
CREATE TABLE esa_dim_integrity_c5 (
    c5_integrity_key INTEGER PRIMARY KEY AUTOINCREMENT,
    c5_status_code INTEGER,          -- Status HTTP/API (e.g., 200)
    c5_status_type TEXT,             -- Trusted / Not Trusted
    c5_integrity_desc TEXT,          -- Deskripsi Hash (e.g., File hash Valid)
    c5_error_message TEXT,           -- Pesan error jika verifikasi gagal
    c5_reason TEXT,                  -- Alasan Signature (Dari PDF Metadata)
    c5_location TEXT,                -- Lokasi Signer (Dari PDF Metadata)
    c5_local_timestamp TEXT          -- Stempel Waktu (Waktu terkunci di dokumen)
);

-- 6. Fact Table (F1): Pusat Analisis (Fact Verification)
CREATE TABLE esa_fact_verifications (
    f1_id INTEGER PRIMARY KEY AUTOINCREMENT,
    f1_doc_id TEXT,                  -- Nama File / Unique Document ID
    c1_signer_key INTEGER,
    c2_issuer_key INTEGER,
    c3_date_key INTEGER,
    c4_corpo_key INTEGER,
    c5_integrity_key INTEGER,
    f1_is_trusted INTEGER,           -- Flag Biner (1=Verified, 0=Failed)
    f1_is_expired INTEGER,           -- Status Ekspirasi (1=Expired, 0=Active)
    f1_validity_days INTEGER,        -- Sisa Masa Aktif (Countdown Hari)
    f1_ltv_status TEXT,              -- Status LTV (Long Term Validation)
    f1_tsa_status TEXT,              -- Info TSA Service (e.g., eSign TSA)
    f1_hash_status TEXT,             -- Status Validasi Hash Dokumen
    f1_sig_status TEXT,              -- Status Tanda Tangan Digital
    f1_chain_status TEXT,            -- Status Certificate Chain (Root CA)
    f1_signing_time BIGINT,          -- Waktu Penandatangan (Unix Epoch dari User)
    f1_ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (c1_signer_key) REFERENCES esa_dim_signer_c1(c1_signer_key),
    FOREIGN KEY (c2_issuer_key) REFERENCES esa_dim_issuer_c2(c2_issuer_key),
    FOREIGN KEY (c3_date_key) REFERENCES esa_dim_date_c3(c3_date_key),
    FOREIGN KEY (c4_corpo_key) REFERENCES esa_dim_corporate_c4(c4_corpo_key),
    FOREIGN KEY (c5_integrity_key) REFERENCES esa_dim_integrity_c5(c5_integrity_key)
);