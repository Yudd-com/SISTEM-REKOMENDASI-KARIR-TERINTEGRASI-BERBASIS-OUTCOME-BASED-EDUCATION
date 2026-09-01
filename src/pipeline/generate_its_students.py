"""
generate_its_students.py
=========================
Script untuk menambahkan 100 Mahasiswa ITS (I0001 - I0100) ke
student_skill_final_v2.csv yang sudah ada (Jakarta + Surabaya).

Sumber Data ITS:
- data_raw/obe/RPS_skill_extracted_20260809_185306.csv (source == 'ITS')
- data_clean/normalized/normalisasi_skill_mahasiswa.xlsx (academic_source == 'ITS')

Format Output (sama persis dengan student_skill_final_v2.csv):
  student_id;student_name;campus;id_CLO;skill_original;canonical_skill;score

Hasil Akhir:
  - 300 Mahasiswa Total (100 Jakarta + 100 Surabaya + 100 ITS)
  - File di-update di: data_clean/normalized/student_skill_final_v2.csv
"""

import random
import numpy as np
import pandas as pd
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent.parent
RANDOM_SEED = 42
random.seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)

# Daftar 100 nama khusus ITS (tidak bentrok dengan Jakarta/Surabaya) — tepat 100 nama
ITS_NAMES = [
    "Achmad Basuki",    "Ade Irfan",         "Adi Nugroho",       "Aditya Trisna",    "Agung Rahardjo",
    "Agus Dwi",         "Alfi Rahmad",       "Alief Hasanuddin",  "Alim Sumarno",     "Andika Prasetya",
    "Andri Wijayanto",  "Anshori Mukhlis",   "Arifin Sofian",     "Arman Hakim",      "Asep Juanda",
    "Asyhari Wahyu",    "Auliya Rizki",      "Bagus Prakoso",     "Bambang Dwi",      "Bayu Firmanto",
    "Bondan Prakoso",   "Budi Prasetyo",     "Cahyo Adhi",        "Dani Maulana",     "Danu Wisesa",
    "Darma Wijaya",     "Deni Wahyudi",      "Dian Nafi",         "Didik Hadiyatno",  "Dimas Arianto",
    "Dipo Prasetyo",    "Dwi Ariesanto",     "Dwi Cahyono",       "Eko Budi",         "Eko Wahono",
    "Erlina Wati",      "Erwin Santosa",     "Fadli Iskandar",    "Fajar Budi",       "Faza Mudrika",
    "Ferry Wahyu",      "Fitra Buana",       "Galih Priambodo",   "Ganda Kusuma",     "Gunawan Prasetyo",
    "Hamam Riza",       "Handika Setyo",     "Heri Susanto",      "Herry Kristanto",  "Hilman Fathoni",
    "Husni Thamrin",    "Ibnu Susilo",       "Ika Yunita",        "Imam Kuswardayan", "Indra Cahya",
    "Ismail Mukhlas",   "Jati Ariawan",      "Juli Setiawan",     "Kresno Adi",       "Kusworo Adi",
    "Lilis Setiawati",  "Lina Handayani",    "Lutfi Fanani",      "Mardiana Oesman",  "Moh Irfan",
    "Mochamad Hariadi", "Muhammad Fauzan",   "Muhyiddin Zainuddin","Nani Sunarni",    "Nur Hidayat",
    "Nurdin Bahtiar",   "Nurul Fajri",       "Paulus Sukamdani",  "Penny Sukmawati",  "Popy Yuniar",
    "Pramuninto Satyo", "Prihandoko Wahyu",  "Raden Achmad",      "Ragil Wahyu",      "Randy Cahyo",
    "Reza Fauzan",      "Ridho Rahmadi",     "Rifqi Basuki",      "Rini Sovia",       "Riza Pahlevy",
    "Rully Soelaiman",  "Seno Aji",          "Siti Rochimah",     "Sri Zalbawi",      "Sumarsono Adi",
    "Surya Sumpeno",    "Sutikno Widodo",    "Tomy Abuzairi",     "Tri Sagirani",     "Uky Yudatama",
    "Ulil Albab",       "Wahyu Suadi",       "Waskitho Nugroho",  "Yosefine Endang",  "Yudha Saintika",
]
assert len(ITS_NAMES) == 100, f"Harus tepat 100 nama! Sekarang: {len(ITS_NAMES)}"


