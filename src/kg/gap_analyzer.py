"""
gap_analyzer.py — Tahap 11–12: Gap Analysis (Matched & Missing Skills)

Menghitung untuk setiap Student × Career:
  - Matched Skills = Student HAS_SKILL ∩ Career REQUIRES
  - Missing Skills = Career REQUIRES - Student HAS_SKILL

TIDAK menghitung:
  - Jaccard Similarity
  - Relative Skill Gap
  - Career Ranking
  - Course Recommendation

Output:
  - output/career_gap_raw.csv
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


class GapAnalyzer:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def run_query(self, query, parameters=None):
        with self.driver.session() as session:
            result = session.run(query, parameters or {})
            return [record.data() for record in result]

    # ==========================================================
    # TAHAP 11: MATCHED SKILLS
    # TAHAP 12: MISSING SKILLS
    # ==========================================================
    def compute_gap_analysis(self):
        """
        Untuk setiap Student × Career, hitung:
        - matched_skills = Student HAS_SKILL ∩ Career REQUIRES
        - missing_skills = Career REQUIRES - Student HAS_SKILL

        Menggunakan Cypher per-student untuk efisiensi memori.
        """
        logger.info("=" * 60)
        logger.info("TAHAP 11-12: GAP ANALYSIS")
        logger.info("=" * 60)

        # Ambil semua students
        students = self.run_query(
            "MATCH (s:Student) RETURN s.student_id AS sid, s.name AS name "
            "ORDER BY s.student_id"
        )
        logger.info(f"  Students: {len(students)}")

        # Ambil semua careers
        careers = self.run_query(
            "MATCH (c:Career) RETURN c.name AS name ORDER BY c.name"
        )
        logger.info(f"  Careers: {len(careers)}")
        logger.info(f"  Total pairs: {len(students) * len(careers)}")

        all_rows = []
        start_time = time.time()

        for i, student in enumerate(students):
            sid = student['sid']
            sname = student['name']

            # Ambil skill mahasiswa ini (satu query per student)
            student_skills_result = self.run_query(
                "MATCH (s:Student {student_id: $sid})-[:HAS_SKILL]->(sk:Skill) "
                "RETURN collect(sk.name) AS skills",
                {"sid": sid}
            )
            student_skills = set(student_skills_result[0]['skills'])

            # Ambil semua career dan required skills mereka (satu batch query)
            if i == 0:
                # Cache career skills (sama untuk semua student)
                career_skills_map = {}
                career_data = self.run_query(
                    "MATCH (c:Career)-[:REQUIRES]->(sk:Skill) "
                    "RETURN c.name AS career, collect(sk.name) AS skills"
                )
                for cd in career_data:
                    career_skills_map[cd['career']] = set(cd['skills'])

            # Hitung gap untuk setiap career
            for career_name, required_skills in career_skills_map.items():
                matched = student_skills & required_skills
                missing = required_skills - student_skills

                all_rows.append({
                    'student_id': sid,
                    'student_name': sname,
                    'student_skills': ' | '.join(sorted(student_skills)),
                    'student_skill_count': len(student_skills),
                    'career_name': career_name,
                    'required_skill_count': len(required_skills),
                    'matched_skill_count': len(matched),
                    'missing_skill_count': len(missing),
                    'required_skills': ' | '.join(sorted(required_skills)),
                    'matched_skills': ' | '.join(sorted(matched)),
                    'missing_skills': ' | '.join(sorted(missing)),
                })

            elapsed = time.time() - start_time
            if (i + 1) % 10 == 0 or (i + 1) == len(students):
                logger.info(f"  Processed {i+1}/{len(students)} students "
                             f"({elapsed:.1f}s)")

        df = pd.DataFrame(all_rows)

        # Simpan ke folder hasil_kg
        OUTPUT_KG_DIR.mkdir(parents=True, exist_ok=True)
        out_path = OUTPUT_KG_DIR / "career_gap_raw.csv"
        df.to_csv(out_path, index=False, sep=';')
        logger.info(f"\n  Output: {out_path}")
        logger.info(f"  Total rows: {len(df)}")

        return df

    # ==========================================================
    # VALIDASI
    # ==========================================================
    def validate_gap(self, df):
        """Sanity checks untuk gap analysis."""
        logger.info("")
        logger.info("=" * 60)
        logger.info("VALIDASI GAP ANALYSIS")
        logger.info("=" * 60)

        errors = []

        # A. matched + missing == required
        logger.info("\n  [A] matched + missing == required")
        df['sum_check'] = (df['matched_skill_count'] + df['missing_skill_count'])
        mismatches = df[df['sum_check'] != df['required_skill_count']]
        if len(mismatches) == 0:
            logger.info(f"  ✅ PASS: Semua {len(df)} pairs valid.")
        else:
            msg = f"  ❌ FAIL: {len(mismatches)} pairs tidak valid!"
            logger.info(msg)
            errors.append(msg)
            for _, row in mismatches.head(5).iterrows():
                logger.info(f"    {row['student_id']} × {row['career_name']}: "
                             f"matched={row['matched_skill_count']} + "
                             f"missing={row['missing_skill_count']} != "
                             f"required={row['required_skill_count']}")
        df.drop('sum_check', axis=1, inplace=True)

        # B & C. Cross-validation matched/missing terhadap graph
        # (Sample check — full check terlalu mahal)
        logger.info("\n  [B/C] Cross-validation matched/missing vs graph (sample)")
        sample_pairs = [
            ('S0001', 'data scientist'),
            ('S0001', 'backend developer - entry level'),
            ('S0050', 'data analyst'),
        ]
        for sid, career in sample_pairs:
            row = df[(df['student_id'] == sid) & (df['career_name'] == career)]
            if len(row) == 0:
                logger.info(f"  ⚠️ Pair ({sid}, {career}) tidak ditemukan")
                continue
            row = row.iloc[0]

            # Verifikasi via Neo4j
            matched_neo4j = self.run_query(
                "MATCH (s:Student {student_id: $sid})-[:HAS_SKILL]->(sk:Skill)"
                "<-[:REQUIRES]-(c:Career {name: $career}) "
                "RETURN collect(sk.name) AS skills",
                {"sid": sid, "career": career}
            )[0]['skills']

            missing_neo4j = self.run_query(
                "MATCH (c:Career {name: $career})-[:REQUIRES]->(sk:Skill) "
                "WHERE NOT (:Student {student_id: $sid})-[:HAS_SKILL]->(sk) "
                "RETURN collect(sk.name) AS skills",
                {"sid": sid, "career": career}
            )[0]['skills']

            csv_matched = set(row['matched_skills'].split(' | ')) if row['matched_skills'] else set()
            csv_missing = set(row['missing_skills'].split(' | ')) if row['missing_skills'] else set()

            neo4j_matched = set(matched_neo4j)
            neo4j_missing = set(missing_neo4j)

            match_ok = csv_matched == neo4j_matched
            missing_ok = csv_missing == neo4j_missing

            status = '✅' if (match_ok and missing_ok) else '❌'
            logger.info(f"  {status} {sid} × {career}:")
            logger.info(f"    Matched: CSV={len(csv_matched)}, "
                         f"Neo4j={len(neo4j_matched)}, "
                         f"match={'✅' if match_ok else '❌'}")
            logger.info(f"    Missing: CSV={len(csv_missing)}, "
                         f"Neo4j={len(neo4j_missing)}, "
                         f"match={'✅' if missing_ok else '❌'}")

            if not match_ok:
                errors.append(f"Matched mismatch: {sid} × {career}")
            if not missing_ok:
                errors.append(f"Missing mismatch: {sid} × {career}")

        # D. No overlap matched ∩ missing
        logger.info("\n  [D] matched_skills ∩ missing_skills == ∅")
        overlap_count = 0
        for _, row in df.iterrows():
            matched_set = set(row['matched_skills'].split(' | ')) if row['matched_skills'] else set()
            missing_set = set(row['missing_skills'].split(' | ')) if row['missing_skills'] else set()
            overlap = matched_set & missing_set
            if overlap:
                overlap_count += 1
                if overlap_count <= 3:
                    logger.info(f"  ❌ {row['student_id']} × {row['career_name']}: "
                                 f"overlap = {overlap}")

        if overlap_count == 0:
            logger.info(f"  ✅ PASS: Tidak ada overlap matched ∩ missing.")
        else:
            msg = f"  ❌ FAIL: {overlap_count} pairs memiliki overlap!"
            logger.info(msg)
            errors.append(msg)

        # E. Distribusi khusus
        logger.info("\n  [E] Distribusi khusus")

        zero_matched = df[df['matched_skill_count'] == 0]
        logger.info(f"  Pairs dengan 0 matched skills: {len(zero_matched)} "
                     f"({len(zero_matched)/len(df)*100:.1f}%)")

        full_matched = df[df['matched_skill_count'] == df['required_skill_count']]
        logger.info(f"  Pairs dengan 100% matched (0 missing): {len(full_matched)} "
                     f"({len(full_matched)/len(df)*100:.1f}%)")

        zero_missing = df[df['missing_skill_count'] == 0]
        logger.info(f"  Pairs dengan 0 missing skills: {len(zero_missing)} "
                     f"(sama dengan 100% matched = {len(full_matched)})")

        # Statistik umum
        logger.info("\n  [Statistik Umum]")
        logger.info(f"  Total pairs: {len(df)}")
        logger.info(f"  Unique students: {df['student_id'].nunique()}")
        logger.info(f"  Unique careers: {df['career_name'].nunique()}")
        logger.info(f"  Rata-rata matched per pair: "
                     f"{df['matched_skill_count'].mean():.2f}")
        logger.info(f"  Rata-rata missing per pair: "
                     f"{df['missing_skill_count'].mean():.2f}")
        logger.info(f"  Rata-rata required per career: "
                     f"{df['required_skill_count'].mean():.2f}")
        logger.info(f"  Max matched: {df['matched_skill_count'].max()}")
        logger.info(f"  Min matched: {df['matched_skill_count'].min()}")
        logger.info(f"  Max missing: {df['missing_skill_count'].max()}")

        return errors

    def print_sample_detail(self, df):
        """Tampilkan detail sample untuk manual check."""
        logger.info("")
        logger.info("=" * 60)
        logger.info("SAMPLE VALIDATION — DETAIL")
        logger.info("=" * 60)

        samples = [
            ('S0001', 'data scientist'),
            ('S0001', 'backend developer - entry level'),
            ('S0001', 'it project manager'),
            ('S0050', 'data analyst'),
            ('S0100', 'cybersecurity analyst'),
        ]

        for sid, career in samples:
            row = df[(df['student_id'] == sid) & (df['career_name'] == career)]
            if len(row) == 0:
                logger.info(f"\n  ⚠️ Pair ({sid}, {career}) tidak ditemukan")
                continue
            row = row.iloc[0]

            # Ambil student skills dari Neo4j
            s_skills = self.run_query(
                "MATCH (s:Student {student_id: $sid})-[:HAS_SKILL]->(sk:Skill) "
                "RETURN collect(sk.name) AS skills",
                {"sid": sid}
            )[0]['skills']

            # Ambil career required skills
            c_skills = self.run_query(
                "MATCH (c:Career {name: $career})-[:REQUIRES]->(sk:Skill) "
                "RETURN collect(sk.name) AS skills",
                {"career": career}
            )[0]['skills']

            matched = set(row['matched_skills'].split(' | ')) if row['matched_skills'] else set()
            missing = set(row['missing_skills'].split(' | ')) if row['missing_skills'] else set()

            sname = row['student_name']

            logger.info(f"\n  {'─' * 50}")
            logger.info(f"  {sname} ({sid}) × {career}")
            logger.info(f"  {'─' * 50}")
            logger.info(f"  Student Skills ({len(s_skills)}): "
                         f"{', '.join(sorted(s_skills)[:10])}...")
            logger.info(f"  Career Required Skills ({len(c_skills)}): "
                         f"{', '.join(sorted(c_skills))}")
            logger.info(f"  Matched Skills ({row['matched_skill_count']}): "
                         f"{', '.join(sorted(matched)) if matched else '-'}")
            logger.info(f"  Missing Skills ({row['missing_skill_count']}): "
                         f"{', '.join(sorted(missing)) if missing else '-'}")
            logger.info(f"  Check: {row['matched_skill_count']} + "
                         f"{row['missing_skill_count']} = "
                         f"{row['matched_skill_count'] + row['missing_skill_count']} "
                         f"== {row['required_skill_count']} "
                         f"{'✅' if row['matched_skill_count'] + row['missing_skill_count'] == row['required_skill_count'] else '❌'}")


def main():
    try:
        analyzer = GapAnalyzer(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    except Exception as e:
        logger.error(f"❌ Gagal koneksi ke Neo4j: {e}")
        return

    try:
        # Compute gap analysis
        df = analyzer.compute_gap_analysis()

        # Validate
        errors = analyzer.validate_gap(df)

        # Sample detail
        analyzer.print_sample_detail(df)

        # Summary
        logger.info("")
        logger.info("=" * 60)
        if len(errors) == 0:
            logger.info("TAHAP 11-12 SELESAI — SEMUA VALIDASI PASS ✅")
        else:
            logger.info(f"TAHAP 11-12 SELESAI — {len(errors)} ERROR DITEMUKAN ❌")
        logger.info("STOP: Menunggu approval sebelum Relative Skill Gap.")
        logger.info("=" * 60)

    finally:
        analyzer.close()


if __name__ == "__main__":
    main()
