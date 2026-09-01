"""
auto_skill_extractor.py
=======================
Modul ekstraksi skill otomatis berbasis NLP & Rule-Free Tokenization.

Dataset Input:
1. Pemprosesan Data/Data Utama/PARSING_JAKARTA.xlsx
2. Pemprosesan Data/Data Utama/PARSING_SURABAYA.xlsx
3. Pemprosesan Data/Ekstraksi Skill/RPS_skill_extracted_20260809_185306.csv (khusus subset ITS)
4. Pemprosesan Data/Data Utama/job_dataset_clean.xlsx
5. Pemprosesan Data/Data Utama/course_master_combined.xlsx (atau Online_Course_clean.xlsx)

Output Target:
- Pemprosesan Data/Ekstraksi Skill/skill_extraction_result.xlsx
"""

import os
import re
import unicodedata
from pathlib import Path
import pandas as pd
import nltk

try:
    nltk.data.find("corpora/stopwords")
except LookupError:
    nltk.download("stopwords", quiet=True)

from nltk.corpus import stopwords

CURRENT_DIR = Path(__file__).resolve().parent
DATA_UTAMA_DIR = CURRENT_DIR / "Data Utama"
EKSTRAKSI_DIR = CURRENT_DIR / "Ekstraksi Skill"
EKSTRAKSI_DIR.mkdir(parents=True, exist_ok=True)

FILE_PARSING_JKT = DATA_UTAMA_DIR / "PARSING_JAKARTA.xlsx"
FILE_PARSING_SBY = DATA_UTAMA_DIR / "PARSING_SURABAYA.xlsx"
FILE_RPS_CSV = EKSTRAKSI_DIR / "RPS_skill_extracted_20260809_185306.csv"
FILE_JOB = DATA_UTAMA_DIR / "job_dataset_clean.xlsx"
FILE_COURSE_MASTER = DATA_UTAMA_DIR / "course_master_combined.xlsx"
FILE_ONLINE_COURSE = CURRENT_DIR.parent / "data" / "Online_Course_clean.xlsx"

OUTPUT_EXTRACTION_XLSX = EKSTRAKSI_DIR / "skill_extraction_result.xlsx"

# Indonesian & English stop phrases to strip from extracted CLO phrases
STOPWORDS_ID = set(stopwords.words("indonesian")) if "indonesian" in stopwords.fileids() else set()
COMMON_ACTION_VERBS = {
    "mampu", "memahami", "menjelaskan", "menerapkan", "menggunakan", "merancang",
    "membuat", "mengidentifikasi", "menganalisis", "menguraikan", "mendemonstrasikan",
    "menjabarkan", "membedakan", "menguji", "mengembangkan", "melakukan", "memanfaatkan",
    "serta", "dan", "atau", "dari", "dalam", "pada", "untuk", "dengan", "secara",
    "berbasis", "terkait", "sebagai", "melalui", "terhadap", "hasil", "studi", "kasus",
    "konsep", "dasar", "dasardasar", "prinsip", "metode", "teknik", "cara", "jenis",
    "jenisjenis", "tingkat", "proses", "tahapan", "siklus", "kebutuhan", "mahasiswa"
}


