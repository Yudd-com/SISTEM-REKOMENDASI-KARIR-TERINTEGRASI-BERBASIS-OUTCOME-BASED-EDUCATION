"""
career_ranker.py — Tahap 13–14: Relative Skill Gap & Career Ranking

Input:
  - output/career_gap_raw.csv (dari Tahap 11-12)

Metode:
  Relative Skill Gap = missing_skill_count / required_skill_count
  (referensi: "Building Knowledge Graphs and Recommender Systems
   for Suggesting Reskilling and Upskilling Options from the Web")

  Semakin kecil RSG → semakin cocok career dengan kompetensi mahasiswa.

TIDAK menggunakan:
  - Jaccard Similarity
  - Skill Coverage
  - matched_skill_count sebagai metode ranking utama

Output:
  - output/career_ranking_result.csv
  - Validation report di terminal
"""
import pandas as pd
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import OUTPUT_DIR, OUTPUT_KG_DIR

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

# Separator yang digunakan di career_gap_raw.csv
CSV_SEP = ';'
SKILL_SEP = ' | '


def main():
    logger.info("=" * 60)
    logger.info("TAHAP 13-14: RELATIVE SKILL GAP & CAREER RANKING")
    logger.info("=" * 60)

    # =========================================================
    # LOAD DATA
    # =========================================================
    gap_file = OUTPUT_KG_DIR / "career_gap_raw.csv"
    if not gap_file.exists():
        gap_file = OUTPUT_DIR / "career_gap_raw.csv"
    df = pd.read_csv(gap_file, sep=CSV_SEP)
    logger.info(f"  Input: {len(df)} student-career pairs from {gap_file.name}")
    logger.info(f"  Students: {df['student_id'].nunique()}")
    logger.info(f"  Careers: {df['career_name'].nunique()}")

    # =========================================================
    # TAHAP 13: RELATIVE SKILL GAP
    # =========================================================
    logger.info("")
    logger.info("=" * 60)
    logger.info("TAHAP 13: Hitung Relative Skill Gap")
    logger.info("=" * 60)

    # Cek careers dengan required_skill_count = 0
    zero_required = df[df['required_skill_count'] == 0]
    if len(zero_required) > 0:
        zero_careers = zero_required['career_name'].unique()
        logger.info(f"  [WARNING] {len(zero_careers)} career dengan "
                     f"required_skill_count = 0:")
        for c in zero_careers:
            logger.info(f"    - {c}")
        logger.info(f"  → {len(zero_required)} pairs dieksklusi dari ranking")

        # Eksklusi
        df_rankable = df[df['required_skill_count'] > 0].copy()
    else:
        logger.info(f"  Career dengan required_skill_count = 0: TIDAK ADA ✅")
        df_rankable = df.copy()

    # Hitung Relative Skill Gap
    df_rankable['relative_skill_gap'] = (
        df_rankable['missing_skill_count'] / df_rankable['required_skill_count']
    ).round(6)

    logger.info(f"\n  [Statistik RSG]")
    logger.info(f"  Rankable pairs: {len(df_rankable)}")
    logger.info(f"  Min RSG : {df_rankable['relative_skill_gap'].min():.6f}")
    logger.info(f"  Mean RSG: {df_rankable['relative_skill_gap'].mean():.6f}")
    logger.info(f"  Max RSG : {df_rankable['relative_skill_gap'].max():.6f}")
    logger.info(f"  Median  : {df_rankable['relative_skill_gap'].median():.6f}")

    # Distribusi RSG
    logger.info(f"\n  [Distribusi RSG]")
    bins = [0, 0.25, 0.50, 0.75, 0.90, 1.0, 1.01]
    labels = ['0.00-0.25', '0.25-0.50', '0.50-0.75', '0.75-0.90',
              '0.90-1.00', '1.00']
    df_rankable['rsg_bin'] = pd.cut(df_rankable['relative_skill_gap'],
                                     bins=bins, labels=labels,
                                     include_lowest=True, right=True)
    bin_counts = df_rankable['rsg_bin'].value_counts().sort_index()
    for bin_label, count in bin_counts.items():
        pct = count / len(df_rankable) * 100
        logger.info(f"    {bin_label}: {count:>6d} ({pct:.1f}%)")
    df_rankable.drop('rsg_bin', axis=1, inplace=True)

    # =========================================================
    # TAHAP 14: CAREER RANKING
    # =========================================================
    logger.info("")
    logger.info("=" * 60)
    logger.info("TAHAP 14: Career Ranking per Student")
    logger.info("=" * 60)

    # Sort: per student, ascending RSG (terkecil = paling cocok)
    # Tie-breaking (approved):
    #   1. relative_skill_gap ASC  (primary)
    #   2. matched_skill_count DESC (prefer more matched skills)
    #   3. required_skill_count DESC (prefer more complex career)
    df_ranked = df_rankable.sort_values(
        by=['student_id', 'relative_skill_gap',
            'matched_skill_count', 'required_skill_count'],
        ascending=[True, True, False, False]
    ).reset_index(drop=True)

    # Assign career_rank per student
    df_ranked['career_rank'] = (
        df_ranked.groupby('student_id').cumcount() + 1
    )

    # Reorder columns
    cols = ['student_id', 'student_name', 'career_rank', 'career_name',
            'required_skill_count', 'matched_skill_count',
            'missing_skill_count', 'relative_skill_gap',
            'required_skills', 'matched_skills', 'missing_skills']
    df_ranked = df_ranked[cols]

    # Simpan sebagai v2 ke folder hasil_kg
    OUTPUT_KG_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_KG_DIR / "career_ranking_result_v2.csv"
    df_ranked.to_csv(out_path, index=False, sep=CSV_SEP)
    logger.info(f"  Output: {out_path}")
    logger.info(f"  Total ranked pairs: {len(df_ranked)}")

    # =========================================================
    # V1 VS V2 COMPARISON
    # =========================================================
    logger.info("")
    logger.info("=" * 60)
    logger.info("V1 vs V2 COMPARISON")
    logger.info("=" * 60)

    v1_path = OUTPUT_DIR / "career_ranking_result.csv"
    if v1_path.exists():
        df_v1 = pd.read_csv(v1_path, sep=CSV_SEP)

        # 1. How many students have changed Top-5 careers?
        changed_students = 0
        for sid in df_ranked['student_id'].unique():
            v1_top5 = set(df_v1[
                (df_v1['student_id'] == sid) & (df_v1['career_rank'] <= 5)
            ]['career_name'])
            v2_top5 = set(df_ranked[
                (df_ranked['student_id'] == sid) & (df_ranked['career_rank'] <= 5)
            ]['career_name'])
            if v1_top5 != v2_top5:
                changed_students += 1

        logger.info(f"\n  [1] Students with changed Top-5 careers: "
                     f"{changed_students}/100")

        # 2. How many career positions changed?
        v1_top5_all = df_v1[df_v1['career_rank'] <= 5][
            ['student_id', 'career_rank', 'career_name']
        ].set_index(['student_id', 'career_rank'])
        v2_top5_all = df_ranked[df_ranked['career_rank'] <= 5][
            ['student_id', 'career_rank', 'career_name']
        ].set_index(['student_id', 'career_rank'])

        merged = v1_top5_all.join(v2_top5_all, lsuffix='_v1', rsuffix='_v2')
        position_changes = (merged['career_name_v1'] != merged['career_name_v2']).sum()
        logger.info(f"  [2] Career positions changed in Top-5: "
                     f"{position_changes}/{len(merged)}")

        # 3. Unique careers in Top-5
        v1_unique = df_v1[df_v1['career_rank'] <= 5]['career_name'].nunique()
        v2_unique = df_ranked[df_ranked['career_rank'] <= 5]['career_name'].nunique()
        logger.info(f"  [3] Unique careers in Top-5: v1={v1_unique}, v2={v2_unique}")

        # List them
        v2_top5_careers = sorted(
            df_ranked[df_ranked['career_rank'] <= 5]['career_name'].unique()
        )
        for c in v2_top5_careers:
            count = df_ranked[
                (df_ranked['career_rank'] <= 5) & (df_ranked['career_name'] == c)
            ]['student_id'].nunique()
            logger.info(f"    - {c}: {count}/100 students")
    else:
        logger.info("  v1 file not found, skipping comparison.")

    # 4. Top-10 for sample students
    logger.info(f"\n  [4] Top-10 Career Ranking v2 — Sample Students:")
    sample_students = ['S0001', 'S0050', 'S0100']

    for sid in sample_students:
        student_df = df_ranked[df_ranked['student_id'] == sid]
        if len(student_df) == 0:
            continue

        sname = student_df.iloc[0]['student_name']
        top10 = student_df.head(10)

        logger.info(f"\n  {sname} ({sid}) — Top 10 (v2):")
        logger.info(f"  {'Rank':>4s}  {'RSG':>8s}  {'Match':>5s}  "
                     f"{'Miss':>5s}  {'Req':>5s}  Career")
        logger.info(f"  {'─'*4}  {'─'*8}  {'─'*5}  {'─'*5}  {'─'*5}  {'─'*30}")

        for _, row in top10.iterrows():
            logger.info(f"  {row['career_rank']:4d}  "
                         f"{row['relative_skill_gap']:8.4f}  "
                         f"{row['matched_skill_count']:5d}  "
                         f"{row['missing_skill_count']:5d}  "
                         f"{row['required_skill_count']:5d}  "
                         f"{row['career_name']}")

    # =========================================================
    # VALIDATION
    # =========================================================
    logger.info("")
    logger.info("=" * 60)
    logger.info("VALIDASI CAREER RANKING")
    logger.info("=" * 60)

    errors = []

    # 1. Total counts
    logger.info(f"\n  [1] Total student-career pairs: {len(df)}")
    logger.info(f"  [2] Total ranked pairs: {len(df_ranked)}")
    logger.info(f"  [3] Careers excluded (req=0): {len(zero_required)}")
    logger.info(f"      Diff: {len(df) - len(df_ranked)}")

    # 4. RSG stats
    logger.info(f"\n  [4] RSG Statistics:")
    logger.info(f"    Min : {df_ranked['relative_skill_gap'].min():.6f}")
    logger.info(f"    Mean: {df_ranked['relative_skill_gap'].mean():.6f}")
    logger.info(f"    Max : {df_ranked['relative_skill_gap'].max():.6f}")

    # 5. Top 10 career for 5 sample students
    logger.info(f"\n  [5] Top 10 Career Ranking — Sample Students:")
    sample_students = ['S0001', 'S0010', 'S0025', 'S0050', 'S0100']

    for sid in sample_students:
        student_df = df_ranked[df_ranked['student_id'] == sid]
        if len(student_df) == 0:
            logger.info(f"\n  ⚠️ Student {sid} tidak ditemukan")
            continue

        sname = student_df.iloc[0]['student_name']
        top10 = student_df.head(10)

        logger.info(f"\n  {sname} ({sid}) — Top 10:")
        logger.info(f"  {'Rank':>4s}  {'RSG':>8s}  {'Match':>5s}  "
                     f"{'Miss':>5s}  {'Req':>5s}  Career")
        logger.info(f"  {'─'*4}  {'─'*8}  {'─'*5}  {'─'*5}  {'─'*5}  {'─'*30}")

        for _, row in top10.iterrows():
            logger.info(f"  {row['career_rank']:4d}  "
                         f"{row['relative_skill_gap']:8.4f}  "
                         f"{row['matched_skill_count']:5d}  "
                         f"{row['missing_skill_count']:5d}  "
                         f"{row['required_skill_count']:5d}  "
                         f"{row['career_name']}")

    # 6. Verify ascending order per student
    logger.info(f"\n  [6] Verify ranking is ascending by RSG per student:")
    ascending_errors = 0
    for sid, group in df_ranked.groupby('student_id'):
        rsg_values = group['relative_skill_gap'].values
        for j in range(1, len(rsg_values)):
            if rsg_values[j] < rsg_values[j-1]:
                ascending_errors += 1
                if ascending_errors <= 3:
                    logger.info(f"  ❌ {sid}: rank {j} RSG={rsg_values[j-1]} > "
                                 f"rank {j+1} RSG={rsg_values[j]}")

    if ascending_errors == 0:
        logger.info(f"  ✅ PASS: Semua {df_ranked['student_id'].nunique()} "
                     f"students memiliki ranking ascending.")
    else:
        msg = f"  ❌ FAIL: {ascending_errors} ascending violations!"
        logger.info(msg)
        errors.append(msg)

    # 7. Verify RSG = missing / required
    logger.info(f"\n  [7] Verify RSG = missing_skill_count / required_skill_count:")
    df_ranked['rsg_check'] = (
        df_ranked['missing_skill_count'] / df_ranked['required_skill_count']
    ).round(6)
    rsg_mismatches = df_ranked[
        (df_ranked['relative_skill_gap'] - df_ranked['rsg_check']).abs() > 1e-5
    ]
    if len(rsg_mismatches) == 0:
        logger.info(f"  ✅ PASS: Semua {len(df_ranked)} RSG values valid.")
    else:
        msg = f"  ❌ FAIL: {len(rsg_mismatches)} RSG mismatches!"
        logger.info(msg)
        errors.append(msg)
    df_ranked.drop('rsg_check', axis=1, inplace=True)

    # 8. Verify no Jaccard or Skill Coverage
    logger.info(f"\n  [8] Verify no Jaccard / Skill Coverage:")
    jaccard_cols = [c for c in df_ranked.columns
                    if 'jaccard' in c.lower() or 'coverage' in c.lower()]
    if len(jaccard_cols) == 0:
        logger.info(f"  ✅ PASS: Tidak ada kolom Jaccard/Coverage.")
    else:
        msg = f"  ❌ FAIL: Kolom terlarang ditemukan: {jaccard_cols}"
        logger.info(msg)
        errors.append(msg)

    # Summary
    logger.info("")
    logger.info("=" * 60)
    if len(errors) == 0:
        logger.info("TAHAP 13-14 SELESAI — SEMUA VALIDASI PASS ✅")
    else:
        logger.info(f"TAHAP 13-14 SELESAI — {len(errors)} ERROR ❌")
    logger.info("STOP: Menunggu approval sebelum Course Recommendation.")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
