"""
dataset_builder.py — Tahap 9: Bangun Dataset Final untuk Knowledge Graph

Membaca 3 file skill mentah + canonical_skill_master.csv,
mengganti semua skill dengan canonical_skill,
dan menghasilkan 3 dataset final + validation report.

Output:
  - output/student_skill_final.csv
  - output/career_skill_final.csv
  - output/course_skill_final.csv
  - Validation report di terminal
"""
import pandas as pd
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import OUTPUT_DIR

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)


def load_canonical_mapping():
    """
    Membaca canonical_skill_master.csv dan membangun lookup:
    (source, original_skill) -> canonical_skill
    
    Juga membuat lookup sederhana:
    original_skill -> canonical_skill (mengambil yang pertama ditemukan)
    """
    df = pd.read_csv(OUTPUT_DIR / "canonical_skill_master.csv")
    
    # Lookup per source
    source_lookup = {}
    for _, row in df.iterrows():
        key = (row['source'], row['original_skill'])
        source_lookup[key] = row['canonical_skill']
    
    # Lookup sederhana (tanpa source)
    simple_lookup = {}
    for _, row in df.iterrows():
        if row['original_skill'] not in simple_lookup:
            simple_lookup[row['original_skill']] = row['canonical_skill']
    
    return source_lookup, simple_lookup


def resolve_canonical(skill, source, source_lookup, simple_lookup):
    """
    Resolusi canonical skill. Prioritas:
    1. Lookup per source (OBE/Jobs/Course)
    2. Lookup sederhana (tanpa source)
    3. Skill itu sendiri (unmatched — jangan buang)
    """
    # Coba lookup per source dulu
    canonical = source_lookup.get((source, skill))
    if canonical:
        return canonical
    
    # Coba lookup sederhana
    canonical = simple_lookup.get(skill)
    if canonical:
        return canonical
    
    # Fallback: skill itu sendiri (unmatched, dipertahankan)
    return skill


def build_student_skill_final(source_lookup, simple_lookup):
    """
    Tahap 9a: Bangun student_skill_final.csv

    Input: obe_skills_raw.csv (student_id, student_name, [kampus], skill, score)
    Output: student_skill_final.csv (student_id, student_name, [kampus], canonical_skill, score)

    - Ganti skill → canonical_skill
    - Deduplikasi: jika satu mahasiswa punya canonical_skill sama dari skill berbeda,
      ambil score tertinggi
    """
    logger.info("=" * 60)
    logger.info("TAHAP 9a: Bangun student_skill_final.csv")
    logger.info("=" * 60)

    df = pd.read_csv(OUTPUT_DIR / "obe_skills_raw.csv")
    logger.info(f"  Input: {len(df)} baris, {df['skill'].nunique()} unique skills")

    # Deteksi kolom kampus (ada di multi-kampus mode)
    has_kampus = 'kampus' in df.columns
    if has_kampus:
        kampus_list = df['kampus'].unique().tolist()
        logger.info(f"  Kampus terdeteksi: {kampus_list}")

    # Map ke canonical
    df['canonical_skill'] = df['skill'].apply(
        lambda s: resolve_canonical(s, 'OBE', source_lookup, simple_lookup)
    )

    # Cek skill yang tidak ter-resolve (tetap sama)
    unresolved = df[df['skill'] == df['canonical_skill']]['skill'].unique()
    truly_unresolved = [s for s in unresolved
                        if ('OBE', s) not in source_lookup and s not in simple_lookup]
    if len(truly_unresolved) > 0:
        logger.info(f"  [WARNING] {len(truly_unresolved)} skill tidak ditemukan di master:")
        for s in truly_unresolved[:10]:
            logger.info(f"    - {s}")

    # Deduplikasi: per mahasiswa per canonical_skill, ambil score tertinggi
    group_cols = ['student_id', 'student_name', 'canonical_skill']
    if has_kampus:
        group_cols = ['student_id', 'student_name', 'kampus', 'canonical_skill']

    df_final = (df
                .groupby(group_cols)
                .agg(score=('score', 'max'))
                .reset_index())

    # Statistik
    logger.info(f"  Output: {len(df_final)} baris")
    logger.info(f"  Unique students: {df_final['student_id'].nunique()}")
    if has_kampus:
        for k in kampus_list:
            n = df_final[df_final['kampus'] == k]['student_id'].nunique()
            logger.info(f"    - {k}: {n} mahasiswa")
    logger.info(f"  Unique canonical skills: {df_final['canonical_skill'].nunique()}")
    logger.info(f"  Rata-rata skill per mahasiswa: "
                f"{df_final.groupby('student_id').size().mean():.1f}")
    logger.info(f"  Min skill per mahasiswa: "
                f"{df_final.groupby('student_id').size().min()}")
    logger.info(f"  Max skill per mahasiswa: "
                f"{df_final.groupby('student_id').size().max()}")

    out_path = OUTPUT_DIR / "student_skill_final.csv"
    df_final.to_csv(out_path, index=False)
    logger.info(f"  Disimpan: {out_path}")

    return df_final



