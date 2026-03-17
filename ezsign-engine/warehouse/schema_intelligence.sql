-- ======================================================
-- NAMA TABEL: ESA_STG_PSRE_INTEL
-- FUNGSI: Penampungan data eksternal hasil scraping (W12)
-- KASTA: Staging Area Intelligence (Phase 3)
-- ======================================================

CREATE TABLE IF NOT EXISTS ESA_STG_PSRE_INTEL (
    intel_id           INTEGER PRIMARY KEY AUTOINCREMENT,
    psre_name          TEXT NOT NULL,          -- Contoh: Peruri, Privy, Vida
    site_url           TEXT,                   -- URL sumber data
    intel_type         TEXT,                   -- CRL_LINK, OCSP_URL, atau CERT_FILE
    intel_value        TEXT,                   -- Hasil scrap (misal link download file)
    security_policy    TEXT,                   -- Status robots.txt (Allow/Disallow/AI-train=no)
    file_extension     TEXT,                   -- .crl, .cer, .crt
    scrape_timestamp   DATETIME DEFAULT CURRENT_TIMESTAMP, -- Waktu pengambilan data
    notes              TEXT                    -- Info tambahan teknis (misal: "Xpath selection")
);

-- Indexing biar query analitik kenceng kasta dewa di Fase 3
CREATE INDEX IF NOT EXISTS idx_psre_name ON ESA_STG_PSRE_INTEL (psre_name);
CREATE INDEX IF NOT EXISTS idx_intel_type ON ESA_STG_PSRE_INTEL (intel_type);