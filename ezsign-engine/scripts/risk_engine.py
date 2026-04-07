#=============================================================================
#🧠 MODULE: EZSIGN FRAUD DETECTION & RISK ENGINE (THE ANALYTICS CORE)
#=============================================================================
#TUGAS UTAMA:
#1. Multi-Attribute Scoring: Menghitung skor risiko berdasarkan 3 kriteria utama:
#   (C1) Frekuensi, (C2) Jendela Waktu, dan (C3) Perubahan Lokasi.
#2. Normalisasi Data: Mengubah data mentah (jam/jumlah) menjadi skala 0.0 - 1.0 
#   agar bisa dihitung secara matematis.
#3. MADM Algorithm (SAW vs WP): Implementasi dua metode pengambilan keputusan 
#   untuk akurasi deteksi anomali yang lebih tajam.

#ALASAN TEKNIS:
#- Menggunakan NumPy untuk operasi vektor/matriks (Dot Product) agar proses 
#  perhitungan batch super cepat (Scalable).
#- Metode WP (Weighted Product) ditambahkan karena lebih sensitif terhadap 
#  kegagalan di satu kriteria fatal dibandingkan SAW (Simple Additive Weighting).
#=============================================================================

import numpy as np
from datetime import datetime

class EzSignRiskEngine:
    def __init__(self):
        # [W11] DEFINISI BOBOT KRITERIA (Weights)
        # Total bobot harus = 1.0 (Normalization Requirement)
        # C1: Frequency (0.4), C2: Time Window (0.2), C3: Location Change (0.4)
        self.weights = np.array([0.4, 0.2, 0.4])
        print("[*] Risk Engine Initialized: Multi-Attribute Logic Ready 💅")

    def _normalize_frequency(self, freq):
        """
        [STEP 1] NORMALISASI FREKUENSI (C1)
        Mengubah jumlah transaksi menjadi nilai risiko 0.2 - 1.0.
        """
        if freq > 50: return 1.0  # Status: Critical Fraud Indication
        if freq > 20: return 0.6  # Status: High Activity Warning
        return 0.2                # Status: Normal Activity

    def _normalize_time(self, hour):
        """
        [STEP 2] NORMALISASI WAKTU (C2)
        Mendeteksi 'Jam Kalong' (23:00 - 04:00) sebagai jam risiko tinggi 
        karena biasanya transaksi otomatis/bot terjadi di jam ini.
        """
        if 23 <= hour or hour <= 4: return 1.0 # High Risk (Out of Office Hours)
        return 0.1                             # Low Risk (Working Hours)

    def calculate_single_risk(self, freq, hour, loc_change):
        """
        [SCENARIO A] SINGLE TRANSACTION CALCULATION
        Menghitung skor risiko untuk satu baris data (Real-time Detection).
        Menggunakan operasi Dot Product (Linear Addition).
        """
        f_score = self._normalize_frequency(freq)
        t_score = self._normalize_time(hour)
        l_score = 1.0 if loc_change else 0.0

        # Vector Calculation
        matrix = np.array([f_score, t_score, l_score])
        final_score = np.dot(matrix, self.weights)
        return round(final_score, 2)

    def calculate_saw_batch(self, data_matrix):
        """
        [SCENARIO B] SAW METHOD (Simple Additive Weighting)
        Metode kompensatoris: Nilai rendah di satu kriteria bisa ditutupi 
        oleh nilai tinggi di kriteria lain. Cocok sebagai baseline.
        Rumus: V = Σ (w_j * r_ij)
        """
        # Matmul = Matrix Multiplication (Perkalian Matriks Terbobot)
        scores = np.matmul(data_matrix, self.weights)
        return np.round(scores, 2)

    def calculate_wp_batch(self, data_matrix):
        """
        [SCENARIO C] WP METHOD (Weighted Product)
        Metode non-kompensatoris: Memberikan penalti berat jika ada satu kriteria 
        yang nilainya sangat buruk. Lebih akurat untuk deteksi Fraud Ekstrem.
        Rumus: V = Π (x_ij ^ w_j)
        """
        # Handling nilai 0 agar tidak merusak operasi perkalian pangkat
        data_matrix = np.where(data_matrix == 0, 0.01, data_matrix)
        
        # Powering & Product across axis (Baris)
        weighted_powers = np.power(data_matrix, self.weights)
        scores = np.prod(weighted_powers, axis=1)
        return np.round(scores, 2)

    def get_risk_status(self, score):
        """
        THRESHOLD LOGIC: Klasifikasi hasil akhir untuk kebutuhan Dashboard/Alert.
        """
        if score >= 0.7: return "CRITICAL (Immediate Action Required) 🚨"
        if score >= 0.4: return "WARNING (Needs Review) ⚠️"
        return "SAFE (Normal Activity) ✅"

# =================================================================
# 🧪 UNIT TESTING & PLAYGROUND
# =================================================================
if __name__ == "__main__":
    engine = EzSignRiskEngine()

    print("\n" + "="*50)
    print("🚀 TESTING SINGLE TRANSACTION LOGIC (W8)")
    print("="*50)
    # Simulasi: Aktivitas masif di jam 2 pagi dengan perubahan lokasi
    s_freq, s_hour, s_loc = 60, 2, True
    score_single = engine.calculate_single_risk(s_freq, s_hour, s_loc)
    print(f"Input: Freq={s_freq}, Hour={s_hour}, LocChange={s_loc}")
    print(f"Final Score: {score_single} -> {engine.get_risk_status(score_single)}")

    print("\n" + "="*50)
    print("🚀 BATCH OPTIMIZATION: SAW vs WP COMPARISON (W11)")
    print("="*50)
    
    # Test Matrix: [Freq_Score, Time_Score, Loc_Score]
    test_matrix = np.array([
        [0.2, 0.1, 0.1], # Case 1: Sangat Aman (Daily User)
        [0.2, 1.0, 0.1], # Case 2: Anomali Waktu (Mungkin lembur, mungkin fraud)
        [1.0, 1.0, 1.0]  # Case 3: Full Anomali (Confirm Fraud)
    ])
    
    saw_results = engine.calculate_saw_batch(test_matrix)
    wp_results = engine.calculate_wp_batch(test_matrix)

    for i in range(len(test_matrix)):
        print(f"Data Transaksi ke-{i+1}:")
        print(f"  > SAW Score: {saw_results[i]} ({engine.get_risk_status(saw_results[i])})")
        print(f"  > WP Score : {wp_results[i]} ({engine.get_risk_status(wp_results[i])})")
        print("-" * 35)

    print("\n[*] STRATEGY NOTE: WP Method digunakan sebagai validasi ketat.")
    print("[*] STATUS: RISK ENGINE LOGIC V2.0 IS STABLE. SLAY! 💅🔥")