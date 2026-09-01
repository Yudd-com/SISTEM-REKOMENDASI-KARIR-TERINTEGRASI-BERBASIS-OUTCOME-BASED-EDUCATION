"""
generate_dummy_students.py
==========================
Script untuk menghasilkan dataset dummy 100 mahasiswa (DATA_MAHASISWA_DUMMY_100.xlsx)
berdasarkan gabungan kurikulum dan skill dari 3 sumber:
1. ITS: RPS_skill_extracted_20260809_185306.csv (subset source == 'ITS')
2. Telkom University Jakarta: data/OBE_JAKARTA.xlsx (Referensi_CLO)
3. Telkom University Surabaya: data/OBE_SURABAYA.xlsx (Referensi_CLO)

Format Output:
- File: DATA_MAHASISWA_DUMMY_100.xlsx
- Sheet 1: Daftar_Mahasiswa (id_student, nama_mahasiswa, angkatan)
- Sheet 2: Nilai_Mahasiswa_per_CLO (id_student, id_CLO, score)
- Sheet 3: input_mahasiswa (Student, CLO, Skill, Score)

Ketentuan Khusus:
- Tepat 100 mahasiswa (M0001 - M0100)
- Score STRICTLY >= 40.01 dan <= 100.00
- Konsistensi 100% antara Sheet 2 dan Sheet 3
- Profil kemampuan dan variasi skill mahasiswa heterogen
"""

import os
import random
import unicodedata
import re
from pathlib import Path
import numpy as np
import pandas as pd

CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
DATA_DIR = PROJECT_ROOT / "data"
PEMPROSESAN_DATA_DIR = PROJECT_ROOT / "Pemprosesan Data"

FILE_RPS_CSV = PEMPROSESAN_DATA_DIR / "Ekstraksi Skill" / "RPS_skill_extracted_20260809_185306.csv"
FILE_OBE_JKT = DATA_DIR / "OBE_JAKARTA.xlsx"
FILE_OBE_SBY = DATA_DIR / "OBE_SURABAYA.xlsx"

OUTPUT_XLSX_PRIMARY = CURRENT_DIR / "DATA_MAHASISWA_DUMMY_100.xlsx"
OUTPUT_XLSX_DATA = DATA_DIR / "DATA_MAHASISWA_DUMMY_100.xlsx"
OUTPUT_REPORT = CURRENT_DIR / "laporan_data_mahasiswa_dummy.md"

# Seed untuk reproducibility
RANDOM_SEED = 42
random.seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)

# Daftar 100 Nama Mahasiswa Sintetis Realistis (Fiktif)
FIRST_NAMES = [
    "Aditya", "Agung", "Ahmad", "Aji", "Aldi", "Alif", "Amalia", "Ananda", "Andi", "Angga",
    "Annisa", "Ari", "Arif", "Aulia", "Bagas", "Bagus", "Bayu", "Bima", "Budi", "Cahya",
    "Citra", "Danang", "Deni", "Dewi", "Dhika", "Dimas", "Dina", "Dwi", "Eka", "Fadhil",
    "Fajar", "Farhan", "Fathur", "Febri", "Fikri", "Galang", "Genta", "Gilang", "Gita", "Hafiz",
    "Hamzah", "Hana", "Handoko", "Hardi", "Hasan", "Hendro", "Heru", "Hidayat", "Ilham", "Indah",
    "Indra", "Iqbal", "Irfan", "Kartika", "Kharisma", "Kiki", "Kurnia", "Kusuma", "Laila", "Laras",
    "Lucky", "Mahendra", "Mega", "Melati", "Muhammad", "Nabila", "Nanda", "Naufal", "Novi", "Nur",
    "Pandu", "Prasetyo", "Pratama", "Putra", "Putri", "Rafi", "Rahma", "Rahmat", "Raka", "Rama",
    "Rangga", "Reza", "Rian", "Riko", "Rina", "Rini", "Rizki", "Rizky", "Roni", "Safira",
    "Salma", "Sandi", "Saputra", "Satria", "Setiawan", "Siti", "Surya", "Syahrul", "Taufik", "Tri"
]

LAST_NAMES = [
    "Pratama", "Saputra", "Kusuma", "Wijaya", "Nugroho", "Hidayat", "Santoso", "Wibowo", "Permana", "Lestari",
    "Ramadhan", "Firmansyah", "Gunawan", "Utomo", "Kurniawan", "Syahputra", "Purnama", "Subagja", "Wahyudi", "Nugraha",
    "Pangestu", "Setiawan", "Maulana", "Arifin", "Saputro", "Handoko", "Sudrajat", "Yuliana", "Astuti", "Anggraini",
    "Hartanto", "Prasetya", "Suhartono", "Suhendra", "Wicaksono", "Budiman", "Susanto", "Kurnia", "Pambudi", "Suryono",
    "Triatmojo", "Adriansyah", "Fauzi", "Hakim", "Iskandar", "Nasution", "Siregar", "Lubis", "Batubara", "Harahap"
]


