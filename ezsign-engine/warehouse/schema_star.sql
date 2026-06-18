-- =============================================================================
-- 🗄️ MODULE: MULTIDIMENSIONAL STAR SCHEMA ARCHITECTURE (DATA WAREHOUSE)
-- =============================================================================
-- 📌 CONFIGURATION : DDL (Data Definition Language) for OLAP Integration
-- 📅 UPDATE        : 5 Juni 2026
-- 🛡️ OBJECTIVE     : Sentralisasi Data Verifikasi Transaksional (Single Source of Truth)
-- 🔬 METHODOLOGY   : Kimball's Data Warehouse Toolkit (Fact & Dimensions)
-- =============================================================================
-- 🗺️ DOKUMEN TATA KERJA FUNGSIONAL PENGEMBANG (FOR NEXT DEVELOPER):
--
-- 1. ARSITEKTUR MULTIDIMENSI (STAR SCHEMA):
--    Skema ini dirancang khusus untuk kebutuhan pemrosesan analitik (OLAP). 
--    Memisahkan antara data kualitatif/deskriptif (Tabel Dimensi C1-C5) dengan 
--    data kuantitatif/metrik bisnis (Tabel Fakta F1) guna mempercepat eksekusi 
--    kueri agregasi pada lapisan antarmuka Streamlit.
--
-- 2. INTEGRASI FOREIGN KEY (REFERENTIAL INTEGRITY):
--    Tabel fakta (esa_fact_verifications) mengikat seluruh entitas dimensi 
--    melalui relasi Foreign Key yang ketat. Pastikan proses Ingestion/ETL selalu 
--    memasukkan data ke tabel dimensi terlebih dahulu sebelum tabel fakta untuk 
--    mencegah pelanggaran integritas referensial (Constraint Violation).
-- =============================================================================

-- =============================================================================
-- [DIMENSION 1] Signer Entity (C1): Pemetaan Identitas & Kriptografi Subjek
-- =============================================================================
CREATE TABLE IF NOT EXISTS esa_dim_signer_c1 (
    c1_signer_key        INTEGER PRIMARY KEY AUTOINCREMENT,
    c1_common_name       TEXT,               -- Identitas Legal Penandatangan (Signer Name)
    c1_serial_number     TEXT,               -- Parameter Nomor Seri Identifikasi Otoritas Sertifikat
    c1_organization      TEXT,               -- Afiliasi Entitas/Organisasi Subjek (Corporate/Personal)
    c1_country           TEXT,               -- Kode Negara Terstandardisasi (Contoh: ID)
    c1_sha1_fingerprint  TEXT UNIQUE,        -- Sidik Jari Kriptografi (Kunci Unik Idempotensi Dimensi)
    c1_full_subject_dn   TEXT,               -- Format Rekaman Lengkap: CN=Nama, O=Instansi, C=ID
    c1_valid_from        TEXT,               -- Stempel Waktu Aktivasi Sertifikat Digital
    c1_valid_until       TEXT                -- Stempel Waktu Kedaluwarsa Sertifikat Digital
);

-- =============================================================================
-- [DIMENSION 2] Issuer Entity (C2): Pemetaan Otoritas Penerbit (CA Provider)
-- =============================================================================
CREATE TABLE IF NOT EXISTS esa_dim_issuer_c2 (
    c2_issuer_key              INTEGER PRIMARY KEY AUTOINCREMENT,
    c2_full_distinguished_name TEXT UNIQUE, -- Identitas Lengkap Penerbit (Kunci Unik Idempotensi CA)
    c2_common_name             TEXT,        -- Nama Otoritas Sertifikat (Contoh: eSign CA Class 1)
    c2_organization            TEXT,        -- Induk Organisasi Penerbit (Vendor PSrE)
    c2_country                 TEXT,        -- Kode Negara Penerbit
    c2_sig_algo                TEXT,        -- Algoritma Tanda Tangan Kriptografi (Contoh: RSA/SHA256)
    c2_is_berinduk             INTEGER DEFAULT 1 -- Flag Biner Legalitas Root CA Kominfo (1=Valid, 0=Invalid)
);

-- =============================================================================
-- [DIMENSION 3] Temporal Entity (C3): Granularitas Waktu Akuisisi Data
-- =============================================================================
CREATE TABLE IF NOT EXISTS esa_dim_date_c3 (
    c3_date_key   INTEGER PRIMARY KEY AUTOINCREMENT,
    c3_full_date  TEXT,               -- Format Standar ISO 8601 (YYYY-MM-DD)
    c3_month_name TEXT,               -- String Representasi Nama Bulan (Contoh: June)
    c3_year       INTEGER,            -- Parameter Tahun
    c3_day        INTEGER,            -- Parameter Hari
    c3_hour       INTEGER             -- Parameter Jam (Pemantauan Aktivitas Anomali Waktu Kerja)
);