def clean_text(text: str) -> str:
    """Membersihkan teks string unicode, spasi, dan karakter aneh."""
    if pd.isna(text) or text is None:
        return ""
    s = unicodedata.normalize("NFKC", str(text))
    s = s.replace("\u2019", "'").replace("\u2018", "'").replace("\u201c", '"').replace("\u201d", '"')
    s = s.replace("\u2013", "-").replace("\u2014", "-")
    s = re.sub(r"[\r\n\t]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def clean_skill_ultimate(s: str) -> str:
    """Membersihkan teks skill secara menyeluruh dari tanda baca, token aneh, dan nomor urut."""
    if pd.isna(s) or s is None:
        return ""
    s = unicodedata.normalize("NFKC", str(s))
    
    # 1. Fix placeholder tokens
    s = re.sub(r'__cicd__', 'ci/cd', s, flags=re.IGNORECASE)
    s = re.sub(r'__ccpp__', 'c/c++', s, flags=re.IGNORECASE)
    s = re.sub(r'__tcpip__', 'tcp/ip', s, flags=re.IGNORECASE)
    s = re.sub(r'__uiux__', 'ui/ux', s, flags=re.IGNORECASE)
    s = re.sub(r'__dotnet__', '.net', s, flags=re.IGNORECASE)
    s = re.sub(r'__cplusplus__', 'c++', s, flags=re.IGNORECASE)
    s = re.sub(r'__csharp__', 'c#', s, flags=re.IGNORECASE)
    s = re.sub(r'__io__', 'i/o', s, flags=re.IGNORECASE)
    
    # 2. Hapus nomor urut di awal seperti '1.', '2.', '12.', 'a.', '- '
    s = re.sub(r'^\s*[\d]+[\.\)\-]\s*', '', s)
    s = re.sub(r'^\s*[a-zA-Z][\.\)]\s*', '', s)
    
    # 3. Hapus kurung buka/tutup yang tidak lengkap atau sisa penjelasan dalam kurung
    s = re.sub(r'\s*\([^)]*\)?', '', s)
    s = re.sub(r'\s*\[[^\]]*\]?', '', s)
    s = re.sub(r'[\(\)\[\]\{\}\<\>\"\'`]', ' ', s)
    
    # 4. Hapus tanda baca di awal dan akhir kecuali .net, c#, c++
    s = re.sub(r'^[^a-zA-Z0-9\.\#\+]+', '', s)
    s = re.sub(r'[^a-zA-Z0-9\.\#\+]+$', '', s)
    
    # 5. Hapus tanda baca di tengah yang aneh
    s = re.sub(r'[:;|_~!?*]+', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip().lower()
    return s


def auto_split_compound_skill(raw_skill: str) -> list[str]:
    """
    Memecah skill majemuk secara otomatis berdasarkan delimiter alami
    (koma, titik koma, garis miring, bullet points, ampersand).
    """
    cleaned = clean_text(raw_skill)
    if not cleaned:
        return []

    placeholders = {
        "ci/cd": "PROTECTED_CICD",
        "tcp/ip": "PROTECTED_TCPIP",
        "ui/ux": "PROTECTED_UIUX",
        "i/o": "PROTECTED_IO",
        "c/c++": "PROTECTED_CCPP",
        ".net": "PROTECTED_DOTNET",
        "c++": "PROTECTED_CPLUSPLUS",
        "c#": "PROTECTED_CSHARP"
    }

    text_lower = cleaned.lower()
    for pattern, placeholder in placeholders.items():
        text_lower = text_lower.replace(pattern, placeholder)

    # Split berdasarkan koma, titik koma, slash, pipe, bullet
    parts = re.split(r"[,;|\u2022\u00b7/]+", text_lower)
    
    extracted = []
    for p in parts:
        # Kembalikan placeholder
        for pattern, placeholder in placeholders.items():
            p = p.replace(placeholder, pattern).replace(placeholder.lower(), pattern)
        
        cleaned_p = clean_skill_ultimate(p)
        if len(cleaned_p) >= 2 and not cleaned_p.isdigit():
            extracted.append(cleaned_p)

    return extracted if extracted else [clean_skill_ultimate(cleaned)]



def extract_skills_from_clo_text(full_clo_text: str) -> list[str]:
    """
    Mengekstrak entitas skill dari narasi kalimat CLO secara otomatis.
    1. Hapus metadata prefix seperti 'Hasil: [CLO 1-Sub CLO 01]'
    2. Pisahkan klausa berdasarkan kata hubung (serta, dan, lalu, koma)
    3. Hapus action verb di awal klausa dan ambil frasa teknis inti
    """
    text = clean_text(full_clo_text)
    if not text:
        return []

    # Hapus prefix header CLO
    text = re.sub(r"^Hasil:\s*\[[^\]]+\]\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^[A-Z0-9_\-]+:\s*", "", text)

    # Pisahkan berdasarkan tanda koma, titik koma, 'serta', 'dan', 'lalu'
    clauses = re.split(r"[,;]|\s+serta\s+|\s+dan\s+|\s+lalu\s+", text, flags=re.IGNORECASE)
    
    skills = []
    for clause in clauses:
        clause_clean = clean_text(clause)
        if not clause_clean:
            continue

        words = clause_clean.split()
        # Filter kata kerja umum di awal kalimat
        start_idx = 0
        while start_idx < len(words) and words[start_idx].lower() in COMMON_ACTION_VERBS:
            start_idx += 1
        
        remaining_words = words[start_idx:]
        if remaining_words:
            candidate = " ".join(remaining_words).strip(" .:,;!?")
            # Hapus stopwords berlebih di ujung
            candidate = re.sub(r"^[*\s\-\.]+|[*\s\-\.\:\,]+$", "", candidate).strip()
            
            # Jika kandidat memiliki panjang masuk akal (antara 2 hingga 6 kata)
            if 2 <= len(candidate) <= 80 and len(candidate.split()) <= 6:
                # Lakukan split majemuk jika ada koma/garis miring internal
                sub_skills = auto_split_compound_skill(candidate)
                for s in sub_skills:
                    # Jangan masukkan jika hanya stopword tunggal
                    if s not in COMMON_ACTION_VERBS and len(s) > 2:
                        skills.append(s)

    return list(dict.fromkeys(skills))


def run_extraction():
    print("=" * 65)
    print("MEMULAI EKSTRAKSI SKILL OTOMATIS BERBASIS NLP (RULE-FREE)")
    print("=" * 65)

    # 1. Ekstraksi dari PARSING_JAKARTA.xlsx
    print("\n[1/5] Mengekstrak skill dari PARSING_JAKARTA.xlsx...")
    df_pj = pd.read_excel(FILE_PARSING_JKT)
    # Temukan kolom teks CLO (biasanya kolom dengan teks panjang)
    col_matkul_jkt = df_pj.columns[0]
    col_clo_jkt = df_pj.columns[2] if len(df_pj.columns) > 2 else df_pj.columns[-1]

    jkt_extracted = []
    for _, row in df_pj.iloc[1:].iterrows():
        matkul = clean_text(row[col_matkul_jkt])
        clo_text = clean_text(row[col_clo_jkt])
        extracted = extract_skills_from_clo_text(clo_text)
        for sk in extracted:
            jkt_extracted.append({
                "campus": "Tel-U Jakarta",
                "course_name": matkul,
                "extracted_skill": sk,
                "original_context": clo_text
            })
    df_jkt_res = pd.DataFrame(jkt_extracted).drop_duplicates(subset=["campus", "course_name", "extracted_skill"])
    print(f"  -> Ekstraksi Jakarta: {len(df_jkt_res):,} skill records ({df_jkt_res['extracted_skill'].nunique():,} unik)")

    # 2. Ekstraksi dari PARSING_SURABAYA.xlsx
    print("\n[2/5] Mengekstrak skill dari PARSING_SURABAYA.xlsx...")
    df_ps = pd.read_excel(FILE_PARSING_SBY)
    col_matkul_sby = df_ps.columns[0]
    col_clo_sby = df_ps.columns[2] if len(df_ps.columns) > 2 else df_ps.columns[-1]

    sby_extracted = []
    for _, row in df_ps.iloc[1:].iterrows():
        matkul = clean_text(row[col_matkul_sby])
        clo_text = clean_text(row[col_clo_sby])
        extracted = extract_skills_from_clo_text(clo_text)
        for sk in extracted:
            sby_extracted.append({
                "campus": "Tel-U Surabaya",
                "course_name": matkul,
                "extracted_skill": sk,
                "original_context": clo_text
            })
    df_sby_res = pd.DataFrame(sby_extracted).drop_duplicates(subset=["campus", "course_name", "extracted_skill"])
    print(f"  -> Ekstraksi Surabaya: {len(df_sby_res):,} skill records ({df_sby_res['extracted_skill'].nunique():,} unik)")

    # 3. Ekstraksi Khusus Subset ITS dari RPS_skill_extracted_*.csv
    print("\n[3/5] Mengambil subset kurikulum ITS dari RPS_skill_extracted_*.csv...")
    its_extracted = []
    if FILE_RPS_CSV.exists():
        df_rps = pd.read_csv(FILE_RPS_CSV, sep=";")
        df_its = df_rps[df_rps["source"].astype(str).str.upper() == "ITS"].copy()
        for _, row in df_its.iterrows():
            raw_sk = clean_text(row["skill_text"])
            orig_clo = clean_text(row["original_clo"])
            sub_skills = auto_split_compound_skill(raw_sk)
            for sk in sub_skills:
                if len(sk) > 2 and sk not in COMMON_ACTION_VERBS:
                    its_extracted.append({
                        "source": "ITS",
                        "kode_mk": row.get("kode_mk", ""),
                        "clo_id": row.get("clo_id", ""),
                        "extracted_skill": sk,
                        "skill_type": row.get("skill_type", "HSkill"),
                        "original_clo": orig_clo
                    })
    df_its_res = pd.DataFrame(its_extracted).drop_duplicates(subset=["source", "kode_mk", "extracted_skill"])
    print(f"  -> Ekstraksi ITS: {len(df_its_res):,} skill records ({df_its_res['extracted_skill'].nunique():,} unik)")

    # 4. Ekstraksi Skill Pasar Kerja (Job Dataset)
    print("\n[4/5] Mengekstrak skill dari job_dataset_clean.xlsx...")
    job_extracted = []
    df_job_skills = pd.read_excel(FILE_JOB, sheet_name="JobSkill")
    df_jobs = pd.read_excel(FILE_JOB, sheet_name="Job")
    df_job_merged = df_job_skills.merge(df_jobs, on="job_id", how="left")
    
    for _, row in df_job_merged.iterrows():
        raw_sk = clean_text(row["skill"])
        job_title = clean_text(row["job_title"])
        sub_skills = auto_split_compound_skill(raw_sk)
        for sk in sub_skills:
            if len(sk) > 1:
                job_extracted.append({
                    "job_id": row["job_id"],
                    "job_title": job_title,
                    "extracted_skill": sk
                })
    df_job_res = pd.DataFrame(job_extracted).drop_duplicates(subset=["job_title", "extracted_skill"])
    print(f"  -> Ekstraksi Job Skills: {len(df_job_res):,} records ({df_job_res['extracted_skill'].nunique():,} unik)")

    # 5. Ekstraksi Skill Kursus (Course Dataset)
    print("\n[5/5] Mengekstrak skill dari katalog course...")
    course_extracted = []
    if FILE_ONLINE_COURSE.exists():
        df_cskill = pd.read_excel(FILE_ONLINE_COURSE, sheet_name="CourseSkill", skiprows=1, header=None)
        df_cskill.columns = ["course_id", "original_skill", "normalized_skill"]
        for _, row in df_cskill.iterrows():
            raw_sk = clean_text(row["original_skill"])
            sub_skills = auto_split_compound_skill(raw_sk)
            for sk in sub_skills:
                if len(sk) > 1:
                    course_extracted.append({
                        "course_id": row["course_id"],
                        "extracted_skill": sk
                    })
    df_course_res = pd.DataFrame(course_extracted).drop_duplicates(subset=["course_id", "extracted_skill"])
    print(f"  -> Ekstraksi Course Skills: {len(df_course_res):,} records ({df_course_res['extracted_skill'].nunique():,} unik)")

    # Gabungkan Seluruh Skill Unik Mentah (Raw Vocabulary)
    all_raw_list = []
    for sk in df_jkt_res["extracted_skill"].unique():
        all_raw_list.append({"skill": sk, "source": "Tel-U Jakarta"})
    for sk in df_sby_res["extracted_skill"].unique():
        all_raw_list.append({"skill": sk, "source": "Tel-U Surabaya"})
    for sk in df_its_res["extracted_skill"].unique():
        all_raw_list.append({"skill": sk, "source": "ITS"})
    for sk in df_job_res["extracted_skill"].unique():
        all_raw_list.append({"skill": sk, "source": "Job Market"})
    for sk in df_course_res["extracted_skill"].unique():
        all_raw_list.append({"skill": sk, "source": "Online Course"})

    df_combined_raw = pd.DataFrame(all_raw_list)
    print(f"\nTotal Keseluruhan Skill Unik Mentah: {df_combined_raw['skill'].nunique():,} skill")

    # Simpan ke Excel Multi-Sheet
    with pd.ExcelWriter(OUTPUT_EXTRACTION_XLSX, engine="openpyxl") as writer:
        df_jkt_res.to_excel(writer, sheet_name="TelU_Jakarta", index=False)
        df_sby_res.to_excel(writer, sheet_name="TelU_Surabaya", index=False)
        df_its_res.to_excel(writer, sheet_name="ITS_Extracted", index=False)
        df_job_res.to_excel(writer, sheet_name="Job_Skills", index=False)
        df_course_res.to_excel(writer, sheet_name="Course_Skills", index=False)
        df_combined_raw.to_excel(writer, sheet_name="All_Raw_Combined", index=False)

    print(f"\n[OK] Hasil ekstraksi otomatis tersimpan di: {OUTPUT_EXTRACTION_XLSX}")
    print("=" * 65)


if __name__ == "__main__":
    run_extraction()