def generate_synthetic_names(n=100) -> list[str]:
    """Menghasilkan n nama mahasiswa sintetis yang unik dan realistis."""
    names = set()
    while len(names) < n:
        first = random.choice(FIRST_NAMES)
        last = random.choice(LAST_NAMES)
        middle = random.choice(FIRST_NAMES)
        
        # Variasikan 2 kata atau 3 kata
        if random.random() > 0.4:
            name = f"{first} {last}"
        else:
            name = f"{first} {middle} {last}"
        names.add(name)
    return sorted(list(names))


def load_curriculum_clos() -> list[dict]:
    """
    Memuat seluruh pemetaan CLO dan Skill dari 3 sumber:
    1. ITS (RPS_skill_extracted_*.csv, subset ITS)
    2. Telkom University Jakarta (OBE_JAKARTA.xlsx)
    3. Telkom University Surabaya (OBE_SURABAYA.xlsx)
    """
    clo_pool = []
    seen_clo_ids = set()

    # 1. Sumber 1: ITS
    if FILE_RPS_CSV.exists():
        df_rps = pd.read_csv(FILE_RPS_CSV, sep=";")
        df_its = df_rps[df_rps["source"].astype(str).str.upper() == "ITS"].copy()
        for idx, r in df_its.iterrows():
            kode_mk = str(r["kode_mk"]).strip() if pd.notna(r["kode_mk"]) else "ITS"
            clo_id = str(r["clo_id"]).strip() if pd.notna(r["clo_id"]) else f"CLO{idx+1}"
            skill = str(r["skill_text"]).strip().rstrip(" .:,;")
            
            # Buat ID CLO yang unik dan rapi
            clean_id = f"ITS_{kode_mk}_{clo_id}"
            if clean_id in seen_clo_ids:
                clean_id = f"ITS_{kode_mk}_{clo_id}_{idx+1}"
            seen_clo_ids.add(clean_id)

            if skill and len(skill) > 1:
                clo_pool.append({
                    "source": "ITS",
                    "id_CLO": clean_id,
                    "skill": skill,
                    "course": kode_mk
                })

    # 2. Sumber 2: Telkom University Jakarta
    if FILE_OBE_JKT.exists():
        df_jkt = pd.read_excel(FILE_OBE_JKT, sheet_name="Referensi_CLO")
        for _, r in df_jkt.iterrows():
            clo_id = str(r["id_CLO"]).strip()
            skill = str(r["skill_technical"]).strip().rstrip(" .:,;")
            course = str(r.get("course_name", r.get("course_code", "Jakarta"))).strip()
            
            seen_clo_ids.add(clo_id)
            if skill and len(skill) > 1:
                clo_pool.append({
                    "source": "Tel-U Jakarta",
                    "id_CLO": clo_id,
                    "skill": skill,
                    "course": course
                })

    # 3. Sumber 3: Telkom University Surabaya
    if FILE_OBE_SBY.exists():
        df_sby = pd.read_excel(FILE_OBE_SBY, sheet_name="Referensi_CLO")
        for _, r in df_sby.iterrows():
            clo_id = str(r["id_CLO"]).strip()
            skill = str(r["skill_technical"]).strip().rstrip(" .:,;")
            course = str(r.get("course_name", r.get("course_code", "Surabaya"))).strip()
            
            seen_clo_ids.add(clo_id)
            if skill and len(skill) > 1:
                clo_pool.append({
                    "source": "Tel-U Surabaya",
                    "id_CLO": clo_id,
                    "skill": skill,
                    "course": course
                })

    return clo_pool


def generate_realistic_score(student_strength_factor: float, clo_difficulty_factor: float) -> float:
    """
    Menghasilkan skor realistis strictly dalam rentang [40.01, 100.00].
    
    student_strength_factor: [0.0, 1.0] (kemampuan umum mahasiswa pada topik ini)
    clo_difficulty_factor: [0.0, 1.0] (faktor kemudahan materi)
    """
    base_mean = 45.0 + (student_strength_factor * 35.0) + (clo_difficulty_factor * 15.0)
    # Tambahkan noise acak
    noise = np.random.normal(0.0, 7.5)
    raw_score = base_mean + noise
    
    # STRICT CLAMP: Nilai harus >= 40.01 dan <= 100.00
    if raw_score < 40.01:
        # Berikan nilai acak di antara 40.01 dan 48.00
        score = random.uniform(40.01, 48.00)
    elif raw_score > 100.00:
        score = 100.00
    else:
        score = raw_score
        
    # Bulatkan ke 1 desimal, namun pastikan tetap >= 40.01
    rounded = round(score, 1)
    if rounded < 40.01:
        rounded = 40.1  # 40.1 strictly >= 40.01
    return float(rounded)


