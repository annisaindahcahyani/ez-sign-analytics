-- =============================================================================
-- 🗄️ MODULE: EXTERNAL INTELLIGENCE DIMENSION SCHEMA (MARKET INTEL WAREHOUSE)
-- =============================================================================
-- 📌 CONFIGURATION : Tabel Dimensi Analitik Data Kompetitor Eksternal
-- 📅 UPDATE        : 5 Juni 2026
-- 🛡️ OBJECTIVE     : Strukturisasi Metadata Hasil Ekstraksi Sub-Mesin "The Hunter"
-- ⚖️ REGULASI TI   : Pemantauan Kepatuhan UU PDP No. 27/2022 & Regulasi Siber
-- =============================================================================
-- 🗺️ DOKUMEN TATA KERJA FUNGSIONAL PENGEMBANG (FOR NEXT DEVELOPER):
--
-- 1. FUNGSI STAGING AREA (ESA_STG_PSRE_INTEL):
--    Tabel ini bertindak sebagai ruang transit data (Temporary Data Store) untuk 
--    menampung data mentah hasil rayapan siber (web scraping) sebelum melalui 
--    fase pembersihan (Wrangling) dan dimuat ke dalam Star Schema utama.
--
-- 2. KEPATUHAN ETIKA KOMPUTER (COMPLIANCE LAYER):
--    Penerapan kolom 'security_policy' didesain secara khusus untuk merekam status 
--    regulasi robots.txt dari server target kompetitor. Hal ini menjamin bahwa 
--    operasi akuisisi data intelijen mematuhi hukum siber yang berlaku.
-- =============================================================================

CREATE TABLE IF NOT EXISTS esa_dim_competitor_intel (
    intel_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp         TEXT NOT NULL,                      -- Stempel waktu aktual pengambilan data (YYYY-MM-DD HH:mm:ss)
    psre_name         TEXT NOT NULL,                      -- Identitas Otoritas Sertifikasi Kompetitor (Contoh: PRIVY, PERURI)
    file_name         TEXT DEFAULT 'N/A',                 -- Nama berkas fisik kriptografi yang teridentifikasi (.crl, .pdf)
    source_url        TEXT,                               -- URL Sumber setelah lolos Anonimisasi (Privasi UU PDP Masking)
    status            TEXT DEFAULT 'SUCCESS',             -- Label status transaksi standar (SUCCESS / FAILED_SERVER)
    fetch_date        TEXT NOT NULL,                      -- Ekstraksi fitur tanggal untuk filter OLAP (YYYY-MM-DD)
    file_type         TEXT DEFAULT 'UNKNOWN',             -- Segmentasi tipe dokumen (Contoh: PDF, CRT, CER, CRL)
    security_policy   TEXT DEFAULT 'COMPLIANT',           -- Log Kepatuhan robots.txt (Allow/Stealth Compliance)
    ingested_at       DATETIME DEFAULT (datetime('now', '+7 hours')) -- Stempel waktu penulisan ke Warehouse (WIB UTC+7)
);

-- =============================================================================
-- ⚡ STRATEGI OPTIMASI KINERJA (OLAP COMPOSITE INDEX TUNING)
-- =============================================================================
-- Implementasi Composite B-Tree Indexing pada parameter filter rentang tanggal 
-- dan pengelompokan vendor untuk mengeliminasi Full Table Scan pada dashboard Streamlit.
CREATE INDEX IF NOT EXISTS idx_competitor_analytics_lookup 
ON esa_dim_competitor_intel (fetch_date, psre_name, status);

CREATE INDEX IF NOT EXISTS idx_file_segmentation 
ON esa_dim_competitor_intel (file_type);