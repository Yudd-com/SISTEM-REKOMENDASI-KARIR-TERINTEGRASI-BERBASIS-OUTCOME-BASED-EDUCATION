"""
skill_extractor.py — Tahap 1–4: Data Cleaning, Skill Extraction, Splitting

Membaca 3 dataset Excel, membersihkan data, mengekstrak skill mentah,
melakukan splitting skill gabungan (di SEMUA sumber), dan menghasilkan
3 file CSV mentah.

Output:
  - output/obe_skills_raw.csv
  - output/job_skills_raw.csv
  - output/course_skills_raw.csv
"""
import pandas as pd
import logging
import sys

sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))
from config import (
    OBE_FILES, STUDENT_FILES, JOBS_FILE, COURSE_FILE, OUTPUT_DIR,
    OBE_SKILL_THRESHOLD, SKILL_SPLIT_MAP, COMPOUND_SKILL_SPLITS
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)


def split_skill(skill_name, split_map):
    """
    Jika skill merupakan gabungan (misal 'java/python'),
    pecah menjadi list individual. Jika tidak, kembalikan [skill].
    Mengecek terhadap OBE SKILL_SPLIT_MAP.
    """
    skill_lower = skill_name.strip().lower()
    if skill_lower in split_map:
        return split_map[skill_lower]
    return [skill_lower]


def split_compound(skill_name, compound_map):
    """
    Jika skill merupakan compound expression (misal 'python, go, java'),
    pecah menjadi list individual. Berlaku untuk SEMUA dataset.
    """
    skill_lower = skill_name.strip().lower()
    if skill_lower in compound_map:
        return compound_map[skill_lower]
    return [skill_lower]


def extract_obe_skills():
    """
    Tahap 1 & 4 (OBE): Baca data OBE dari MULTI-KAMPUS (Jakarta + Surabaya).

    Untuk setiap kampus:
      - OBE_FILES[kampus]: Referensi CLO (id_CLO, skill_technical)
      - STUDENT_FILES[kampus]: Nilai Mahasiswa (id_student, id_CLO, score)
    
    Flow per kampus:
      1. Load OBE reference (CLO -> skill_technical)
      2. Load nilai mahasiswa
      3. Join nilai + OBE via id_CLO
      4. Filter score >= threshold (50.01)
      5. Split skill gabungan
      6. Deduplikasi per mahasiswa per skill
    
    Gabungkan semua kampus -> obe_skills_raw.csv
    """
    logger.info("=" * 60)
    logger.info("TAHAP 1: Ekstraksi Skill OBE (Multi-Kampus)")
    logger.info("=" * 60)

    all_rows = []

    for kampus, obe_path in OBE_FILES.items():
        student_path = STUDENT_FILES[kampus]
        logger.info(f"\n  [Kampus: {kampus}]")
        logger.info(f"  OBE File     : {obe_path.name}")
        logger.info(f"  Student File : {student_path.name}")

        # Load OBE Reference (CLO -> skill_technical)
        df_obe = pd.read_excel(obe_path, sheet_name='Referensi_CLO')
        # Kolom: id_CLO, course_code, course_name, clo_code,
        #        clo_description, skill_domain, skill_technical
        logger.info(f"  OBE CLOs     : {df_obe['id_CLO'].nunique()} CLOs, "
                     f"{df_obe['skill_technical'].nunique()} unique skills")

        # Load Nilai Mahasiswa
        df_mhs = pd.read_excel(student_path, sheet_name='Daftar_Mahasiswa')
        df_scores = pd.read_excel(student_path, sheet_name='Nilai_Mahasiswa_per_CLO')
        # Kolom mhs: id_student, nama_mahasiswa, angkatan
        # Kolom scores: id_student, id_CLO, score

        logger.info(f"  Mahasiswa    : {df_mhs['id_student'].nunique()}")
        logger.info(f"  Score Records: {len(df_scores)}")

        # Filter berdasarkan threshold
        df_pass = df_scores[df_scores['score'] >= OBE_SKILL_THRESHOLD].copy()
        logger.info(f"  Lolos Threshold ({OBE_SKILL_THRESHOLD}): "
                     f"{len(df_pass)} / {len(df_scores)} "
                     f"({len(df_pass)/len(df_scores)*100:.1f}%)")

        # Join nilai dengan OBE reference via id_CLO
        df_joined = df_pass.merge(
            df_obe[['id_CLO', 'skill_technical']],
            on='id_CLO', how='left'
        )

        # Join nama mahasiswa
        df_joined = df_joined.merge(
            df_mhs[['id_student', 'nama_mahasiswa']],
            on='id_student', how='left'
        )

        # Split skill gabungan (OBE-specific splits + compound splits)
        rows = []
        for _, row in df_joined.iterrows():
            original_skill = str(row['skill_technical']).strip()
            if pd.isna(row['skill_technical']):
                continue
            # OBE-specific split map
            split_results = split_skill(original_skill, SKILL_SPLIT_MAP)
            # Compound splits
            final_skills = []
            for sk in split_results:
                final_skills.extend(split_compound(sk, COMPOUND_SKILL_SPLITS))

            for sk in final_skills:
                rows.append({
                    'student_id': row['id_student'],
                    'student_name': row['nama_mahasiswa'],
                    'kampus': kampus,
                    'clo': row['id_CLO'],
                    'original_skill': original_skill.lower(),
                    'skill': sk.strip().lower(),
                    'score': row['score']
                })

        df_expanded = pd.DataFrame(rows)

        # Deduplikasi: per mahasiswa per skill, ambil score tertinggi
        df_dedup = (
            df_expanded
            .groupby(['student_id', 'student_name', 'kampus', 'skill'])
            .agg(score=('score', 'max'))
            .reset_index()
        )

        logger.info(f"  Skill records setelah dedup: {len(df_dedup)}")
        logger.info(f"  Unique skills (kampus {kampus}): "
                     f"{df_dedup['skill'].nunique()}")

        all_rows.append(df_dedup)

    # Gabungkan semua kampus
    df_all = pd.concat(all_rows, ignore_index=True)

    # Deduplikasi lintas kampus (tidak mungkin karena ID berbeda, tapi jaga-jaga)
    df_all = (
        df_all
        .groupby(['student_id', 'student_name', 'kampus', 'skill'])
        .agg(score=('score', 'max'))
        .reset_index()
    )

    logger.info(f"\n  [TOTAL GABUNGAN]")
    logger.info(f"  Total Mahasiswa  : {df_all['student_id'].nunique()}")
    logger.info(f"  Total Skill Recs : {len(df_all)}")
    logger.info(f"  Unique OBE Skills: {df_all['skill'].nunique()}")

    # Simpan
    out_path = OUTPUT_DIR / "obe_skills_raw.csv"
    df_all.to_csv(out_path, index=False)
    logger.info(f"  Disimpan: {out_path}")

    return df_all


