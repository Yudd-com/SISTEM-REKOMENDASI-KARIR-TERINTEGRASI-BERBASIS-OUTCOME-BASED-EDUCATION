# 🎓 OBE Career & Course Recommender System

Sistem Rekomendasi Karir dan Kursus Online Terintegrasi Berbasis **Outcome-Based Education (OBE)**, **Knowledge Graph (Neo4j)**, dan **Relative Skill Gap (RSG) Analysis**.

Proyek Riset Magang — Badan Riset dan Inovasi Nasional (BRIN).

---

## 📌 Ringkasan Proyek

Sistem ini dirancang untuk menjembatani kesenjangan kompetensi (*skill gap*) antara lulusan perguruan tinggi dengan standar kebutuhan industri kerja secara objektif dan terpersonalisasi.

* **Multi-Kampus:** 300 Mahasiswa Terpadu (100 ITS Surabaya, 100 Telkom University Jakarta, 100 Telkom University Surabaya).
* **Standar Industri:** 496 Posisi Karir Industri (5.505 persyaratan kompetensi).
* **Katalog Pembelajaran:** 8.207 Kursus Online Master (Coursera).
* **Knowledge Graph:** 159.298 Total Relasi (`HAS_SKILL`, `REQUIRES`, `TEACHES`).
* **Algoritma Gap:** *Relative Skill Gap (RSG)* dengan perangkingan karir Top-5 & rekomendasi kursus bertahap (*Beginner $\rightarrow$ Advanced*).

---

## 📂 Struktur Direktori

```text
final_project/
├── app.py                      # Aplikasi Utama Streamlit (Port 8502)
├── app1.py                     # Aplikasi Eksperimen + Nilai Mahasiswa (Port 8503)
├── run_app.bat                 # Script batch cepat untuk menjalankan app.py
├── run_app1.bat                # Script batch cepat untuk menjalankan app1.py
├── run_both.bat                # Script batch untuk menjalankan kedua aplikasi
├── src/
│   └── kg/                     # Pipeline Knowledge Graph & Rekomendasi
│       ├── config.py           # Konfigurasi parameter & threshold
│       ├── graph_importer.py   # Skrip import Neo4j Cypher
│       ├── gap_analyzer.py     # Perhitungan Matched & Missing Skills
│       ├── career_ranker.py    # Perangkingan Karir berbasis RSG
│       └── course_recommender.py # Rekomendasi kursus bertahap
├── data_clean/                 # Dataset kurikulum & profil bersih
├── output/                     # Hasil normalisasi & perangkingan akhir
└── requirements.txt            # Dependensi pustaka Python
```

---

## Cara Menjalankan Aplikasi

1. **Clone repository:**
   ```bash
   git clone <URL_REPOSITORY_ANDA>
   cd final_project
   ```

2. **Install dependensi:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Jalankan aplikasi Streamlit:**
   ```bash
   # Aplikasi Utama
   python -m streamlit run app.py --server.port 8502
`