def main():
    print("=" * 70)
    print("MENAMBAHKAN 100 MAHASISWA ITS KE student_skill_final_v2.csv")
    print("=" * 70)

    # ── Paths ──────────────────────────────────────────────────────────────
    p_v2       = BASE / "data_clean" / "normalized" / "student_skill_final_v2.csv"
    p_norm     = BASE / "data_clean" / "normalized" / "normalisasi_skill_mahasiswa.xlsx"

    # ── 1. Load data existing ──────────────────────────────────────────────
    print(f"\n[1/5] Membaca student_skill_final_v2.csv yang ada...")
    df_v2 = pd.read_csv(p_v2, sep=";")
    print(f"  Total baris awal : {len(df_v2):,}")
    print(f"  Kampus           : {df_v2['campus'].unique().tolist()}")
    print(f"  Total mahasiswa  : {df_v2['student_id'].nunique()} (J:100 + S:100)")

    # ── 2. Load ITS canonical skills ───────────────────────────────────────
    print(f"\n[2/5] Membaca skill ITS dari normalisasi_skill_mahasiswa.xlsx...")
    df_norm = pd.read_excel(p_norm)
    its_skills = df_norm[df_norm["academic_source"] == "ITS"][
        ["id_CLO", "original_skill", "canonical_skill"]
    ].reset_index(drop=True)
    print(f"  Total CLO ITS    : {len(its_skills)}")
    print(f"  Unique CLO ITS   : {its_skills['id_CLO'].nunique()}")

    # ── 3. Generate 100 mahasiswa ITS ─────────────────────────────────────
    print(f"\n[3/5] Generating 100 Mahasiswa ITS (I0001 - I0100)...")

    its_clo_list = its_skills.to_dict("records")   # 149 CLO/skill ITS

    rows = []
    for i, name in enumerate(ITS_NAMES, start=1):
        student_id = f"I{i:04d}"

        # Setiap mahasiswa mendapat semua 149 skill ITS dengan skor acak >= 50.1
        for clo_row in its_clo_list:
            score = round(random.uniform(50.1, 100.0), 1)
            rows.append({
                "student_id"    : student_id,
                "student_name"  : name,
                "campus"        : "ITS",
                "id_CLO"        : clo_row["id_CLO"],
                "skill_original": clo_row["original_skill"],
                "canonical_skill": clo_row["canonical_skill"],
                "score"         : score,
            })

    df_its = pd.DataFrame(rows)

    # Deduplikasi: per (student_id, canonical_skill) ambil skor tertinggi
    df_its = df_its.sort_values(["student_id", "score"], ascending=[True, False])
    df_its = df_its.drop_duplicates(subset=["student_id", "canonical_skill"], keep="first")

    print(f"  Total baris ITS (setelah dedup): {len(df_its):,}")
    print(f"  Rata-rata skill per mhs ITS     : {len(df_its)/100:.1f}")

    # ── 4. Gabungkan ke df_v2 ─────────────────────────────────────────────
    print(f"\n[4/5] Menggabungkan dengan data Jakarta + Surabaya...")
    df_final = pd.concat([df_v2, df_its], ignore_index=True)

    # Simpan kembali ke student_skill_final_v2.csv (overwrite)
    df_final.to_csv(p_v2, sep=";", index=False, encoding="utf-8")
    print(f"  Total baris akhir: {len(df_final):,}")
    print(f"  Disimpan ke      : {p_v2}")

    # ── 5. Ringkasan ──────────────────────────────────────────────────────
    print(f"\n{'='*70}")
    print("RINGKASAN STUDENT_SKILL_FINAL_V2.CSV (SETELAH UPDATE):")
    print(f"{'='*70}")
    campus_stats = df_final.groupby("campus").agg(
        mhs=("student_id", "nunique"),
        baris=("student_id", "count"),
    )
    total_mhs  = df_final["student_id"].nunique()
    total_rows = len(df_final)
    for campus, row in campus_stats.iterrows():
        print(f"  {campus:<10}: {int(row['mhs']):>3} mahasiswa, {int(row['baris']):>5,} baris")
    print(f"  {'TOTAL':<10}: {total_mhs:>3} mahasiswa, {total_rows:>5,} baris")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