def build_career_skill_final(source_lookup, simple_lookup):
    """
    Tahap 9b: Bangun career_skill_final.csv
    
    Input: job_skills_raw.csv (career_name, skill)
    Output: career_skill_final.csv (career_name, canonical_skill)
    
    - Ganti skill → canonical_skill
    - Deduplikasi: per career per canonical_skill (unique pairs saja)
    """
    logger.info("")
    logger.info("=" * 60)
    logger.info("TAHAP 9b: Bangun career_skill_final.csv")
    logger.info("=" * 60)
    
    df = pd.read_csv(OUTPUT_DIR / "job_skills_raw.csv")
    logger.info(f"  Input: {len(df)} baris, {df['skill'].nunique()} unique skills")
    
    # Map ke canonical
    df['canonical_skill'] = df['skill'].apply(
        lambda s: resolve_canonical(s, 'Jobs', source_lookup, simple_lookup)
    )
    
    # Deduplikasi: per career per canonical_skill
    df_final = df[['career_name', 'canonical_skill']].drop_duplicates()
    
    # --- DATA QUALITY CHECKS ---
    # 1. Cek null career_name
    null_career = df_final['career_name'].isna().sum()
    if null_career > 0:
        logger.info(f"  [ERROR] {null_career} rows dengan null career_name ditemukan!")
        logger.info(f"  [FIX] Menghapus {null_career} rows null career_name...")
        df_final = df_final.dropna(subset=['career_name'])
    else:
        logger.info(f"  [CHECK] Null career_name: 0 ✅")
    
    # 2. Cek null canonical_skill
    null_skill = df_final['canonical_skill'].isna().sum()
    if null_skill > 0:
        logger.info(f"  [ERROR] {null_skill} rows dengan null canonical_skill!")
        df_final = df_final.dropna(subset=['canonical_skill'])
    else:
        logger.info(f"  [CHECK] Null canonical_skill: 0 ✅")
    
    # 3. Cek duplicate (career_name + canonical_skill)
    dupes = df_final.duplicated(subset=['career_name', 'canonical_skill']).sum()
    if dupes > 0:
        logger.info(f"  [WARNING] {dupes} duplicate career+skill pairs ditemukan!")
        df_final = df_final.drop_duplicates(subset=['career_name', 'canonical_skill'])
    else:
        logger.info(f"  [CHECK] Duplicate career+skill: 0 ✅")
    
    # Cek career dengan 0 skill (seharusnya tidak ada)
    career_counts = df_final.groupby('career_name').size().reset_index(name='skill_count')
    zero_careers = career_counts[career_counts['skill_count'] == 0]
    if len(zero_careers) > 0:
        logger.info(f"  [CAUTION] {len(zero_careers)} career dengan 0 skill!")
    else:
        logger.info(f"  [CHECK] Career dengan 0 skill: 0 ✅")
    
    # Statistik
    logger.info(f"  Output: {len(df_final)} baris (valid career-skill pairs)")
    logger.info(f"  Unique careers: {df_final['career_name'].nunique()}")
    logger.info(f"  Unique canonical skills: {df_final['canonical_skill'].nunique()}")
    logger.info(f"  Rata-rata skill per career: "
                f"{career_counts['skill_count'].mean():.1f}")
    logger.info(f"  Min skill per career: "
                f"{career_counts['skill_count'].min()}")
    logger.info(f"  Max skill per career: "
                f"{career_counts['skill_count'].max()}")
    
    # Data quality: career outliers
    outliers = career_counts[career_counts['skill_count'] > 50]
    if len(outliers) > 0:
        logger.info(f"  [INFO] Career dengan > 50 canonical skills (outlier):")
        for _, o in outliers.iterrows():
            logger.info(f"    - {o['career_name']}: {o['skill_count']} skills")
    
    out_path = OUTPUT_DIR / "career_skill_final.csv"
    df_final.to_csv(out_path, index=False)
    logger.info(f"  Disimpan: {out_path}")
    
    return df_final


