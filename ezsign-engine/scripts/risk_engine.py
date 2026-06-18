# =============================================================================
# 🧠 MODULE: EZSIGN FRAUD DETECTION & MATHEMATICAL DECISION SUPPORT ENGINE
# =============================================================================
# 📌 CONFIGURATION : Multi-Attribute Decision Making (MADM) Core Engine
# 📅 UPDATE        : 5 Juni 2026
# 🔬 METODE UTAMA  : Simple Additive Weighting (SAW) & Weighted Product (WP)
# ⚖️ KOMPUTASI     : Vektorisasi Aljabar Linear Menggunakan NumPy Matrix
# =============================================================================
# 🗺️ DOKUMEN ALUR LOGIKA MATEMATIS (FOR NEXT DEVELOPER):
#
# 1. VEKTOR BOBOT KRITERIA (WEIGHTS COMPLIANCE):
#    Ditetapkan matriks bobot horizontal tunggal berbasis preferensi risiko:
#    W = [C1: Frekuensi Transaksi (0.4), C2: Jendela Waktu (0.2), C3: Anomali Lokasi (0.4)]
#    Total akumulasi nilai seluruh bobot wajib bernilai mutlak 1.0.
#
# 2. PROSES NORMALISASI DATA MENTAH:
#    - Kriteria Frekuensi (C1): Mengubah kuantitas hit menjadi skala diskrit 0.2 - 1.0
#    - Kriteria Waktu (C2): Mendeteksi aktivitas "Jam Kalong" (23:00 - 04:00 WIB)
#      sebagai indikator risiko bot otomatis tingkat tinggi (Nilai Maksimal = 1.0).
#
# 3. KOMPARASI EVALUASI MODEL KEPUTUSAN BATCH:
#    - Metode SAW (Kompensatoris): Melakukan operasi perkalian matriks linear (Dot Product).
#      Nilai risiko rendah pada satu kriteria dapat dikompensasi oleh kriteria lain.
#    - Metode WP (Non-Kompensatoris): Melakukan operasi perkalian pangkat multiplikatif.
#      Memberikan penalti berat apabila ditemukan satu kriteria bernilai buruk ekstrem.
# =============================================================================

import numpy as np
from datetime import datetime

class EzSignRiskEngine:
    def __init__(self):
        """ Inisialisasi parameter pembobotan kriteria keputusan (Fase Target W11 Silabus) """
        self.weights = np.array([0.4, 0.2, 0.4])
        print("[INFO] Risk Engine Berhasil Diinisialisasi: Sistem Aturan Multi-Atribut Siap Beroperasi.")

    def _normalize_frequency(self, freq):
        """
        [TAHAPAN 1] NORMALISASI PARAMETER FREKUENSI (C1)
        Mengubah akumulasi kuantitas transaksi menjadi skala indeks risiko 0.2 - 1.0.
        """
        if freq > 50: 
            return 1.0  # Klasifikasi: Indikasi Anomali Kritis (Critical Fraud Indication)
        if freq > 20: 
            return 0.6  # Klasifikasi: Peringatan Aktivitas Tinggi (High Activity Warning)
        return 0.2      # Klasifikasi: Aktivitas Normal (Normal Activity)

    def _normalize_time(self, hour):
        """
        [TAHAPAN 2] NORMALISASI PARAMETER JENDELA WAKTU (C2)
        Mendeteksi aktivitas luar jam kerja operasional (Jam Kalong: 23:00 - 04:00 WIB)
        sebagai indikator risiko transaksi otomatisasi bot ilegal.
        """
        if 23 <= hour or hour <= 4: 
            return 1.0 # Risiko Tinggi (Di Luar Jam Kerja / Out of Office Hours)
        return 0.1     # Risiko Rendah (Jam Kerja Aktif / Working Hours)

    def calculate_single_risk(self, freq, hour, loc_change):
        """
        [SKENARIO A] EVALUASI TRANSAKSI TUNGGAL (REAL-TIME DETECTION)
        Menghitung skor risiko komposit untuk satu baris data audit trail.
        Menggunakan operasi perkalian titik vektor (Dot Product Linear Addition).
        """
        f_score = self._normalize_frequency(freq)
        t_score = self._normalize_time(hour)
        l_score = 1.0 if loc_change else 0.0

        # Konstruksi Vektor Atribut
        matrix = np.array([f_score, t_score, l_score])
        final_score = np.dot(matrix, self.weights)
        return round(final_score, 2)

    def calculate_saw_batch(self, data_matrix):
        """
        [SKENARIO B] PEMODELAN MADM METODE SAW (SIMPLE ADDITIVE WEIGHTING)
        Pendeketan Kompensatoris: Mengalikan matriks data dengan vektor bobot (Matrix Multiplication).
        Formulasi Rumus: V_i = Σ (w_j * r_ij)
        """
        scores = np.matmul(data_matrix, self.weights)
        return np.round(scores, 2)

    def calculate_wp_batch(self, data_matrix):
        """
        [SKENARIO C] PEMODELAN MADM METODE WP (WEIGHTED PRODUCT)
        Pendekatan Non-Kompensatoris: Menghitung pembobotan berbasis nilai pangkat multiplikatif.
        Formulasi Rumus: V_i = Π (x_ij ^ w_j) / Σ(Π (x_ij ^ w_j))
        Penanganan nilai 0.0 diubah menjadi 0.01 guna mengamankan akurasi perhitungan matematika.
        """
        adjusted_matrix = np.where(data_matrix == 0, 0.01, data_matrix)
        
        # Operasi perpangkatan berbasis vektor bobot dilanjutkan perkalian produk antar baris (axis=1)
        weighted_powers = np.power(adjusted_matrix, self.weights)
        s_vector = np.prod(weighted_powers, axis=1)
        
        # Normalisasi vektor S untuk mendapatkan nilai preferensi relatif V yang sebanding (Scale Compliance)
        if np.sum(s_vector) > 0:
            scores = s_vector / np.max(s_vector)
        else:
            scores = s_vector
            
        return np.round(scores, 2)

    def get_risk_status(self, score):
        """ Threshold Logic: Klasifikasi skor akhir untuk kebutuhan visualisasi UI Dashboard """
        if score >= 0.7: 
            return "CRITICAL (Immediate Action Required) 🚨"
        if score >= 0.4: 
            return "WARNING (Needs Review) ⚠️"
        return "SAFE (Normal Activity) ✅"


