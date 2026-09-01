"""
course_recommender.py — Tahap 15: Course Recommendation

Input:
  - output/career_ranking_result.csv (dari Tahap 13-14)
  - Neo4j Knowledge Graph (Course -[:TEACHES]-> Skill)

Metode:
  1. Untuk setiap student, ambil Top 5 Career (by career_rank ASC)
  2. Untuk setiap Student × Top-5 Career, ambil missing_skills
  3. Cari Course yang TEACHES setidaknya 1 missing skill
  4. Ranking: covered_missing_skill_count DESC

TIDAK menggunakan:
  - Jaccard / Skill Coverage
  - Weighted scores
  - Name-based similarity

Output:
  - output/course_recommendation_result.csv
  - Validation report di terminal
"""
import pandas as pd
import logging
import sys
import time
from pathlib import Path
from neo4j import GraphDatabase

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, OUTPUT_DIR, OUTPUT_KG_DIR

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

CSV_SEP = ';'
SKILL_SEP = ' | '
TOP_K_CAREERS = 5


class CourseRecommender:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def run_query(self, query, parameters=None):
        with self.driver.session() as session:
            result = session.run(query, parameters or {})
            return [record.data() for record in result]

    def get_courses_for_skills(self, missing_skills_list):
        """
        Cari semua Course yang TEACHES setidaknya 1 skill
        dari missing_skills_list.
        Returns: list of {course_id, course_name, platform, level,
                          covered_skills: [list]}
        """
        if not missing_skills_list:
            return []

        result = self.run_query(
            "UNWIND $skills AS skill_name "
            "MATCH (co:Course)-[:TEACHES]->(sk:Skill {name: skill_name}) "
            "RETURN co.course_id AS course_id, co.name AS course_name, "
            "       co.platform AS platform, co.level AS level, "
            "       collect(DISTINCT sk.name) AS covered_skills",
            {"skills": missing_skills_list}
        )
        return result

    def generate_recommendations(self):
        """Tahap 15: Generate course recommendations."""
        logger.info("=" * 60)
        logger.info("TAHAP 15: COURSE RECOMMENDATION")
        logger.info("=" * 60)

        # Load career ranking
        ranking_file = OUTPUT_KG_DIR / "career_ranking_result_v2.csv"
        if not ranking_file.exists():
            ranking_file = OUTPUT_DIR / "career_ranking_result_v2.csv"
        if not ranking_file.exists():
            ranking_file = OUTPUT_DIR / "career_ranking_result.csv"
        df_ranking = pd.read_csv(ranking_file, sep=CSV_SEP)
        logger.info(f"  Loaded: {len(df_ranking)} ranked pairs from {ranking_file.name}")

        # Filter Top-K careers per student
        df_top = df_ranking[df_ranking['career_rank'] <= TOP_K_CAREERS].copy()
        logger.info(f"  Top-{TOP_K_CAREERS} pairs: {len(df_top)}")
        logger.info(f"  Students: {df_top['student_id'].nunique()}")

        # Cache: precompute courses per skill set
        # (many students share similar missing skills)
        courses_cache = {}
        all_rows = []
        start_time = time.time()

        no_course_pairs = 0
        total_pairs = len(df_top)

        for idx, (_, row) in enumerate(df_top.iterrows()):
            sid = row['student_id']
            sname = row['student_name']
            career_rank = row['career_rank']
            career_name = row['career_name']
            rsg = row['relative_skill_gap']
            missing_count = row['missing_skill_count']
            missing_str = row['missing_skills']

            # Parse missing skills
            if pd.isna(missing_str) or missing_str == '':
                missing_skills = []
            else:
                missing_skills = [s.strip() for s in missing_str.split(SKILL_SEP)]

            if not missing_skills:
                no_course_pairs += 1
                continue

            # Cache key: frozenset of missing skills
            cache_key = frozenset(missing_skills)

            if cache_key not in courses_cache:
                courses_cache[cache_key] = self.get_courses_for_skills(
                    missing_skills
                )

            courses = courses_cache[cache_key]

            if not courses:
                no_course_pairs += 1
                continue

            # Build recommendation rows
            for course in courses:
                # Covered = Course skills ∩ Missing skills
                covered = sorted(set(course['covered_skills']) &
                                 set(missing_skills))

                all_rows.append({
                    'student_id': sid,
                    'student_name': sname,
                    'career_rank': career_rank,
                    'career_name': career_name,
                    'relative_skill_gap': rsg,
                    'missing_skill_count': missing_count,
                    'course_id': course['course_id'],
                    'course_name': course['course_name'],
                    'platform': course['platform'],
                    'level': course['level'],
                    'covered_missing_skill_count': len(covered),
                    'covered_missing_skills': SKILL_SEP.join(covered),
                })

            if (idx + 1) % 100 == 0 or (idx + 1) == total_pairs:
                elapsed = time.time() - start_time
                logger.info(f"  Processed {idx+1}/{total_pairs} pairs "
                             f"({elapsed:.1f}s)")

        df_rec = pd.DataFrame(all_rows)

        # Sort: per student+career, descending by covered count
        df_rec = df_rec.sort_values(
            by=['student_id', 'career_rank', 'covered_missing_skill_count',
                'course_name'],
            ascending=[True, True, False, True]
        ).reset_index(drop=True)

        # Simpan ke folder hasil_kg
        OUTPUT_KG_DIR.mkdir(parents=True, exist_ok=True)
        out_path = OUTPUT_KG_DIR / "course_recommendation_result.csv"
        df_rec.to_csv(out_path, index=False, sep=CSV_SEP)

        logger.info(f"\n  Output: {out_path}")
        logger.info(f"  Total recommendation rows: {len(df_rec)}")
        logger.info(f"  Pairs with no course: {no_course_pairs}/{total_pairs}")

        return df_rec, df_top

    def validate(self, df_rec, df_top):
        """Validation checks."""
        logger.info("")
        logger.info("=" * 60)
        logger.info("VALIDASI COURSE RECOMMENDATION")
        logger.info("=" * 60)

        errors = []

        # A. Every course teaches at least 1 missing skill
        logger.info("\n  [A] Every course teaches ≥1 missing skill:")
        zero_covered = df_rec[df_rec['covered_missing_skill_count'] == 0]
        if len(zero_covered) == 0:
            logger.info(f"  ✅ PASS: Semua {len(df_rec)} recommendations valid.")
        else:
            msg = f"  ❌ FAIL: {len(zero_covered)} recs dengan 0 covered skills!"
            logger.info(msg)
            errors.append(msg)

        # B. No course recommended because of matched skill
        logger.info("\n  [B] No course recommended for matched skill:")
        violation_count = 0
        # Sample check (full check expensive)
        sample_checks = df_rec.head(500)
        for _, rec in sample_checks.iterrows():
            covered = set(rec['covered_missing_skills'].split(SKILL_SEP)) \
                if rec['covered_missing_skills'] else set()

            # Get the matching top-career row
            top_row = df_top[
                (df_top['student_id'] == rec['student_id']) &
                (df_top['career_name'] == rec['career_name'])
            ]
            if len(top_row) == 0:
                continue
            top_row = top_row.iloc[0]

            matched = set(top_row['matched_skills'].split(SKILL_SEP)) \
                if pd.notna(top_row['matched_skills']) and top_row['matched_skills'] else set()

            overlap = covered & matched
            if overlap:
                violation_count += 1

        if violation_count == 0:
            logger.info(f"  ✅ PASS: No matched-skill violations (sample 500).")
        else:
            msg = f"  ❌ FAIL: {violation_count} violations!"
            logger.info(msg)
            errors.append(msg)

        # C. covered count == len(covered skills)
        logger.info("\n  [C] covered_count == len(covered_skills):")
        count_mismatches = 0
        for _, rec in df_rec.iterrows():
            skills = rec['covered_missing_skills'].split(SKILL_SEP) \
                if rec['covered_missing_skills'] else []
            actual = len([s for s in skills if s.strip()])
            if actual != rec['covered_missing_skill_count']:
                count_mismatches += 1

        if count_mismatches == 0:
            logger.info(f"  ✅ PASS: Semua {len(df_rec)} counts valid.")
        else:
            msg = f"  ❌ FAIL: {count_mismatches} count mismatches!"
            logger.info(msg)
            errors.append(msg)

        # D. Courses ranked DESC by covered_count per student×career
        logger.info("\n  [D] Courses ranked DESC by covered_count:")
        desc_errors = 0
        for (sid, career), group in df_rec.groupby(['student_id', 'career_name']):
            vals = group['covered_missing_skill_count'].values
            for j in range(1, len(vals)):
                if vals[j] > vals[j-1]:
                    desc_errors += 1
                    break

        if desc_errors == 0:
            logger.info(f"  ✅ PASS: All student×career groups sorted DESC.")
        else:
            msg = f"  ❌ FAIL: {desc_errors} groups not sorted DESC!"
            logger.info(msg)
            errors.append(msg)

        # E. Missing skills with at least one course
        logger.info("\n  [E/F] Missing skill coverage by courses:")
        all_missing = set()
        all_covered = set()
        for _, row in df_top.iterrows():
            if pd.notna(row['missing_skills']) and row['missing_skills']:
                for s in row['missing_skills'].split(SKILL_SEP):
                    all_missing.add(s.strip())
        for _, row in df_rec.iterrows():
            if row['covered_missing_skills']:
                for s in row['covered_missing_skills'].split(SKILL_SEP):
                    all_covered.add(s.strip())

        no_course = all_missing - all_covered
        has_course = all_missing & all_covered

        logger.info(f"  Total unique missing skills (Top-{TOP_K_CAREERS}): "
                     f"{len(all_missing)}")
        logger.info(f"  Missing skills WITH course : {len(has_course)} "
                     f"({len(has_course)/len(all_missing)*100:.1f}%)")
        logger.info(f"  Missing skills WITHOUT course: {len(no_course)} "
                     f"({len(no_course)/len(all_missing)*100:.1f}%)")

        if len(no_course) > 0:
            logger.info(f"  Skills without course (sample):")
            for s in sorted(no_course)[:15]:
                logger.info(f"    - {s}")
            if len(no_course) > 15:
                logger.info(f"    ... dan {len(no_course) - 15} lainnya")

        # G. Student×Career with no recommendation
        logger.info(f"\n  [G] Student×Career with no course recommendation:")
        rec_keys = set(
            zip(df_rec['student_id'], df_rec['career_name'])
        )
        top_keys = set(
            zip(df_top['student_id'], df_top['career_name'])
        )
        no_rec = top_keys - rec_keys
        logger.info(f"  Pairs with no recommendation: {len(no_rec)}/{len(top_keys)}")
        if len(no_rec) > 0 and len(no_rec) <= 10:
            for sid, career in sorted(no_rec):
                logger.info(f"    - {sid} × {career}")

        return errors

    def print_sample_recommendations(self, df_rec, df_top):
        """Show detailed recommendations for sample students."""
        logger.info("")
        logger.info("=" * 60)
        logger.info("SAMPLE RECOMMENDATIONS — DETAIL")
        logger.info("=" * 60)

        sample_students = ['S0001', 'S0050', 'S0100']

        for sid in sample_students:
            student_top = df_top[df_top['student_id'] == sid]
            if len(student_top) == 0:
                continue

            sname = student_top.iloc[0]['student_name']
            logger.info(f"\n  {'═' * 55}")
            logger.info(f"  {sname} ({sid})")
            logger.info(f"  {'═' * 55}")

            for _, career_row in student_top.iterrows():
                career = career_row['career_name']
                rank = career_row['career_rank']
                rsg = career_row['relative_skill_gap']
                missing_str = career_row['missing_skills']
                missing = missing_str.split(SKILL_SEP) if pd.notna(missing_str) and missing_str else []

                logger.info(f"\n  Career #{rank}: {career} (RSG: {rsg:.4f})")
                logger.info(f"  Missing Skills ({len(missing)}): "
                             f"{', '.join(sorted(missing))}")

                # Get recommendations for this pair
                recs = df_rec[
                    (df_rec['student_id'] == sid) &
                    (df_rec['career_name'] == career)
                ].head(5)

                if len(recs) == 0:
                    logger.info(f"  → Tidak ada course yang bisa menutup "
                                 f"missing skills.")
                    continue

                logger.info(f"  → Top {min(5, len(recs))} Recommended Courses:")
                for _, rec in recs.iterrows():
                    covered = rec['covered_missing_skills']
                    logger.info(f"    • {rec['course_name']} "
                                 f"[{rec['platform']}, {rec['level']}] "
                                 f"— covers {rec['covered_missing_skill_count']} "
                                 f"missing skill(s): {covered}")


def main():
    try:
        recommender = CourseRecommender(
            NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
        )
    except Exception as e:
        logger.error(f"❌ Gagal koneksi ke Neo4j: {e}")
        return

    try:
        # Generate recommendations
        df_rec, df_top = recommender.generate_recommendations()

        # Validate
        errors = recommender.validate(df_rec, df_top)

        # Sample output
        recommender.print_sample_recommendations(df_rec, df_top)

        # Summary
        logger.info("")
        logger.info("=" * 60)
        if len(errors) == 0:
            logger.info("TAHAP 15 SELESAI — SEMUA VALIDASI PASS ✅")
        else:
            logger.info(f"TAHAP 15 SELESAI — {len(errors)} ERROR ❌")
        logger.info("STOP: Menunggu review.")
        logger.info("=" * 60)

    finally:
        recommender.close()


if __name__ == "__main__":
    main()