def extract_job_skills():
    """
    Tahap 1 (Jobs): Baca sheet Job + JobSkill.
    - Agregasi job_title: 1 career per judul, gabungkan semua skill
    - Split compound skills
    - Lowercase + trim
    """
    logger.info("")
    logger.info("=" * 60)
    logger.info("TAHAP 1: Ekstraksi Skill Jobs")
    logger.info("=" * 60)

    df_job = pd.read_excel(JOBS_FILE, sheet_name='Job')
    df_jobskill = pd.read_excel(JOBS_FILE, sheet_name='JobSkill')

    logger.info(f"  Job Postings      : {len(df_job)}")
    logger.info(f"  JobSkill Rows     : {len(df_jobskill)}")

    # Merge job_title ke skill
    df_merged = df_jobskill.merge(df_job, on='job_id', how='left')

    # --- DETEKSI ORPHAN JOB_ID ---
    # job_id yang ada di JobSkill tapi TIDAK ada di Job (tidak punya job_title)
    orphan_mask = df_merged['job_title'].isna()
    df_orphans = df_merged[orphan_mask].copy()
    df_valid = df_merged[~orphan_mask].copy()

    if len(df_orphans) > 0:
        orphan_ids = df_orphans['job_id'].unique()
        logger.info(f"  [ORPHAN DETECTED] {len(df_orphans)} JobSkill records "
                     f"dari {len(orphan_ids)} orphan job_id:")
        for oid in orphan_ids:
            orphan_skills = df_orphans[df_orphans['job_id'] == oid]['skill'].tolist()
            logger.info(f"    - job_id: {oid} ({len(orphan_skills)} skills)")
            for s in orphan_skills:
                logger.info(f"        • {s}")

        # Simpan orphan report
        orphan_report = df_orphans[['job_id', 'skill']].copy()
        orphan_report.columns = ['orphan_job_id', 'skill']
        orphan_path = OUTPUT_DIR / "orphan_jobskill_report.csv"
        orphan_report.to_csv(orphan_path, index=False)
        logger.info(f"  [ORPHAN SAVED] {orphan_path}")
        logger.info(f"  [ORPHAN EXCLUDED] {len(df_orphans)} records dieksklusi "
                     f"dari career_skill output.")
    else:
        logger.info(f"  [ORPHAN CHECK] Tidak ada orphan job_id. ✅")

    # Lanjut hanya dengan data valid (yang punya job_title)
    df_valid['career_name'] = df_valid['job_title'].str.strip().str.lower()
    df_valid['skill_raw'] = df_valid['skill'].str.strip().str.lower()

    # Split compound skills dan agregasi per career
    career_skills = {}
    for _, row in df_valid.iterrows():
        career = row['career_name']
        skill_raw = str(row['skill_raw'])
        if pd.isna(row['skill_raw']):
            continue
        # Split compound
        split_results = split_compound(skill_raw, COMPOUND_SKILL_SPLITS)
        if career not in career_skills:
            career_skills[career] = set()
        for sk in split_results:
            career_skills[career].add(sk.strip())

    # Expand ke flat table
    rows = []
    for career, skills in career_skills.items():
        for sk in skills:
            rows.append({
                'career_name': career,
                'skill': sk
            })

    df_flat = pd.DataFrame(rows)

    logger.info(f"  Unique Careers (setelah agregasi): {df_flat['career_name'].nunique()}")
    logger.info(f"  Unique Job Skills (setelah split): {df_flat['skill'].nunique()}")
    logger.info(f"  Total Career-Skill pairs: {len(df_flat)}")

    # Cek outlier (career dengan skill sangat banyak)
    skill_counts = df_flat.groupby('career_name').size().reset_index(name='skill_count')
    outliers = skill_counts[skill_counts['skill_count'] > 50]
    if len(outliers) > 0:
        logger.info(f"  [WARNING] Career dengan > 50 skills (outlier):")
        for _, o in outliers.iterrows():
            logger.info(f"    - {o['career_name']}: {o['skill_count']} skills")

    # Simpan
    out_path = OUTPUT_DIR / "job_skills_raw.csv"
    df_flat.to_csv(out_path, index=False)
    logger.info(f"  Disimpan: {out_path}")

    return df_flat


