import numpy as np
from datetime import datetime

class EzSignRiskEngine:
    def __init__(self):
        # [W11] Definisi Bobot Kriteria (Total harus 1.0 biar Slay!)
        # C1: Frequency, C2: Time Window, C3: Location Change
        self.weights = np.array([0.4, 0.2, 0.4])
        print("[*] Risk Engine Initialized: Multi-Attribute Logic Ready 💅")

    def _normalize_frequency(self, freq):
        """[W8] Normalisasi frekuensi ke skala 0-1"""
        if freq > 50: return 1.0  # Critical
        if freq > 20: return 0.6  # Medium
        return 0.2               # Low

    def _normalize_time(self, hour):
        """[W8] Normalisasi jam transaksi ke skala 0-1"""
        # Jam kalong (23:00 - 04:00) dianggap risiko tinggi
        if 23 <= hour or hour <= 4: return 1.0
        return 0.1

    def calculate_single_risk(self, freq, hour, loc_change):
        """
        [W8] Menghitung skor risiko untuk satu transaksi rill (Fungsi Dasar)
        """
        f_score = self._normalize_frequency(freq)
        t_score = self._normalize_time(hour)
        l_score = 1.0 if loc_change else 0.0

        # Menggunakan Dot Product untuk perhitungan linear sederhana
        matrix = np.array([f_score, t_score, l_score])
        final_score = np.dot(matrix, self.weights)
        return round(final_score, 2)

    def calculate_saw_batch(self, data_matrix):
        """
        [W11] Simple Additive Weighting (SAW) - Batch Processing
        Metode penjumlahan terbobot linear.
        """
        # Rumus: Skor = jumlah dari (nilai * bobot)
        scores = np.matmul(data_matrix, self.weights)
        return np.round(scores, 2)

    def calculate_wp_batch(self, data_matrix):
        """
        [W11] Weighted Product (WP) - Optimization & Validation
        Metode perkalian pangkat bobot (lebih sensitif terhadap anomali).
        """
        # Rumus: Skor = kali dari (nilai ^ bobot)
        # Catatan: Nilai 0 diubah ke 0.01 agar tidak merusak perkalian
        data_matrix = np.where(data_matrix == 0, 0.01, data_matrix)
        weighted_powers = np.power(data_matrix, self.weights)
        scores = np.prod(weighted_powers, axis=1)
        return np.round(scores, 2)

    def get_risk_status(self, score):
        """Kategorisasi status risiko berdasarkan skor akhir"""
        if score >= 0.7: return "CRITICAL (Immediate Action Required) 🚨"
        if score >= 0.4: return "WARNING (Needs Review) ⚠️"
        return "SAFE (Normal Activity) ✅"

# --- [PLAYGROUND / TESTING UNIT - PRE-HOLIDAY START] ---
if __name__ == "__main__":
    engine = EzSignRiskEngine()

    print("\n" + "="*50)
    print("TEST SINGLE TRANSACTION LOGIC (W8)")
    print("="*50)
    # Simulasi: User sangat aktif di jam 2 pagi dari lokasi berbeda
    s_freq, s_hour, s_loc = 60, 2, True
    score_single = engine.calculate_single_risk(s_freq, s_hour, s_loc)
    print(f"Input: Freq={s_freq}, Hour={s_hour}, LocChange={s_loc}")
    print(f"Final Score: {score_single} -> {engine.get_risk_status(score_single)}")

    print("\n" + "="*50)
    print("BATCH OPTIMIZATION: SAW vs WP (W11)")
    print("="*50)
    # Matrix: [Freq_Score, Time_Score, Loc_Score]
    # Row 1: Transaksi Sangat Aman
    # Row 2: Anomali di Jam (WP akan lebih sensitif di sini)
    # Row 3: Full Anomali / Fraud
    test_matrix = np.array([
        [0.2, 0.1, 0.1],
        [0.2, 1.0, 0.1],
        [1.0, 1.0, 1.0]
    ])
    
    saw_results = engine.calculate_saw_batch(test_matrix)
    wp_results = engine.calculate_wp_batch(test_matrix)

    for i in range(len(test_matrix)):
        print(f"Data ke-{i+1}:")
        print(f"  > SAW Method Score: {saw_results[i]} ({engine.get_risk_status(saw_results[i])})")
        print(f"  > WP Method Score : {wp_results[i]} ({engine.get_risk_status(wp_results[i])})")
        print("-" * 30)

    print("\n[*] Optimization Note: SAW digunakan sebagai baseline, WP sebagai validasi silang.")
    print("[*] Status: ALL PHASE 2 ENGINE LOGIC IS READY TO DEPLOY. SLAY! 💅")