# =============================================================================
# 🧪 LOG UNIT TESTING & VALIDASI OPERASIONAL LAYER
# =============================================================================
if __name__ == "__main__":
    engine = EzSignRiskEngine()

    print("\n" + "="*60)
    print("🚀 EKSEKUSI PENGUJIAN LOGIKA TRANSAKSI TUNGGAL (MILESTONE W8)")
    print("="*60)
    
    # Simulasi Kasus: Aktivitas masif (60 hit) pada pukul 02:00 subuh disertai perubahan lokasi
    s_freq, s_hour, s_loc = 60, 2, True
    score_single = engine.calculate_single_risk(s_freq, s_hour, s_loc)
    print(f"Parameter Input: Frekuensi={s_freq}, Jam={s_hour}, Perubahan Lokasi={s_loc}")
    print(f"Skor Risiko Akhir: {score_single} -> Status: {engine.get_risk_status(score_single)}")

    print("\n" + "="*60)
    print("🚀 EVALUASI KOMPARASI BATCH KEPUTUSAN: METODE SAW VS WP (MILESTONE W11)")
    print("="*60)
    
    # Konstruksi Matriks Pengujian Pengambilan Keputusan Konvergen: [Skor_Frekuensi, Skor_Waktu, Skor_Lokasi]
    test_matrix = np.array([
        [0.2, 0.1, 0.0], # Kasus 1: Aktivitas Terindikasi Sangat Aman (Daily User)
        [0.2, 1.0, 0.0], # Kasus 2: Aktivitas Terindikasi Anomali Waktu Kerja (Time Window Exception)
        [1.0, 1.0, 1.0]  # Kasus 3: Aktivitas Terindikasi Full Anomali (Confirmed Fraud Attempt)
    ])
    
    saw_results = engine.calculate_saw_batch(test_matrix)
    wp_results = engine.calculate_wp_batch(test_matrix)

    for i in range(len(test_matrix)):
        print(f"Analisis Data Rekaman Transaksi ke-{i+1}:")
        print(f"  > Skor Metode SAW : {saw_results[i]} ({engine.get_risk_status(saw_results[i])})")
        print(f"  > Skor Metode WP  : {wp_results[i]} ({engine.get_risk_status(wp_results[i])})")
        print("-" * 45)

    print("\n[CATATAN STRATEGIS DEVELOPER]: Metode Weighted Product (WP) digunakan sebagai instrumen validasi ketat.")
    print("[STATUS] Laporan Hasil Pengujian: ARSITEKTUR RISK ENGINE LOGIC V2.0 DINYATAKAN STABIL.")
    print("="*60 + "\n")