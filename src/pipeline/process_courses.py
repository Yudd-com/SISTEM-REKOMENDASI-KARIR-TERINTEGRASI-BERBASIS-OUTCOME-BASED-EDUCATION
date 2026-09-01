"""
process_courses.py
==================
Modul untuk memproses, membersihkan, menormalisasi, dan menggabungkan
4 dataset course mentah menjadi satu dataset master terpadu (course_master_combined.xlsx).

Dataset Sumber:
1. data/UCoursera_Courses_cleaned.xlsx
2. data/udemy_courses_cleaned.xlsx
3. data/Online_Course_clean.xlsx
4. data/coursera_course_2024_cleaned.xlsx

Struktur Output Target:
- File  : course_master_combined.xlsx
- Sheet : Course
- Kolom : course_id | course_name | platform | level
"""

import os
import sys
import re
import unicodedata
from pathlib import Path
import pandas as pd

# Konfigurasi Path
CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = CURRENT_DIR / "Output Course"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def get_dataset_path(filename: str) -> Path:
    """Mencari file dataset di folder saat ini atau folder data/."""
    local_path = CURRENT_DIR / filename
    if local_path.exists():
        return local_path
    data_path = DATA_DIR / filename
    if data_path.exists():
        return data_path
    return local_path

FILE_UCOURSERA = get_dataset_path("UCoursera_Courses_cleaned.xlsx")
FILE_UDEMY = get_dataset_path("udemy_courses_cleaned.xlsx")
FILE_ONLINE_COURSE = get_dataset_path("Online_Course_clean.xlsx")
FILE_COURSERA_2024 = get_dataset_path("coursera_course_2024_cleaned.xlsx")

OUTPUT_EXCEL_PRIMARY = OUTPUT_DIR / "course_master_combined.xlsx"
OUTPUT_EXCEL_DATA = DATA_DIR / "course_master_combined.xlsx"
OUTPUT_REPORT = OUTPUT_DIR / "laporan_pemprosesan_course.md"




def normalize_string(s: str) -> str:
    """Normalisasi string unicode dasar, whitespace, dan tanda baca kutip."""
    if pd.isna(s) or s is None:
        return ""
    # Normalisasi Unicode form NFKC
    s = unicodedata.normalize("NFKC", str(s))
    # Standarisasi variasi tanda kutip dan apostrof
    s = s.replace("\u2019", "'").replace("\u2018", "'").replace("\u201c", '"').replace("\u201d", '"')
    s = s.replace("\u2013", "-").replace("\u2014", "-").replace("\u2026", "...")
    # Hapus simbol dekoratif/bullet di awal teks
    s = re.sub(r"^[*\s\u2022\u00b7\-\.]+", "", s)
    # Hapus spasi berlebih
    s = re.sub(r"\s+", " ", s).strip()
    return s


def clean_course_name(s: str) -> str:
    """Membersihkan judul course tanpa mengubah makna atau nama aslinya."""
    s = normalize_string(s)
    if not s:
        return ""
    
    # Jika seluruh teks adalah ALL CAPS dan panjang > 4 karakter,
    # ubah menjadi format Title Case cerdas dengan mempertahankan singkatan teknis.
    if s.isupper() and len(s) > 4:
        words = s.split()
        converted = []
        keep_upper = {
            "AI", "API", "AWS", "CPA", "CSS", "HTML", "IBM", "IDP-ICE",
            "IT", "JS", "ML", "NIST", "PHP", "R", "REST", "SAS", "SEO",
            "SQL", "SSCP", "UI", "UX", "UI/UX", "VBA", "VR", "AR",
            "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"
        }
        for w in words:
            clean_w = re.sub(r"[^A-Za-z0-9]", "", w)
            if clean_w.upper() in keep_upper:
                converted.append(w.upper())
            else:
                converted.append(w.capitalize())
        s = " ".join(converted)
    
    return s


def normalize_platform(p: str) -> str:
    """Menstandarkan penamaan platform/provider yang sama."""
    p = normalize_string(p)
    if not p or p.lower() in ["organization not found", "nan", "none", "unknown", ""]:
        return "Coursera"
    
    p_lower = p.lower()
    
    # Standarisasi variasi penamaan institusi/organisasi
    if p_lower in ["deeplearning.ai"]:
        return "DeepLearning.AI"
    elif "illinois" in p_lower and "urbana-champaign" in p_lower:
        return "University of Illinois Urbana-Champaign"
    elif p_lower in ["isc2", "(isc)2", "(isc)²"]:
        return "(ISC)²"
    elif p_lower in ["illinois tech", "illinois institute of technology"]:
        return "Illinois Institute of Technology"
    elif p_lower in ["rutgers university", "rutgers the state university of new jersey"]:
        return "Rutgers University"
    elif p_lower in ["berklee", "berklee college of music"]:
        return "Berklee College of Music"
    elif p_lower in ["coursera", "coursera.org"]:
        return "Coursera"
    elif p_lower in ["udemy", "udemy.com"]:
        return "Udemy"
    elif p_lower in ["google", "google inc", "google llc"]:
        return "Google"
    
    return p