def generate_dataset():
    print("=" * 65)
    print("MEMULAI GENERATOR DATASET DUMMY 100 MAHASISWA")
    print("=" * 65)

    # 1. Muat Seluruh CLO & Skill dari 3 Sumber
    print("\n[1/5] Memuat CLO & Skill dari ITS, Tel-U Jakarta, dan Tel-U Surabaya...")
    clo_pool = load_curriculum_clos()
    print(f"  -> Total CLO-Skill Terpadu: {len(clo_pool):,} CLOs")
    
    # Hitung distribusi per sumber
    sources_count = pd.Series([c["source"] for c in clo_pool]).value_counts().to_dict()
    for src, count in sources_count.items():
        print(f"     * {src}: {count} CLOs")

    # 2. Buat Sheet 1: Daftar_Mahasiswa (100 Mahasiswa)
    print("\n[2/5] Menghasilkan data 100 mahasiswa (M0001 - M0100)...")
    synthetic_names = generate_synthetic_names(100)
    angkatan_options = [2021, 2022, 2023, 2024]
    angkatan_weights = [0.15, 0.35, 0.35, 0.15]

    daftar_mahasiswa_rows = []
    for i in range(1, 101):
        std_id = f"M{i:04d}"
        std_name = synthetic_names[i - 1]
        std_angkatan = random.choices(angkatan_options, weights=angkatan_weights, k=1)[0]
        daftar_mahasiswa_rows.append({
            "id_student": std_id,
            "nama_mahasiswa": std_name,
            "angkatan": std_angkatan
        })
    df_daftar_mahasiswa = pd.DataFrame(daftar_mahasiswa_rows)
    print(f"  -> Daftar Mahasiswa: {len(df_daftar_mahasiswa)} mahasiswa berhasil dibuat.")

    # 3. Buat Sheet 2 & Sheet 3: Nilai_Mahasiswa_per_CLO & input_mahasiswa
    print("\n[3/5] Mengenerate nilai per CLO dan profil skill bervariasi...")
    
    # Tentukan profil spesialisasi untuk membuat variasi realistis
    # Setiap mahasiswa memiliki kekuatan di topik tertentu
    specialization_topics = [
        "Programming & Software", "Database & Data Engineering", "Data Science & AI",
        "Networking & Security", "Web & Mobile Development", "Enterprise & Information Systems",
        "UI/UX & Human Computer Interaction", "General Balanced"
    ]

    nilai_per_clo_rows = []
    input_mahasiswa_rows = []

    for std in daftar_mahasiswa_rows:
        std_id = std["id_student"]
        std_spec = random.choice(specialization_topics)
        
        # Jumlah CLO yang diambil oleh mahasiswa (bervariasi antara 18 hingga 45 CLO)
        num_clos_taken = random.randint(18, 45)
        
        # Pilih subset CLO secara acak representatif dari ketiga sumber
        selected_clos = random.sample(clo_pool, k=min(num_clos_taken, len(clo_pool)))
        
        # Kekuatan dasar mahasiswa (ada mahasiswa pintar, sedang, dan cukup)
        student_base_tier = random.choices(["high", "medium", "low"], weights=[0.25, 0.55, 0.20], k=1)[0]
        
        if student_base_tier == "high":
            base_strength = random.uniform(0.70, 0.95)
        elif student_base_tier == "medium":
            base_strength = random.uniform(0.40, 0.75)
        else:
            base_strength = random.uniform(0.10, 0.45)

        for clo_info in selected_clos:
            clo_id = clo_info["id_CLO"]
            skill_name = clo_info["skill"]
            
            # Modifikasi kekuatan jika sesuai spesialisasi
            spec_boost = 0.15 if random.random() < 0.3 else 0.0
            difficulty_factor = random.uniform(0.3, 0.8)
            
            eff_strength = min(1.0, base_strength + spec_boost)
            final_score = generate_realistic_score(eff_strength, difficulty_factor)
            
            # Sheet 2: Nilai_Mahasiswa_per_CLO
            nilai_per_clo_rows.append({
                "id_student": std_id,
                "id_CLO": clo_id,
                "score": final_score
            })
            
            # Sheet 3: input_mahasiswa (HARUS 100% SAMA)
            input_mahasiswa_rows.append({
                "Student": std_id,
                "CLO": clo_id,
                "Skill": skill_name,
                "Score": final_score
            })

    df_nilai_clo = pd.DataFrame(nilai_per_clo_rows)
    df_input_mhs = pd.DataFrame(input_mahasiswa_rows)

    print(f"  -> Total Record Nilai per CLO : {len(df_nilai_clo):,} baris")
    print(f"  -> Total Record input_mahasiswa: {len(df_input_mhs):,} baris")

    # 4. VALIDASI KETAT
    print("\n[4/5] Menjalankan Validasi Ketat Integritas Data...")
    
    # Validasi Jumlah Mahasiswa
    assert len(df_daftar_mahasiswa) == 100, f"Error: Total mahasiswa bukan 100, melainkan {len(df_daftar_mahasiswa)}"
    assert df_daftar_mahasiswa["id_student"].nunique() == 100, "Error: id_student tidak unik"
    assert df_daftar_mahasiswa["id_student"].iloc[0] == "M0001", "Error: ID awal bukan M0001"
    assert df_daftar_mahasiswa["id_student"].iloc[-1] == "M0100", "Error: ID akhir bukan M0100"
    
    # Validasi Rentang Skor
    min_score_s2 = df_nilai_clo["score"].min()
    max_score_s2 = df_nilai_clo["score"].max()
    min_score_s3 = df_input_mhs["Score"].min()
    max_score_s3 = df_input_mhs["Score"].max()
    
    print(f"  -> Min Score Sheet 2: {min_score_s2:.2f}, Max Score: {max_score_s2:.2f}")
    print(f"  -> Min Score Sheet 3: {min_score_s3:.2f}, Max Score: {max_score_s3:.2f}")
    
    assert min_score_s2 >= 40.01, f"Error: Terdapat skor di bawah 40.01 pada Sheet 2: {min_score_s2}"
    assert max_score_s2 <= 100.00, f"Error: Terdapat skor di atas 100.00 pada Sheet 2: {max_score_s2}"
    assert min_score_s3 >= 40.01, f"Error: Terdapat skor di bawah 40.01 pada Sheet 3: {min_score_s3}"
    assert max_score_s3 <= 100.00, f"Error: Terdapat skor di atas 100.00 pada Sheet 3: {max_score_s3}"
    
    # Validasi Konsistensi Sheet 2 == Sheet 3
    assert len(df_nilai_clo) == len(df_input_mhs), "Error: Jumlah baris Sheet 2 dan Sheet 3 tidak sama"
    assert (df_nilai_clo["id_student"].values == df_input_mhs["Student"].values).all(), "Error: ID Student tidak cocok"
    assert (df_nilai_clo["id_CLO"].values == df_input_mhs["CLO"].values).all(), "Error: ID CLO tidak cocok"
    assert (df_nilai_clo["score"].values == df_input_mhs["Score"].values).all(), "Error: Nilai Score tidak konsisten"
    
    # Validasi Kolom dan Null
    assert list(df_daftar_mahasiswa.columns) == ["id_student", "nama_mahasiswa", "angkatan"]
    assert list(df_nilai_clo.columns) == ["id_student", "id_CLO", "score"]
    assert list(df_input_mhs.columns) == ["Student", "CLO", "Skill", "Score"]
    assert df_daftar_mahasiswa.isnull().sum().sum() == 0, "Ada null di Sheet 1"
    assert df_nilai_clo.isnull().sum().sum() == 0, "Ada null di Sheet 2"
    assert df_input_mhs.isnull().sum().sum() == 0, "Ada null di Sheet 3"
    
    print("  [OK] Seluruh Validasi Integritas LULUS 100%!")

    # 5. Ekspor ke Excel Multi-Sheet
    print("\n[5/5] Menyimpan dataset dummy ke file Excel...")
    
    CURRENT_DIR.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(OUTPUT_XLSX_PRIMARY, engine="openpyxl") as writer:
        df_daftar_mahasiswa.to_excel(writer, sheet_name="Daftar_Mahasiswa", index=False)
        df_nilai_clo.to_excel(writer, sheet_name="Nilai_Mahasiswa_per_CLO", index=False)
        df_input_mhs.to_excel(writer, sheet_name="input_mahasiswa", index=False)
    print(f"  -> File Excel tersimpan di: {OUTPUT_XLSX_PRIMARY}")

    with pd.ExcelWriter(OUTPUT_XLSX_DATA, engine="openpyxl") as writer:
        df_daftar_mahasiswa.to_excel(writer, sheet_name="Daftar_Mahasiswa", index=False)
        df_nilai_clo.to_excel(writer, sheet_name="Nilai_Mahasiswa_per_CLO", index=False)
        df_input_mhs.to_excel(writer, sheet_name="input_mahasiswa", index=False)
    print(f"  -> File Excel salinan tersimpan di: {OUTPUT_XLSX_DATA}")

    # Buat Laporan Markdown
    skills_per_student = df_input_mhs.groupby("Student")["Skill"].nunique()
    score_stats = df_nilai_clo["score"].describe()

    report_content = rf"""# Laporan Pembuatan Dataset Dummy 100 Mahasiswa

**Waktu Pembuatan:** {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Target File:** `{OUTPUT_XLSX_PRIMARY.name}`

---

## 1. Ringkasan Parameter & Ketentuan

| Parameter | Nilai / Ketentuan | Status |
|---|---|---|
| **Total Mahasiswa** | 100 Mahasiswa (`M0001` - `M0100`) | Sesuai |
| **Sumber Skill** | ITS (149 CLO) + Tel-U Jakarta (137 CLO) + Tel-U Surabaya (180 CLO) | Sesuai |
| **Batasan Nilai Minimum** | $\ge 40.01$ (Terkecil: `{min_score_s2:.2f}`) | Lulus 100% |
| **Batasan Nilai Maksimum** | $\le 100.00$ (Terbesar: `{max_score_s2:.2f}`) | Lulus 100% |
| **Konsistensi Antar-Sheet** | Skor Sheet `Nilai_Mahasiswa_per_CLO` == Sheet `input_mahasiswa` | 100% Konsisten |


---

## 2. Struktur Sheet & Jumlah Baris

| No | Nama Sheet | Kolom | Jumlah Baris Data |
|---|---|---|---|
| 1 | `Daftar_Mahasiswa` | `id_student`, `nama_mahasiswa`, `angkatan` | {len(df_daftar_mahasiswa):,} |
| 2 | `Nilai_Mahasiswa_per_CLO` | `id_student`, `id_CLO`, `score` | {len(df_nilai_clo):,} |
| 3 | `input_mahasiswa` | `Student`, `CLO`, `Skill`, `Score` | {len(df_input_mhs):,} |

---

## 3. Statistik Distribusi Nilai & Kemampuan Mahasiswa

* **Rata-rata Skor Mahasiswa**: {score_stats['mean']:.2f}
* **Standar Deviasi**: {score_stats['std']:.2f}
* **Kuartil 25% (Q1)**: {score_stats['25%']:.2f}
* **Median (Q2)**: {score_stats['50%']:.2f}
* **Kuartil 75% (Q3)**: {score_stats['75%']:.2f}
* **Rentang Jumlah Skill per Mahasiswa**: {skills_per_student.min()} s/d {skills_per_student.max()} skill per mahasiswa (Rata-rata: {skills_per_student.mean():.1f} skill)

---

## 4. Sampel 5 Baris Pertama Setiap Sheet

### Sheet 1: `Daftar_Mahasiswa`
| id_student | nama_mahasiswa | angkatan |
|---|---|---|
"""
    for _, r in df_daftar_mahasiswa.head(5).iterrows():
        report_content += f"| `{r['id_student']}` | {r['nama_mahasiswa']} | {r['angkatan']} |\n"

    report_content += "\n\n### Sheet 2: `Nilai_Mahasiswa_per_CLO`\n| id_student | id_CLO | score |\n|---|---|---|\n"
    for _, r in df_nilai_clo.head(5).iterrows():
        report_content += f"| `{r['id_student']}` | `{r['id_CLO']}` | **{r['score']}** |\n"

    report_content += "\n\n### Sheet 3: `input_mahasiswa`\n| Student | CLO | Skill | Score |\n|---|---|---|---|\n"
    for _, r in df_input_mhs.head(5).iterrows():
        report_content += f"| `{r['Student']}` | `{r['CLO']}` | {r['Skill']} | **{r['Score']}** |\n"

    with open(OUTPUT_REPORT, "w", encoding="utf-8") as f:
        f.write(report_content)
    print(f"  -> Laporan markdown tersimpan di: {OUTPUT_REPORT}")


    print("\n" + "=" * 65)
    print("PEMBUATAN DATASET DUMMY MAHASISWA 100 SELESAI DENGAN SUKSES!")
    print("=" * 65)


if __name__ == "__main__":
    generate_dataset()