def build_course_skill_final(source_lookup, simple_lookup):
    """
    Tahap 9c: Bangun course_skill_final.csv
    
    Input: course_skills_raw.csv (course_id, course_name, platform, level, skill)
    Output: course_skill_final.csv (course_id, course_name, platform, level, canonical_skill)
    
    - Ganti skill → canonical_skill
    - Deduplikasi: per course per canonical_skill
    """
    logger.info("")
    logger.info("=" * 60)
    logger.info("TAHAP 9c: Bangun course_skill_final.csv")
    logger.info("=" * 60)
    
    df = pd.read_csv(OUTPUT_DIR / "course_skills_raw.csv")
    logger.info(f"  Input: {len(df)} baris, {df['skill'].nunique()} unique skills")
    
    # Map ke canonical
    df['canonical_skill'] = df['skill'].apply(
        lambda s: resolve_canonical(s, 'Course', source_lookup, simple_lookup)
    )
    
    # Deduplikasi: per course per canonical_skill
    df_final = df[['course_id', 'course_name', 'platform', 'level', 
                    'canonical_skill']].drop_duplicates(subset=['course_id', 'canonical_skill'])
    
    # Statistik
    logger.info(f"  Output: {len(df_final)} baris")
    logger.info(f"  Unique courses: {df_final['course_id'].nunique()}")
    logger.info(f"  Unique canonical skills: {df_final['canonical_skill'].nunique()}")
    logger.info(f"  Rata-rata skill per course: "
                f"{df_final.groupby('course_id').size().mean():.1f}")
    
    out_path = OUTPUT_DIR / "course_skill_final.csv"
    df_final.to_csv(out_path, index=False)
    logger.info(f"  Disimpan: {out_path}")
    
    return df_final


