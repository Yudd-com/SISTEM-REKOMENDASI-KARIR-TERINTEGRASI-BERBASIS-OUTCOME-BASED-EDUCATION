"""
generate_job_output.py
======================
Script untuk menghasilkan file output lengkap Ekstraksi & Normalisasi Job:
File: DATA_JOB_EKSTRAKSI_DAN_NORMALISASI.xlsx

Struktur Sheet:
1. Job_Master              : Daftar posisi pekerjaan & total kebutuhan skill
2. Job_Skill_Ekstraksi     : Hasil ekstraksi skill mentah per lowongan
3. Job_Skill_Normalisasi   : Pemetaan ekstraksi -> canonical skill + similarity score & status
4. Job_Skill_Final         : Format clean siap Knowledge Graph (Job -> REQUIRES -> Skill)
"""

import os
import re
import unicodedata
from pathlib import Path
import pandas as pd

CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
PEMPROSESAN_DATA_DIR = PROJECT_ROOT / "Pemprosesan Data"

FILE_JOB = PEMPROSESAN_DATA_DIR / "Data Utama" / "job_dataset_clean.xlsx"
FILE_CANONICAL = PEMPROSESAN_DATA_DIR / "Normalisasi Skill" / "canonical_skill_master.xlsx"

OUTPUT_DIR = CURRENT_DIR
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_EXCEL = OUTPUT_DIR / "DATA_JOB_EKSTRAKSI_DAN_NORMALISASI.xlsx"
OUTPUT_REPORT = OUTPUT_DIR / "laporan_pemprosesan_job.md"


def clean_skill_str(s: str) -> str:
    """Pembersihan teks string untuk matching."""
    if pd.isna(s) or s is None:
        return ""
    s = unicodedata.normalize("NFKC", str(s))
    s = s.replace("\u2019", "'").replace("\u2018", "'").replace("\u201c", '"').replace("\u201d", '"')
    s = re.sub(r"^[*\s\-\.]+|[*\s\-\.\:\,]+$", "", s)
    s = re.sub(r"\s+", " ", s).strip().lower()
    return s


def build_job_output():
    print("=" * 65)
    print("MEMBANGUN OUTPUT EKSTRAKSI & NORMALISASI DATA JOB")
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

    # 2. Muat Data Job
    print("\n[2/4] Memuat data lowongan pekerjaan (Job & JobSkill)...")
    df_job_meta = pd.read_excel(FILE_JOB, sheet_name="Job")
    df_job_raw_skills = pd.read_excel(FILE_JOB, sheet_name="JobSkill")
    
    # Merge informasi job title
    df_job_joined = df_job_raw_skills.merge(df_job_meta, on="job_id", how="left")
    
    # 3. Bangun Sheet Ekstraksi, Normalisasi, dan Final
    print("\n[3/4] Melakukan pemetaan normalisasi...")
    ekstraksi_rows = []
    normalisasi_rows = []
    final_rows = []

    for _, r in df_job_joined.iterrows():
        job_id = str(r["job_id"]).strip()
        job_title = str(r.get("job_title", "")).strip()
        raw_skill = str(r.get("skill", "")).strip()
        clean_raw = clean_skill_str(raw_skill)
        
        if not clean_raw:
            continue

        # Sheet Ekstraksi
        ekstraksi_rows.append({
            "job_id": job_id,
            "job_title": job_title,
            "extracted_skill": clean_raw
        })

        # Sheet Normalisasi
        canon_skill = canon_lookup.get(clean_raw, clean_raw)
        sim_score = score_lookup.get(clean_raw, 1.0)
        status = status_lookup.get(clean_raw, "accepted")

        normalisasi_rows.append({
            "job_id": job_id,
            "job_title": job_title,
            "extracted_skill": clean_raw,
            "canonical_skill": canon_skill,
            "similarity_score": sim_score,
            "status": status
        })

        # Sheet Final (Clean Deduplicated)
        final_rows.append({
            "job_id": job_id,
            "job_title": job_title,
            "canonical_skill": canon_skill
        })

    df_ekstraksi = pd.DataFrame(ekstraksi_rows).drop_duplicates()
    df_normalisasi = pd.DataFrame(normalisasi_rows).drop_duplicates()
    df_final = pd.DataFrame(final_rows).drop_duplicates(subset=["job_id", "canonical_skill"])

    # Sheet Master Job
    df_job_master = df_final.groupby(["job_id", "job_title"]).size().reset_index(name="total_canonical_skills")
    
    # 4. Simpan ke File Excel Multi-Sheet
    print("\n[4/4] Menyimpan ke file Excel multi-sheet...")
    with pd.ExcelWriter(OUTPUT_EXCEL, engine="openpyxl") as writer:
        df_job_master.to_excel(writer, sheet_name="Job_Master", index=False)
        df_ekstraksi.to_excel(writer, sheet_name="Job_Skill_Ekstraksi", index=False)
        df_normalisasi.to_excel(writer, sheet_name="Job_Skill_Normalisasi", index=False)
        df_final.to_excel(writer, sheet_name="Job_Skill_Final", index=False)

    print(f"  -> File Excel tersimpan: {OUTPUT_EXCEL}")

    # Buat Laporan Markdown
    report_content = rf"""# Laporan Pemprosesan Data Job (Ekstraksi & Normalisasi)

**Waktu Pembuatan:** {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Target File:** `{OUTPUT_EXCEL.name}`  
**Lokasi Direktori:** `{OUTPUT_DIR}`

---

## 1. Ringkasan Statistik Data Job

| Metrik | Jumlah |
|---|---|
| **Total Posisi Pekerjaan (Job Master)** | {len(df_job_master):,} Lowongan |
| **Total Record Ekstraksi Skill Mentah** | {len(df_ekstraksi):,} Baris |
| **Total Skill Mentah Unik** | {df_ekstraksi['extracted_skill'].nunique():,} Skill |
| **Total Record Normalisasi Skill** | {len(df_normalisasi):,} Baris |
| **Total Canonical Skill Unik** | {df_final['canonical_skill'].nunique():,} Skill |
| **Total Relasi Bersih Siap KG (`[:REQUIRES]`)** | **{len(df_final):,}** Baris |
| **Rata-rata Skill per Pekerjaan** | {df_job_master['total_canonical_skills'].mean():.1f} Skill |

---

## 2. Struktur Sheet pada `{OUTPUT_EXCEL.name}`

1. **`Job_Master`**: `job_id`, `job_title`, `total_canonical_skills`
2. **`Job_Skill_Ekstraksi`**: `job_id`, `job_title`, `extracted_skill`
3. **`Job_Skill_Normalisasi`**: `job_id`, `job_title`, `extracted_skill`, `canonical_skill`, `similarity_score`, `status`
4. **`Job_Skill_Final`**: `job_id`, `job_title`, `canonical_skill` (Clean untuk Knowledge Graph)

---

## 3. Sampel Data Job_Skill_Final
"""
    for _, r in df_final.head(10).iterrows():
        report_content += f"- **[{r['job_id']}] {r['job_title']}** $\\rightarrow$ `REQUIRES` $\\rightarrow$ **`{r['canonical_skill']}`**\n"

    with open(OUTPUT_REPORT, "w", encoding="utf-8") as f:
        f.write(report_content)
    print(f"  -> Laporan markdown tersimpan di: {OUTPUT_REPORT}")

    print("\n" + "=" * 65)
    print("OUTPUT PEMPROSESAN JOB SELESAI DENGAN SUKSES!")
    print("=" * 65)


if __name__ == "__main__":
    build_job_output()
