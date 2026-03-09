-- =============================================
-- REBUILD TOTAL: STAR SCHEMA EZSIGN ANALYTICS
-- Sesuai Draw.io Page 1 & 9 + JSON Real-Time
-- =============================================

-- 1. Dimensi Signer (C1): Profile Penandatangan
CREATE TABLE esa_dim_signer_c1 (
    c1_signer_key INTEGER PRIMARY KEY AUTOINCREMENT,
    c1_signer_name TEXT,
    c1_subject_dn TEXT,
    c1_serial_number TEXT UNIQUE, -- Serial Number unik dari JSON
    c1_sha1_fingerprint TEXT -- Placeholder: Buat data Sidik Jari SHA-1
);

-- 2. Dimensi Issuer (C2): CA Provider
CREATE TABLE esa_dim_issuer_c2 (
    c2_issuer_key INTEGER PRIMARY KEY AUTOINCREMENT,
    c2_full_distinguished_name TEXT, -- Simpan aslinya buat audit
    c2_common_name TEXT,            -- Contoh: BSRE CA DS G1
    c2_organization TEXT,           -- Contoh: Badan Siber dan Sandi Negara
    c2_country TEXT,                -- Contoh: ID
    c2_sig_algo TEXT,
    c2_is_berinduk INTEGER DEFAULT 1
);

-- 3. Dimensi Date/Time (C3): Analisis Tren
CREATE TABLE esa_dim_date_c3 (
    c3_date_key INTEGER PRIMARY KEY AUTOINCREMENT,
    c3_full_date DATE,
    c3_month_name TEXT,
    c3_year INTEGER,
    c3_day INTEGER,
    c3_hour INTEGER
);

-- 4. Dimensi Corporate (C4): Mapping Vendor
CREATE TABLE esa_dim_corporate_c4 (
    c4_corpo_key INTEGER PRIMARY KEY AUTOINCREMENT,
    c4_corpo_code TEXT,
    c4_corpo_name TEXT
);

-- 5. Dimensi Integrity (C5): Status & Error
CREATE TABLE esa_dim_integrity_c5 (
    c5_integrity_key INTEGER PRIMARY KEY AUTOINCREMENT,
    c5_status_code INTEGER,   -- Diambil dari "code" (e.g., 200, 1003)
    c5_status_type TEXT,      -- Trusted / Not Trusted
    c5_integrity_desc TEXT,   -- Detail dari "File hash Validation"
    c5_error_message TEXT,     -- Pesan error Java yang panjang itu
    c5_reason TEXT,           -- Placeholder: Alasan TTE (UI Figma)
    c5_location TEXT,         -- Placeholder: Lokasi TTE (UI Figma)
    c5_local_timestamp TEXT   -- Placeholder: Stempel Waktu (UI Figma)
);

-- 6. Fact Table (F1): Central Analytics
CREATE TABLE esa_fact_verifications (
    f1_id INTEGER PRIMARY KEY AUTOINCREMENT,
    f1_doc_id TEXT,           -- Metadata file
    c1_signer_key INTEGER,
    c2_issuer_key INTEGER,
    c3_date_key INTEGER,
    c4_corpo_key INTEGER,
    c5_integrity_key INTEGER,
    f1_is_trusted INTEGER,    -- 1 (verified), 0 (failed)
    f1_is_expired INTEGER,    -- Hasil logic Python dari "Validity"
    f1_validity_days INTEGER, -- Sisa hari masa aktif
    f1_ltv_status TEXT,       -- Diambil dari "LTV"
    f1_tsa_status TEXT,       -- Placeholder: Info TSA (UI Figma)
    f1_hash_status TEXT,      -- Diambil dari "File hash Validation"
    f1_sig_status TEXT,       -- Diambil dari "timestamp signature"
    f1_chain_status TEXT,     -- Diambil dari "Verify_Certificate_Chain"
    f1_signing_time BIGINT,   -- Unix Epoch dari API
    f1_ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (c1_signer_key) REFERENCES esa_dim_signer_c1(c1_signer_key),
    FOREIGN KEY (c2_issuer_key) REFERENCES esa_dim_issuer_c2(c2_issuer_key),
    FOREIGN KEY (c3_date_key) REFERENCES esa_dim_date_c3(c3_date_key),
    FOREIGN KEY (c4_corpo_key) REFERENCES esa_dim_corporate_c4(c4_corpo_key),
    FOREIGN KEY (c5_integrity_key) REFERENCES esa_dim_integrity_c5(c5_integrity_key)
);