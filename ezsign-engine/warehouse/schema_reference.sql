-- =============================================================================
-- 🛡️ MODULE: BUSINESS POLICY & REFERENCE LAYER (INTELLIGENCE)
-- =============================================================================
-- Berisi tabel referensi untuk aturan bisnis, kebijakan kepatuhan, dan whitelist
-- =============================================================================

CREATE TABLE IF NOT EXISTS esa_ref_psre_whitelist (
    psre_name TEXT PRIMARY KEY,
    is_active INTEGER DEFAULT 1
);

INSERT OR IGNORE INTO esa_ref_psre_whitelist (psre_name) VALUES 
('BSRE'), ('BSSN'), ('PERURI'), ('PRIVY'), ('VIDA'), ('TILAKA'), ('DIGISIGN'), ('EZSIGN');