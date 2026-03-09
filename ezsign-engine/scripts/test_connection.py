import sqlite3
import os

# Path ini berarti: naik satu level (..), masuk ke data, cari database.sqlite
db_path = os.path.join('..', 'data', 'database.sqlite')

def check_connection():
    print(f"🔍 Mencoba menyambung ke: {os.path.abspath(db_path)}")
    
    if not os.path.exists(db_path):
        print("❌ ERROR: File database.sqlite GAK KETEMU! Cek folder data/ ya Ca!")
        return

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Cek apakah tabel dim_issuer udah ada isinya
        cursor.execute("SELECT issuer_name FROM dim_issuer")
        rows = cursor.fetchall()
        
        print("\n✅ KONEKSI BERHASIL, SLAY! ✨")
        print(f"📦 Daftar Issuer di Database: {[row[0] for row in rows]}")
        
        conn.close()
    except Exception as e:
        print(f"❌ WADUH ERROR: {e}")

if __name__ == "__main__":
    check_connection()