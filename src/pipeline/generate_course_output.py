"""
generate_course_output.py
=========================
Script untuk menghasilkan file output lengkap Ekstraksi & Normalisasi Course:
File: DATA_COURSE_EKSTRAKSI_DAN_NORMALISASI.xlsx

Struktur Sheet:
1. Course_Master            : Daftar katalog kursus & total skill yang diajarkan
2. Course_Skill_Ekstraksi   : Hasil ekstraksi skill mentah per kursus
3. Course_Skill_Normalisasi : Pemetaan ekstraksi -> canonical skill + similarity score & status
4. Course_Skill_Final       : Format clean siap Knowledge Graph (Course -> TEACHES -> Skill)
"""

import os
import re
import unicodedata
from pathlib import Path
import pandas as pd

CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
DATA_DIR = PROJECT_ROOT / "data"
PEMPROSESAN_DATA_DIR = PROJECT_ROOT / "Pemprosesan Data"

FILE_COURSE_MASTER = PEMPROSESAN_DATA_DIR / "Data Utama" / "course_master_combined.xlsx"
FILE_ONLINE_COURSE = DATA_DIR / "Online_Course_clean.xlsx"
FILE_CANONICAL = PEMPROSESAN_DATA_DIR / "Normalisasi Skill" / "canonical_skill_master.xlsx"

OUTPUT_DIR = CURRENT_DIR / "Output Course"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_EXCEL = OUTPUT_DIR / "DATA_COURSE_EKSTRAKSI_DAN_NORMALISASI.xlsx"
OUTPUT_REPORT = OUTPUT_DIR / "laporan_ekstraksi_normalisasi_course.md"


def clean_skill_str(s: str) -> str:
    """Pembersihan teks string untuk matching."""
    if pd.isna(s) or s is None:
        return ""
    s = unicodedata.normalize("NFKC", str(s))
    s = s.replace("\u2019", "'").replace("\u2018", "'").replace("\u201c", '"').replace("\u201d", '"')
    s = re.sub(r"^[*\s\-\.]+|[*\s\-\.\:\,]+$", "", s)
    s = re.sub(r"\s+", " ", s).strip().lower()
    return s