def validation_report(df_student, df_career, df_course):
    """
    Validation Report: Statistik dan cross-check sebelum Neo4j.
    """
    logger.info("")
    logger.info("=" * 60)
    logger.info("VALIDATION REPORT — DATASET FINAL")
    logger.info("=" * 60)
    
    # Kumpulkan unique canonical skills per dataset
    student_skills = set(df_student['canonical_skill'].unique())
    career_skills = set(df_career['canonical_skill'].unique())
    course_skills = set(df_course['canonical_skill'].unique())
    all_canonical = student_skills | career_skills | course_skills
    
    logger.info(f"\n  [1. JUMLAH ENTITAS]")
    logger.info(f"  Students          : {df_student['student_id'].nunique()}")
    logger.info(f"  Careers           : {df_career['career_name'].nunique()}")
    logger.info(f"  Courses           : {df_course['course_id'].nunique()}")
    logger.info(f"  Total Canonical Skills (Node Skill): {len(all_canonical)}")
    
    logger.info(f"\n  [2. SKILL PER SUMBER (CANONICAL)]")
    logger.info(f"  Student skills    : {len(student_skills)}")
    logger.info(f"  Career skills     : {len(career_skills)}")
    logger.info(f"  Course skills     : {len(course_skills)}")
    
    logger.info(f"\n  [3. OVERLAP CANONICAL SKILLS]")
    sc = student_skills & career_skills
    logger.info(f"  Student ∩ Career  : {len(sc)} "
                f"({len(sc)/len(student_skills)*100:.1f}% dari Student skills)")
    sco = student_skills & course_skills
    logger.info(f"  Student ∩ Course  : {len(sco)} "
                f"({len(sco)/len(student_skills)*100:.1f}% dari Student skills)")
    cc = career_skills & course_skills
    logger.info(f"  Career ∩ Course   : {len(cc)} "
                f"({len(cc)/len(career_skills)*100:.1f}% dari Career skills)")
    all3 = student_skills & career_skills & course_skills
    logger.info(f"  All Three         : {len(all3)} "
                f"({len(all3)/len(student_skills)*100:.1f}% dari Student skills)")
    
    logger.info(f"\n  [4. RELATIONSHIP COUNTS (UNTUK NEO4J)]")
    logger.info(f"  HAS_SKILL  (Student → Skill) : {len(df_student)}")
    logger.info(f"  REQUIRES   (Career → Skill)  : {len(df_career)}")
    logger.info(f"  TEACHES    (Course → Skill)   : {len(df_course)}")
    
    logger.info(f"\n  [5. DISTRIBUSI SKILL PER MAHASISWA]")
    student_dist = df_student.groupby('student_id').size()
    logger.info(f"  Min   : {student_dist.min()}")
    logger.info(f"  Max   : {student_dist.max()}")
    logger.info(f"  Mean  : {student_dist.mean():.1f}")
    logger.info(f"  Median: {student_dist.median():.1f}")
    
    logger.info(f"\n  [6. DISTRIBUSI SKILL PER CAREER]")
    career_dist = df_career.groupby('career_name').size()
    logger.info(f"  Min   : {career_dist.min()}")
    logger.info(f"  Max   : {career_dist.max()}")
    logger.info(f"  Mean  : {career_dist.mean():.1f}")
    logger.info(f"  Median: {career_dist.median():.1f}")
    
    logger.info(f"\n  [7. DISTRIBUSI SKILL PER COURSE]")
    course_dist = df_course.groupby('course_id').size()
    logger.info(f"  Min   : {course_dist.min()}")
    logger.info(f"  Max   : {course_dist.max()}")
    logger.info(f"  Mean  : {course_dist.mean():.1f}")
    logger.info(f"  Median: {course_dist.median():.1f}")
    
    # Analisis gap potensial
    logger.info(f"\n  [8. ANALISIS GAP POTENSIAL]")
    only_student = student_skills - career_skills
    logger.info(f"  Skill HANYA di Student (tidak ada Career yang membutuhkan):")
    logger.info(f"    Jumlah: {len(only_student)}")
    if len(only_student) > 0:
        for s in sorted(only_student)[:15]:
            logger.info(f"    - {s}")
        if len(only_student) > 15:
            logger.info(f"    ... dan {len(only_student) - 15} lainnya")
    
    only_career = career_skills - student_skills
    logger.info(f"\n  Skill HANYA di Career (tidak dimiliki mahasiswa manapun):")
    logger.info(f"    Jumlah: {len(only_career)}")
    logger.info(f"    (Ini adalah skill yang selalu menjadi 'missing skill')")
    
    missing_no_course = (career_skills - student_skills) - course_skills
    logger.info(f"\n  Skill Career yang tidak dimiliki mahasiswa DAN tidak ada course-nya:")
    logger.info(f"    Jumlah: {len(missing_no_course)}")
    logger.info(f"    (Missing skills yang TIDAK BISA ditutup oleh course manapun)")
    if len(missing_no_course) > 0:
        for s in sorted(missing_no_course)[:15]:
            logger.info(f"    - {s}")
        if len(missing_no_course) > 15:
            logger.info(f"    ... dan {len(missing_no_course) - 15} lainnya")
    
    # Contoh sample data
    logger.info(f"\n  [9. SAMPLE DATA]")
    sample_student = df_student[df_student['student_id'] == df_student['student_id'].iloc[0]]
    logger.info(f"\n  Sample: {sample_student['student_name'].iloc[0]} "
                f"({sample_student['student_id'].iloc[0]})")
    logger.info(f"  Skills ({len(sample_student)}):")
    for _, r in sample_student.head(10).iterrows():
        logger.info(f"    - {r['canonical_skill']} (score: {r['score']:.1f})")
    if len(sample_student) > 10:
        logger.info(f"    ... dan {len(sample_student) - 10} lainnya")
    
    sample_career = df_career[df_career['career_name'] == 'data scientist']
    if len(sample_career) > 0:
        logger.info(f"\n  Sample Career: data scientist")
        logger.info(f"  Required Skills ({len(sample_career)}):")
        for _, r in sample_career.iterrows():
            logger.info(f"    - {r['canonical_skill']}")
    
    logger.info("")
    logger.info("=" * 60)
    logger.info("TAHAP 9 SELESAI.")
    logger.info("Review validation report di atas.")
    logger.info("Jika approved, lanjut ke Tahap 10 (Neo4j Import).")
    logger.info("=" * 60)


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    logger.info("=" * 60)
    logger.info("TAHAP 9: BANGUN DATASET FINAL")
    logger.info("=" * 60)
    
    # Load canonical mapping
    source_lookup, simple_lookup = load_canonical_mapping()
    logger.info(f"  Canonical mapping loaded: {len(simple_lookup)} entries")
    
    # Build final datasets
    df_student = build_student_skill_final(source_lookup, simple_lookup)
    df_career = build_career_skill_final(source_lookup, simple_lookup)
    df_course = build_course_skill_final(source_lookup, simple_lookup)
    
    # Validation report
    validation_report(df_student, df_career, df_course)


if __name__ == "__main__":
    main()
