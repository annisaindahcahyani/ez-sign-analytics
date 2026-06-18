# EzSign Analytics Dashboard 🛡️
**Sistem Analitik Forensik dan Integritas Dokumen Digital Real-Time**

## 📋 Deskripsi Proyek
EzSign Analytics adalah platform *Data Warehouse* berbasis arsitektur **Star Schema** yang berfungsi untuk membedah forensik dokumen bertanda tangan elektronik (TTE). Sistem ini dirancang guna memfasilitasi audit integritas dokumen, ekstraksi metadata kriptografi, serta analisis intelijen pasar sektor PSrE secara sistematis.

## 🛠️ Arsitektur Sistem
Proyek ini mengimplementasikan arsitektur *Decoupled Microservices*:
1. **Frontend/Gateway:** Next.js API Route dengan implementasi **sql.js (WebAssembly)** untuk manajemen persistensi data berbasis SQLite.
2. **Backend Engine:** Python FastAPI (**api.py**) sebagai *processing core* untuk ekstraksi biner dan otomatisasi ETL.
3. **Analytics Dashboard:** Streamlit untuk visualisasi data (OLAP) dan monitoring performa.
4. **Data Store:** SQLite sebagai *Single Source of Truth* (SSoT).

## 🚀 Instalasi & Deployment

### Prasyarat
- Docker & Docker Compose
- Python 3.11+

### Konfigurasi
1. Salin konfigurasi lingkungan:
   ```bash
   cp .env.example .env

```

2. Sesuaikan variabel `CORPORATE_CODE` dan `DATABASE_PATH` pada berkas `.env` sesuai dengan konfigurasi volume Docker.

### Menjalankan Layanan

Gunakan perintah berikut pada direktori root untuk memulai orkestrasi layanan:

```bash
docker-compose up --build

```

* **Dashboard:** Dapat diakses pada port `8501`.
* **API Gateway:** Beroperasi pada port `8000`.

## 🔄 Pipeline Orchestration

Sistem memanfaatkan **Selenium Headless Browser** untuk akuisisi data pasar intelijen serta mengintegrasikan **FastAPI (main.py)** sebagai *trigger* utama untuk alur transformasi data.

1. **Data Wrangling (Transformation Engine)**
Proses transformasi dari *Staging* ke *Warehouse* dikelola oleh *Watchdog Service*. Setiap kali berkas masuk ke `/data/staging`, sistem akan memicu `api.py` untuk mengalirkan data ke pipa transformasi.
* **Audit Manual:** Jalankan perintah di dalam kontainer untuk sinkronisasi paksa:
```bash
docker exec -it ezsign_analytics_engine python scripts/wrangling_engine.py

```




2. **Scraping & Data Acquisition**
Sistem melakukan akuisisi data intelijen kompetitor secara periodik menggunakan *Selenium Headless Browser*. Log aktivitas ETL dapat dipantau melalui perintah:
```bash
docker logs -f ezsign_analytics_engine

```



## 📁 Struktur Direktori

```text
├── data/               # Persistent Storage (SQLite & Staging Vault)
│   ├── config/         # DDL SQL Schema (Warehouse & Staging Schema)
│   └── staging/        # Tempat transit berkas fisik (.pdf, .json, .csv)
├── ezsign-engine/      # Backend Core Engine & Scripts
│   ├── dashboard/      # Antarmuka Streamlit OLAP
│   ├── scripts/        # Core Scripts (Extraction, Purging, Scraping)
│   └── utils/          # Data Bridge & Cleansing Utilities
├── ezsign-frontend/    # Ingestion Gateway (Next.js)
├── docker-compose.yml  # Service Orchestrator
└── README.md           # Dokumentasi Sistem

```

## ⚖️ Kepatuhan & Keamanan

* **UU PDP Compliance:** Implementasi modul *Automated Data Purging* dilakukan untuk memastikan dokumen residu di folder staging dihapus dalam 1 jam sesuai prinsip *Data Minimization*.
* **Security:** Seluruh akses API dikelola melalui kebijakan CORS yang terverifikasi dan validasi struktur *payload* untuk mitigasi *injection attacks*.

## 👨‍💻 Kontributor (Squad DPR)

Sistem ini dirancang dan dibangun oleh tim *Data Engineer Intern* dari Program Studi Sistem Informasi UPN "Veteran" Jawa Timur Angkatan 2023:

* **Karina Catur Febriantika**
* **Annisa Indah Cahyani**
* **Debita Faulirisma Garcia**
* **Zikhaila Diva Priamita**

---

*Proyek ini merupakan bagian dari inisiatif pengembangan sistem analitik forensik pada PT Solusi Identitas Global Net.*

*Built with passion, logic, and Stoic mindset (Amor Fati & Ikigai).*