def extract_course_skills():
    """
    Tahap 1 (Course): Baca sheet Course + CourseSkill.
    - Handle header khusus (baris 1 = header asli)
    - Gunakan normalized_skill sebagai starting vocabulary
    - Split compound skills
    """
    logger.info("")
    logger.info("=" * 60)
    logger.info("TAHAP 1: Ekstraksi Skill Course")
    logger.info("=" * 60)

    # Course — header ada di baris 1
    df_course_raw = pd.read_excel(COURSE_FILE, sheet_name='Course')
    df_course = df_course_raw.iloc[1:].reset_index(drop=True)
    df_course.columns = ['course_id', 'course_name', 'platform', 'level']

    # CourseSkill — header ada di baris 1
    df_cskill_raw = pd.read_excel(COURSE_FILE, sheet_name='CourseSkill')
    df_cskill = df_cskill_raw.iloc[1:].reset_index(drop=True)
    df_cskill.columns = ['course_id', 'original_skill', 'normalized_skill']

    logger.info(f"  Jumlah Course     : {len(df_course)}")
    logger.info(f"  CourseSkill Rows  : {len(df_cskill)}")

    # Merge course info
    df_merged = df_cskill.merge(df_course, on='course_id', how='left')
    df_merged['original_skill_clean'] = df_merged['original_skill'].str.strip().str.lower()
    df_merged['normalized_skill_clean'] = df_merged['normalized_skill'].str.strip().str.lower()

    # Split compound skills dari normalized_skill
    rows = []
    for _, row in df_merged.iterrows():
        norm_skill = str(row['normalized_skill_clean'])
        if pd.isna(row['normalized_skill_clean']):
            continue
        split_results = split_compound(norm_skill, COMPOUND_SKILL_SPLITS)
        for sk in split_results:
            rows.append({
                'course_id': row['course_id'],
                'course_name': row['course_name'],
                'platform': row['platform'],
                'level': row['level'],
                'original_skill': row['original_skill_clean'],
                'skill': sk.strip()
            })

    df_expanded = pd.DataFrame(rows)

    # Deduplikasi per course per skill
    df_dedup = df_expanded.drop_duplicates(subset=['course_id', 'skill'])

    logger.info(f"  Unique Original Skills : {df_merged['original_skill_clean'].nunique()}")
    logger.info(f"  Unique Skills (setelah split): {df_dedup['skill'].nunique()}")

    # Simpan
    out_path = OUTPUT_DIR / "course_skills_raw.csv"
    df_dedup.to_csv(out_path, index=False)
    logger.info(f"  Disimpan: {out_path}")

    return df_dedup


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    df_obe = extract_obe_skills()
    df_jobs = extract_job_skills()
    df_course = extract_course_skills()

    # Ringkasan overlap
    obe_set = set(df_obe['skill'].unique())
    job_set = set(df_jobs['skill'].unique())
    course_set = set(df_course['skill'].unique())
    all_skills = obe_set | job_set | course_set

    logger.info("")
    logger.info("=" * 60)
    logger.info("RINGKASAN SEBELUM NORMALISASI")
    logger.info("=" * 60)
    logger.info(f"  OBE unique skills (setelah split)  : {len(obe_set)}")
    logger.info(f"  Jobs unique skills (setelah split)  : {len(job_set)}")
    logger.info(f"  Course unique skills (setelah split): {len(course_set)}")
    logger.info(f"  Total gabungan (sebelum normalisasi): {len(all_skills)}")
    logger.info(f"  Exact Match: OBE & Jobs    = {len(obe_set & job_set)}")
    logger.info(f"  Exact Match: OBE & Course  = {len(obe_set & course_set)}")
    logger.info(f"  Exact Match: Jobs & Course = {len(job_set & course_set)}")
    logger.info(f"  Exact Match: All Three     = {len(obe_set & job_set & course_set)}")


if __name__ == "__main__":
    main()