def map_level(raw_level, course_title: str = "") -> str:
    """
    Memetakan variasi level ke 4 kategori baku:
    - Beginner
    - Intermediate
    - Advanced
    - Unknown
    """
    if pd.isna(raw_level) or raw_level is None:
        raw_str = ""
    else:
        raw_str = str(raw_level).strip()
    
    lvl_lower = raw_str.lower()
    
    # 1. Cek string eksplisit level sumber
    if any(k in lvl_lower for k in ["beginner", "basic", "introductory", "entry level", "entry-level", "fundamental", "starter"]):
        return "Beginner"
    elif any(k in lvl_lower for k in ["intermediate", "medium", "middle"]):
        return "Intermediate"
    elif any(k in lvl_lower for k in ["advanced", "expert", "master", "specialist"]):
        return "Advanced"
    
    # 2. Jika level sumber tidak spesifik (All Levels, Mixed, Not specified, Course, Specialization, Degree, kosong),
    # cari indikator kuat pada judul course.
    t_lower = course_title.lower() if course_title else ""
    
    if re.search(r"\b(beginner|beginners|introduction to|intro to|introductory|fundamentals of|basics of|basic|getting started with|for dummies)\b", t_lower):
        return "Beginner"
    elif re.search(r"\b(advanced|masterclass|expert|deep dive)\b", t_lower):
        return "Advanced"
    elif re.search(r"\b(intermediate)\b", t_lower):
        return "Intermediate"
    
    # 3. Fallback jika benar-benar tidak tersedia
    return "Unknown"


def create_dedup_key(course_name: str, platform: str) -> tuple:
    """Membuat signature unik untuk deduplikasi akurat pada platform yang sama."""
    c = normalize_string(course_name).lower()
    # Hapus tanda baca di ujung nama (colon, dash, period, dsb.) untuk perbandingan dedup
    c = re.sub(r"[\s\.\:\,\;\-]+$", "", c)
    p = normalize_platform(platform).lower()
    return (c, p)