-- =============================================================================
-- [DIMENSION 4] Corporate Entity (C4): Segmentasi Tenant & CRM Mapping
-- =============================================================================
CREATE TABLE IF NOT EXISTS esa_dim_corporate_c4 (
    c4_corpo_key  INTEGER PRIMARY KEY AUTOINCREMENT,
    c4_corpo_name TEXT UNIQUE,        -- Nomenklatur Legal Perusahaan Pelanggan (Kunci Unik Tenant)
    c4_corpo_code TEXT                -- Kode Unik Identifikasi Perusahaan (Contoh: PER)
);

-- =============================================================================
-- [DIMENSION 5] Integrity Entity (C5): Detail Bukti Fisik & Analisis Heuristik
-- =============================================================================
CREATE TABLE IF NOT EXISTS esa_dim_integrity_c5 (
    c5_integrity_key   INTEGER PRIMARY KEY AUTOINCREMENT,
    c5_status_code     INTEGER,       -- Kode Respon API/HTTP (Contoh: 200)
    c5_status_type     TEXT,          -- Klasifikasi Kepercayaan (Trusted / Not Trusted / Warning)
    c5_integrity_desc  TEXT,          -- Validasi Hash Berkas Fisik (Aggregated Doc Check)
    c5_error_message   TEXT,          -- Ekstraksi Pesan Kesalahan Forensik
    c5_reason          TEXT,          -- Metadata Alasan Penggabungan / Analisis Fraud
    c5_location        TEXT,          -- Metadata Lokasi Geografis (Signature Location)
    c5_local_timestamp TEXT           -- Stempel Waktu Internal Terkunci Pada Dokumen (WIB Format)
);

-- =============================================================================
-- [FACT TABLE] Verifications (F1): Tabel Fakta Sentral & Metrik Kalkulasi
-- =============================================================================
CREATE TABLE IF NOT EXISTS esa_fact_verifications (
    f1_id              INTEGER PRIMARY KEY AUTOINCREMENT,
    f1_doc_id          TEXT,          -- Pengenal Unik Transaksi Dokumen (Unique Doc ID)
    c1_signer_key      INTEGER,       -- Relasi Identitas Penandatangan
    c2_issuer_key      INTEGER,       -- Relasi Otoritas Penerbit
    c3_date_key        INTEGER,       -- Relasi Waktu Transaksi
    c4_corpo_key       INTEGER,       -- Relasi Entitas Perusahaan Tenant
    c5_integrity_key   INTEGER,       -- Relasi Integritas Dokumen
    f1_is_trusted      INTEGER,       -- Metrik Flag Biner Status Keaslian (1=Verified, 0=Failed)
    f1_is_expired      INTEGER,       -- Metrik Flag Biner Kedaluwarsa Sertifikat (1=Expired, 0=Active)
    f1_validity_days   INTEGER,       -- Metrik Hitung Mundur Sisa Hari Aktif Sertifikat
    f1_ltv_status      TEXT,          -- Status Validasi Jangka Panjang (Long Term Validation)
    f1_tsa_status      TEXT,          -- Informasi Layanan Stempel Waktu (Timestamp Authority)
    f1_hash_status     TEXT,          -- Konfirmasi Integritas Nilai Hash Dokumen
    f1_sig_status      TEXT,          -- Konfirmasi Matematis Tanda Tangan Kriptografi
    f1_chain_status    TEXT,          -- Validasi Rantai Kepercayaan (Certificate Chain Trust)
    f1_signing_time    TEXT,          -- Waktu Penandatanganan Aktual (ISO Format String YYYY-MM-DD HH:mm:ss)
    f1_ingested_at     TEXT DEFAULT (datetime('now', '+7 hours')), -- Stempel Waktu Ingesti Data Warehouse (WIB)
    
    -- Definisi Kepatuhan Integritas Referensial (Referential Integrity Constraints)
    FOREIGN KEY (c1_signer_key) REFERENCES esa_dim_signer_c1(c1_signer_key),
    FOREIGN KEY (c2_issuer_key) REFERENCES esa_dim_issuer_c2(c2_issuer_key),
    FOREIGN KEY (c3_date_key) REFERENCES esa_dim_date_c3(c3_date_key),
    FOREIGN KEY (c4_corpo_key) REFERENCES esa_dim_corporate_c4(c4_corpo_key),
    FOREIGN KEY (c5_integrity_key) REFERENCES esa_dim_integrity_c5(c5_integrity_key)
);

-- =============================================================================
-- ⚡ STRATEGI OPTIMASI ANALITIK WAREHOUSE (OLAP PERFORMANCE TUNING)
-- =============================================================================
-- Membuat indeks komposit pada Tabel Fakta untuk mempercepat operasi kueri JOIN 
-- dan penyaringan filter global berdasarkan waktu pada tingkat runtime dashboard.
CREATE INDEX IF NOT EXISTS idx_fact_warehouse_date_lookup 
ON esa_fact_verifications (f1_ingested_at, f1_is_trusted);

CREATE INDEX IF NOT EXISTS idx_fact_foreign_keys_cluster 
ON esa_fact_verifications (c1_signer_key, c2_issuer_key, c3_date_key, c4_corpo_key, c5_integrity_key);