def build_course_output():
    print("=" * 65)
    print("MEMBANGUN OUTPUT EKSTRAKSI & NORMALISASI DATA COURSE")
    print("=" * 65)

    # 1. Muat Kamus Canonical
    print("\n[1/4] Memuat kamus Canonical Skill Master...")
    df_canon = pd.read_excel(FILE_CANONICAL, sheet_name="Canonical_Master")
    canon_lookup = {}
    score_lookup = {}
    status_lookup = {}
    for _, r in df_canon.iterrows():
        orig = clean_skill_str(r["original_skill"])
        canon = clean_skill_str(r["canonical_skill"])
        if orig:
            canon_lookup[orig] = canon if canon else orig
            score_lookup[orig] = r.get("similarity_score", 1.0)
            status_lookup[orig] = r.get("status", "accepted")

    # 2. Muat Data Kursus
    print("\n[2/4] Memuat data katalog kursus & skill kursus...")
    df_course_master_meta = pd.read_excel(FILE_COURSE_MASTER, sheet_name="Course")
    
    df_cskill = pd.read_excel(FILE_ONLINE_COURSE, sheet_name="CourseSkill", skiprows=1, header=None)
    df_cskill.columns = ["course_id", "original_skill", "normalized_skill"]
    
    # Merge informasi metadata kursus
    df_course_joined = df_cskill.merge(df_course_master_meta, on="course_id", how="left")
    
    # 3. Bangun Sheet Ekstraksi, Normalisasi, dan Final
    print("\n[3/4] Melakukan pemetaan normalisasi skill kursus...")
    ekstraksi_rows = []
    normalisasi_rows = []
    final_rows = []

    for _, r in df_course_joined.iterrows():
        cid = str(r["course_id"]).strip()
        cname = str(r.get("course_name", "")).strip()
        platform = str(r.get("platform", "Coursera")).strip()
        level = str(r.get("level", "Unknown")).strip()
        raw_skill = str(r.get("original_skill", "")).strip()
        clean_raw = clean_skill_str(raw_skill)
        
        if not clean_raw:
            continue

        # Sheet Ekstraksi
        ekstraksi_rows.append({
            "course_id": cid,
            "course_name": cname,
            "platform": platform,
            "level": level,
            "extracted_skill": clean_raw
        })

        # Sheet Normalisasi
        canon_skill = canon_lookup.get(clean_raw, clean_raw)
        sim_score = score_lookup.get(clean_raw, 1.0)
        status = status_lookup.get(clean_raw, "accepted")

        normalisasi_rows.append({
            "course_id": cid,
            "course_name": cname,
            "platform": platform,
            "level": level,
            "extracted_skill": clean_raw,
            "canonical_skill": canon_skill,
            "similarity_score": sim_score,
            "status": status
        })

        # Sheet Final (Clean Deduplicated)
        final_rows.append({
            "course_id": cid,
            "course_name": cname,
            "platform": platform,
            "level": level,
            "canonical_skill": canon_skill
        })

    df_ekstraksi = pd.DataFrame(ekstraksi_rows).drop_duplicates()
    df_normalisasi = pd.DataFrame(normalisasi_rows).drop_duplicates()
    df_final = pd.DataFrame(final_rows).drop_duplicates(subset=["course_id", "canonical_skill"])

    # Sheet Master Course
    df_course_master = df_final.groupby(["course_id", "course_name", "platform", "level"]).size().reset_index(name="total_taught_skills")
    
    # 4. Simpan ke File Excel Multi-Sheet
    print("\n[4/4] Menyimpan ke file Excel multi-sheet...")
    with pd.ExcelWriter(OUTPUT_EXCEL, engine="openpyxl") as writer:
        df_course_master.to_excel(writer, sheet_name="Course_Master", index=False)
        df_ekstraksi.to_excel(writer, sheet_name="Course_Skill_Ekstraksi", index=False)
        df_normalisasi.to_excel(writer, sheet_name="Course_Skill_Normalisasi", index=False)
        df_final.to_excel(writer, sheet_name="Course_Skill_Final", index=False)

    print(f"  -> File Excel tersimpan: {OUTPUT_EXCEL}")

    # Buat Laporan Markdown
    report_content = rf"""# Laporan Pemprosesan Data Course (Ekstraksi & Normalisasi)

**Waktu Pembuatan:** {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Target File:** `{OUTPUT_EXCEL.name}`  
**Lokasi Direktori:** `{OUTPUT_DIR}`

---

## 1. Ringkasan Statistik Data Course

| Metrik | Jumlah |
|---|---|
| **Total Kursus dengan Skill (Course Master)** | {len(df_course_master):,} Kursus |
| **Total Record Ekstraksi Skill Mentah** | {len(df_ekstraksi):,} Baris |
| **Total Skill Mentah Unik** | {df_ekstraksi['extracted_skill'].nunique():,} Skill |
| **Total Record Normalisasi Skill** | {len(df_normalisasi):,} Baris |
| **Total Canonical Skill Unik** | {df_final['canonical_skill'].nunique():,} Skill |
| **Total Relasi Bersih Siap KG (`[:TEACHES]`)** | **{len(df_final):,}** Baris |
| **Rata-rata Skill per Kursus** | {df_course_master['total_taught_skills'].mean():.1f} Skill |

---

## 2. Struktur Sheet pada `{OUTPUT_EXCEL.name}`

1. **`Course_Master`**: `course_id`, `course_name`, `platform`, `level`, `total_taught_skills`
2. **`Course_Skill_Ekstraksi`**: `course_id`, `course_name`, `platform`, `level`, `extracted_skill`
3. **`Course_Skill_Normalisasi`**: `course_id`, `course_name`, `platform`, `level`, `extracted_skill`, `canonical_skill`, `similarity_score`, `status`
4. **`Course_Skill_Final`**: `course_id`, `course_name`, `platform`, `level`, `canonical_skill` (Clean untuk Knowledge Graph)

---

## 3. Sampel Data Course_Skill_Final
"""
    for _, r in df_final.head(10).iterrows():
        report_content += f"- **[{r['course_id']}] {r['course_name']}** ({r['platform']}) $\\rightarrow$ `TEACHES` $\\rightarrow$ **`{r['canonical_skill']}`**\n"

    with open(OUTPUT_REPORT, "w", encoding="utf-8") as f:
        f.write(report_content)
    print(f"  -> Laporan markdown tersimpan di: {OUTPUT_REPORT}")

    print("\n" + "=" * 65)
    print("OUTPUT PEMPROSESAN COURSE SELESAI DENGAN SUKSES!")
    print("=" * 65)


if __name__ == "__main__":
    build_course_output()