def run_pipeline():
    print("=" * 70)
    print("MEMULAI PIPELINE PEMPROSESAN DATASET COURSE MASTER")
    print("=" * 70)
    
    # -------------------------------------------------------------
    # Langkah 1: Membaca ke-4 Dataset Sumber
    # -------------------------------------------------------------
    print("\n[1/5] Membaca dataset sumber...")
    
    # 1. UCoursera
    df_ucoursera = pd.read_excel(FILE_UCOURSERA, sheet_name="Courses")
    count_ucoursera = len(df_ucoursera)
    print(f"  -> 1. UCoursera_Courses_cleaned.xlsx  : {count_ucoursera:,} baris")
    
    # 2. Udemy
    df_udemy = pd.read_excel(FILE_UDEMY, sheet_name="Courses")
    count_udemy = len(df_udemy)
    print(f"  -> 2. udemy_courses_cleaned.xlsx      : {count_udemy:,} baris")
    
    # 3. Online Course
    df_online_raw = pd.read_excel(FILE_ONLINE_COURSE, sheet_name="Course")
    if str(df_online_raw.iloc[0, 0]).strip() == "course_id":
        df_online = df_online_raw.iloc[1:].copy().reset_index(drop=True)
    else:
        df_online = df_online_raw.copy()
    count_online = len(df_online)
    print(f"  -> 3. Online_Course_clean.xlsx        : {count_online:,} baris data")
    
    # 4. Coursera 2024
    df_coursera_2024 = pd.read_excel(FILE_COURSERA_2024, sheet_name="Courses")
    count_coursera_2024 = len(df_coursera_2024)
    print(f"  -> 4. coursera_course_2024_cleaned.xlsx: {count_coursera_2024:,} baris")
    
    total_raw = count_ucoursera + count_udemy + count_online + count_coursera_2024
    print(f"\n  Total data sebelum penggabungan: {total_raw:,} baris")
    
    # -------------------------------------------------------------
    # Langkah 2: Ekstraksi Record Mentah
    # -------------------------------------------------------------
    print("\n[2/5] Menggabungkan dan mengekstrak field...")
    raw_records = []
    
    # UCoursera: Title -> course_name, Organization -> platform, Difficulty -> level
    for _, r in df_ucoursera.iterrows():
        raw_records.append({
            "source_file": "UCoursera_Courses_cleaned.xlsx",
            "raw_title": r["Title"],
            "raw_platform": r["Organization"],
            "raw_level": r["Difficulty"]
        })
        
    # Udemy: Title -> course_name, Udemy -> platform, Level -> level
    for _, r in df_udemy.iterrows():
        raw_records.append({
            "source_file": "udemy_courses_cleaned.xlsx",
            "raw_title": r["Title"],
            "raw_platform": "Udemy",
            "raw_level": r["Level"]
        })
        
    # Online Course: Unnamed: 1 -> course_name, Unnamed: 2 -> platform, Unnamed: 3 -> level
    for _, r in df_online.iterrows():
        raw_records.append({
            "source_file": "Online_Course_clean.xlsx",
            "raw_title": r.iloc[1],
            "raw_platform": r.iloc[2],
            "raw_level": r.iloc[3]
        })
        
    # Coursera 2024: Title -> course_name, Organization -> platform, Level -> level
    for _, r in df_coursera_2024.iterrows():
        raw_records.append({
            "source_file": "coursera_course_2024_cleaned.xlsx",
            "raw_title": r["Title"],
            "raw_platform": r["Organization"],
            "raw_level": r["Level"]
        })
        
    # -------------------------------------------------------------
    # Langkah 3: Normalisasi, Deduplikasi & Pengayaan Level
    # -------------------------------------------------------------
    print("\n[3/5] Melakukan normalisasi dan deduplikasi cerdas...")
    seen_signatures = {}
    master_records = []
    duplicate_count = 0
    
    for item in raw_records:
        title = clean_course_name(item["raw_title"])
        platform = normalize_platform(item["raw_platform"])
        
        # Validasi: course_name tidak boleh kosong
        if not title:
            continue
            
        level = map_level(item["raw_level"], title)
        sig = create_dedup_key(title, platform)
        
        if sig in seen_signatures:
            duplicate_count += 1
            idx = seen_signatures[sig]
            # Pengayaan level: jika entri sebelumnya Unknown tetapi entri baru punya level spesifik, perbarui
            if master_records[idx]["level"] == "Unknown" and level != "Unknown":
                master_records[idx]["level"] = level
        else:
            seen_signatures[sig] = len(master_records)
            master_records.append({
                "course_name": title,
                "platform": platform,
                "level": level
            })
            
    final_unique_count = len(master_records)
    print(f"  -> Jumlah duplikat dihapus : {duplicate_count:,}")
    print(f"  -> Jumlah course unik final: {final_unique_count:,}")
    
    # -------------------------------------------------------------
    # Langkah 4: Pembuatan course_id Terurut dan Validasi Akhir
    # -------------------------------------------------------------
    print("\n[4/5] Mengenerate course_id dan melakukan validasi...")
    
    # Format course_id: C001, C002, ..., C010, ..., C100, ..., C1000, dst.
    # Penomoran 1-indexed berurutan
    for i, rec in enumerate(master_records, start=1):
        rec["course_id"] = f"C{i:03d}"
        
    df_final = pd.DataFrame(master_records)[["course_id", "course_name", "platform", "level"]]
    
    # VALIDASI INTEGRITAS
    assert len(df_final.columns) == 4, f"Error: Kolom harus tepat 4, ditemukan {len(df_final.columns)}"
    assert list(df_final.columns) == ["course_id", "course_name", "platform", "level"], "Error: Nama kolom tidak sesuai"
    assert df_final["course_id"].is_unique, "Error: course_id tidak unik"
    assert df_final["course_name"].isnull().sum() == 0, "Error: Terdapat course_name kosong"
    assert df_final["platform"].isnull().sum() == 0, "Error: Terdapat platform kosong"
    assert df_final["level"].isnull().sum() == 0, "Error: Terdapat level kosong"
    
    valid_levels = {"Beginner", "Intermediate", "Advanced", "Unknown"}
    level_diff = set(df_final["level"].unique()) - valid_levels
    assert len(level_diff) == 0, f"Error: Nilai level tidak valid ditemukan: {level_diff}"
    
    print("  [OK] Validasi Struktur & Integritas Data Lulus 100%!")
    
    # -------------------------------------------------------------
    # Langkah 5: Ekspor ke Excel & Pembuatan Laporan
    # -------------------------------------------------------------
    print("\n[5/5] Menyimpan dataset master dan membuat laporan...")
    
    # Simpan ke folder Pemprosesan Course
    with pd.ExcelWriter(OUTPUT_EXCEL_PRIMARY, engine="openpyxl") as writer:
        df_final.to_excel(writer, sheet_name="Course", index=False)
    print(f"  -> File Excel tersimpan di: {OUTPUT_EXCEL_PRIMARY}")
    
    # Simpan salinan ke folder data/
    with pd.ExcelWriter(OUTPUT_EXCEL_DATA, engine="openpyxl") as writer:
        df_final.to_excel(writer, sheet_name="Course", index=False)
    print(f"  -> File Excel salinan tersimpan di: {OUTPUT_EXCEL_DATA}")
    
    # Analisis Distribusi
    level_dist = df_final["level"].value_counts()
    platform_dist = df_final["platform"].value_counts()
    
    # Buat Laporan Markdown
    report_content = f"""# Laporan Hasil Pemprosesan Dataset Course Master

**Waktu Pemprosesan:** {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Target Output:** `{OUTPUT_EXCEL_PRIMARY.name}` (Sheet: `Course`)

---

## 1. Ringkasan Data Awal & Penggabungan

| No | Dataset Sumber | Sheet Sumber | Jumlah Baris Awal |
|---|---|---|---|
| 1 | `UCoursera_Courses_cleaned.xlsx` | `Courses` | {count_ucoursera:,} |
| 2 | `udemy_courses_cleaned.xlsx` | `Courses` | {count_udemy:,} |
| 3 | `Online_Course_clean.xlsx` | `Course` | {count_online:,} |
| 4 | `coursera_course_2024_cleaned.xlsx` | `Courses` | {count_coursera_2024:,} |
| **Total** | **Total Baris Sebelum Penggabungan** | - | **{total_raw:,}** |

---

## 2. Hasil Deduplikasi & Finalisasi Course Unik

| Metrik | Nilai | Persentase |
|---|---|---|
| **Total Data Awal** | {total_raw:,} baris | 100.0% |
| **Jumlah Duplikat Dihapus** | {duplicate_count:,} baris | {duplicate_count/total_raw*100:.2f}% |
| **Jumlah Course Unik Final** | **{final_unique_count:,} baris** | **{final_unique_count/total_raw*100:.2f}%** |
| **Rentang `course_id`** | `{df_final.iloc[0]['course_id']}` s/d `{df_final.iloc[-1]['course_id']}` | 100% Unik & Gapless |

---

## 3. Distribusi Course Berdasarkan Level

| Level | Jumlah Course | Persentase |
|---|---|---|
"""
    for lvl, cnt in level_dist.items():
        report_content += f"| **{lvl}** | {cnt:,} | {cnt/final_unique_count*100:.2f}% |\n"
    report_content += f"| **Total** | **{final_unique_count:,}** | **100.00%** |\n\n"

    report_content += """---

## 4. Distribusi Course Berdasarkan Platform (Top 25)

| No | Platform / Provider | Jumlah Course | Persentase |
|---|---|---|---|
"""
    for idx, (plat, cnt) in enumerate(platform_dist.head(25).items(), start=1):
        report_content += f"| {idx} | {plat} | {cnt:,} | {cnt/final_unique_count*100:.2f}% |\n"
    
    other_cnt = platform_dist.iloc[25:].sum()
    other_plats = len(platform_dist) - 25
    report_content += f"| - | *Lainnya ({other_plats} platform/institusi)* | {other_cnt:,} | {other_cnt/final_unique_count*100:.2f}% |\n"
    report_content += f"| **Total** | **Total Seluruh Platform ({len(platform_dist)} unik)** | **{final_unique_count:,}** | **100.00%** |\n\n"

    report_content += """---

## 5. Struktur & Format Dataset Final

Struktur kolom pada sheet `Course`:

| Nama Kolom | Tipe Data | Contoh Nilai | Keterangan |
|---|---|---|---|
| `course_id` | String | `C001`, `C002`, `C1000` | ID unik terurut 1-indexed |
| `course_name` | String | `Google Cybersecurity` | Judul course bersih & terstandarisasi |
| `platform` | String | `Google`, `Udemy`, `IBM` | Platform / Provider course |
| `level` | String | `Beginner`, `Intermediate`, `Advanced`, `Unknown` | Tingkat kesulitan baku |

---

## 6. Sampel 10 Baris Pertama Dataset Final

| course_id | course_name | platform | level |
|---|---|---|---|
"""
    for _, r in df_final.head(10).iterrows():
        report_content += f"| `{r['course_id']}` | {r['course_name']} | {r['platform']} | {r['level']} |\n"

    with open(OUTPUT_REPORT, "w", encoding="utf-8") as f:
        f.write(report_content)
    print(f"  -> Laporan markdown tersimpan di: {OUTPUT_REPORT}")
    
    print("\n" + "=" * 70)
    print("PIPELINE SELESAI DENGAN SUKSES!")
    print("=" * 70)


if __name__ == "__main__":
    run_pipeline()
