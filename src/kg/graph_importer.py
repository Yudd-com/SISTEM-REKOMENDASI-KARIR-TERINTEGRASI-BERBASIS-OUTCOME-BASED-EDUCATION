"""
graph_importer.py — Tahap 10: Import Dataset Final ke Neo4j Knowledge Graph

Input (HANYA 3 file final):
  - output/student_skill_final.csv
  - output/career_skill_final.csv
  - output/course_skill_final.csv

Node: Student, Career, Skill, Course
Relationship: HAS_SKILL, REQUIRES, TEACHES

Proses bertahap:
  STEP 1: Buat constraints
  STEP 2: Import Student + Skill + HAS_SKILL
  STEP 3: Import Career + REQUIRES
  STEP 4: Import Course + TEACHES
  STEP 5: Graph Validation
  STEP 6: Tampilkan hasil validation → STOP

Script ini IDEMPOTENT — menggunakan MERGE, bukan CREATE.
Dapat dijalankan berkali-kali tanpa duplikasi.
"""
import pandas as pd
import logging
import sys
from pathlib import Path
from neo4j import GraphDatabase

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, OUTPUT_DIR, OUTPUT_NORM_DIR, DATA_CLEAN_DIR

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

# CSV delimiter
CSV_SEP = ';'

def get_norm_file(fname):
    """Cari file normalisasi di output/normalisasi_skill/, output/, atau data_clean/normalized/."""
    candidates = [
        OUTPUT_NORM_DIR / fname,
        OUTPUT_DIR / fname,
        DATA_CLEAN_DIR / "normalized" / fname
    ]
    for p in candidates:
        if p.exists():
            return p
    return candidates[0]


class KnowledgeGraphImporter:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        logger.info(f"  Connected to Neo4j: {uri}")

    def close(self):
        self.driver.close()

    def run_query(self, query, parameters=None):
        """Jalankan satu Cypher query."""
        with self.driver.session() as session:
            result = session.run(query, parameters or {})
            return [record.data() for record in result]

    def run_query_count(self, query, parameters=None):
        """Jalankan query dan return single count."""
        results = self.run_query(query, parameters)
        if results:
            return list(results[0].values())[0]
        return 0

    # ==========================================================
    # STEP 1: CONSTRAINTS
    # ==========================================================
    def create_constraints(self):
        """Buat uniqueness constraints untuk mencegah duplikasi node."""
        logger.info("")
        logger.info("=" * 60)
        logger.info("STEP 1: Membuat Constraints")
        logger.info("=" * 60)

        constraints = [
            ("Student", "student_id",
             "CREATE CONSTRAINT student_unique IF NOT EXISTS "
             "FOR (s:Student) REQUIRE s.student_id IS UNIQUE"),
            ("Career", "name",
             "CREATE CONSTRAINT career_unique IF NOT EXISTS "
             "FOR (c:Career) REQUIRE c.name IS UNIQUE"),
            ("Skill", "name",
             "CREATE CONSTRAINT skill_unique IF NOT EXISTS "
             "FOR (sk:Skill) REQUIRE sk.name IS UNIQUE"),
            ("Course", "course_id",
             "CREATE CONSTRAINT course_unique IF NOT EXISTS "
             "FOR (co:Course) REQUIRE co.course_id IS UNIQUE"),
        ]

        for label, prop, query in constraints:
            try:
                self.run_query(query)
                logger.info(f"  ✅ Constraint {label}.{prop} created/exists")
            except Exception as e:
                logger.info(f"  ⚠️ Constraint {label}.{prop}: {e}")

    # ==========================================================
    # STEP 2: IMPORT STUDENT + SKILL + HAS_SKILL
    # ==========================================================
    def import_students(self):
        """Import Student nodes, Skill nodes, dan HAS_SKILL relationships."""
        logger.info("")
        logger.info("=" * 60)
        logger.info("STEP 2: Import Student + Skill + HAS_SKILL")
        logger.info("=" * 60)

        df = pd.read_csv(get_norm_file("student_skill_final.csv"), sep=CSV_SEP)
        logger.info(f"  Input: {len(df)} baris")
        logger.info(f"  Unique students: {df['student_id'].nunique()}")
        logger.info(f"  Unique skills: {df['canonical_skill'].nunique()}")

        # Import dalam batch
        batch_size = 500
        total = len(df)
        imported = 0

        for start in range(0, total, batch_size):
            batch = df.iloc[start:start + batch_size]
            records = batch.to_dict('records')

            query = """
            UNWIND $records AS row
            MERGE (s:Student {student_id: row.student_id})
            ON CREATE SET s.name = row.student_name
            MERGE (sk:Skill {name: row.canonical_skill})
            MERGE (s)-[r:HAS_SKILL]->(sk)
            ON CREATE SET r.score = row.score
            """
            self.run_query(query, {"records": records})
            imported += len(records)
            logger.info(f"  Imported {imported}/{total}")

        # Verifikasi
        student_count = self.run_query_count("MATCH (s:Student) RETURN count(s) AS c")
        skill_count = self.run_query_count("MATCH (sk:Skill) RETURN count(sk) AS c")
        has_skill_count = self.run_query_count(
            "MATCH ()-[r:HAS_SKILL]->() RETURN count(r) AS c")

        logger.info(f"  Hasil: Students={student_count}, "
                     f"Skills={skill_count}, HAS_SKILL={has_skill_count}")

    # ==========================================================
    # STEP 3: IMPORT CAREER + REQUIRES
    # ==========================================================
    def import_careers(self):
        """Import Career nodes dan REQUIRES relationships."""
        logger.info("")
        logger.info("=" * 60)
        logger.info("STEP 3: Import Career + REQUIRES")
        logger.info("=" * 60)

        df = pd.read_csv(get_norm_file("career_skill_final.csv"), sep=CSV_SEP)
        logger.info(f"  Input: {len(df)} baris")
        logger.info(f"  Unique careers: {df['career_name'].nunique()}")
        logger.info(f"  Unique skills: {df['canonical_skill'].nunique()}")

        batch_size = 500
        total = len(df)
        imported = 0

        for start in range(0, total, batch_size):
            batch = df.iloc[start:start + batch_size]
            records = batch.to_dict('records')

            query = """
            UNWIND $records AS row
            MERGE (c:Career {name: row.career_name})
            MERGE (sk:Skill {name: row.canonical_skill})
            MERGE (c)-[:REQUIRES]->(sk)
            """
            self.run_query(query, {"records": records})
            imported += len(records)
            logger.info(f"  Imported {imported}/{total}")

        # Verifikasi
        career_count = self.run_query_count("MATCH (c:Career) RETURN count(c) AS c")
        requires_count = self.run_query_count(
            "MATCH ()-[r:REQUIRES]->() RETURN count(r) AS c")

        logger.info(f"  Hasil: Careers={career_count}, REQUIRES={requires_count}")

    # ==========================================================
    # STEP 4: IMPORT COURSE + TEACHES
    # ==========================================================
    def import_courses(self):
        """Import Course nodes dan TEACHES relationships."""
        logger.info("")
        logger.info("=" * 60)
        logger.info("STEP 4: Import Course + TEACHES")
        logger.info("=" * 60)

        df = pd.read_csv(get_norm_file("course_skill_final.csv"), sep=CSV_SEP)
        logger.info(f"  Input: {len(df)} baris")
        logger.info(f"  Unique courses: {df['course_id'].nunique()}")
        logger.info(f"  Unique skills: {df['canonical_skill'].nunique()}")

        batch_size = 500
        total = len(df)
        imported = 0

        for start in range(0, total, batch_size):
            batch = df.iloc[start:start + batch_size]
            records = batch.to_dict('records')

            query = """
            UNWIND $records AS row
            MERGE (co:Course {course_id: row.course_id})
            ON CREATE SET co.name = row.course_name,
                          co.platform = row.platform,
                          co.level = row.level
            MERGE (sk:Skill {name: row.canonical_skill})
            MERGE (co)-[:TEACHES]->(sk)
            """
            self.run_query(query, {"records": records})
            imported += len(records)
            logger.info(f"  Imported {imported}/{total}")

        # Verifikasi
        course_count = self.run_query_count("MATCH (co:Course) RETURN count(co) AS c")
        teaches_count = self.run_query_count(
            "MATCH ()-[r:TEACHES]->() RETURN count(r) AS c")

        logger.info(f"  Hasil: Courses={course_count}, TEACHES={teaches_count}")

    # ==========================================================
    # STEP 5: GRAPH VALIDATION
    # ==========================================================
    def validate_graph(self):
        """Validasi graph setelah import."""
        logger.info("")
        logger.info("=" * 60)
        logger.info("STEP 5: GRAPH VALIDATION")
        logger.info("=" * 60)

        # Expected counts — multi-kampus (Jakarta + Surabaya + ITS, 300 mahasiswa)
        expected = {
            'Student': 300,
            'Career': 496,
            'Course': 1069,
            'Skill': 1796,
            'HAS_SKILL': 19890,
            'REQUIRES': 5505,
            'TEACHES': 10554,
        }

        results = {}

        # 1-4. Node counts
        logger.info("\n  [1-4. NODE COUNTS]")
        for label in ['Student', 'Career', 'Course', 'Skill']:
            count = self.run_query_count(
                f"MATCH (n:{label}) RETURN count(n) AS c")
            exp = expected[label]
            status = '✅' if count == exp else '❌'
            results[label] = count
            logger.info(f"  {status} {label}: {count} (expected: {exp})")

        # 5-7. Relationship counts
        logger.info("\n  [5-7. RELATIONSHIP COUNTS]")
        for rel_type in ['HAS_SKILL', 'REQUIRES', 'TEACHES']:
            count = self.run_query_count(
                f"MATCH ()-[r:{rel_type}]->() RETURN count(r) AS c")
            exp = expected[rel_type]
            status = '✅' if count == exp else '❌'
            results[rel_type] = count
            logger.info(f"  {status} {rel_type}: {count} (expected: {exp})")

        # 8. Student tanpa skill
        logger.info("\n  [8. Student tanpa skill]")
        no_skill_students = self.run_query_count(
            "MATCH (s:Student) WHERE NOT (s)-[:HAS_SKILL]->() "
            "RETURN count(s) AS c")
        status = '✅' if no_skill_students == 0 else '❌'
        logger.info(f"  {status} Student tanpa HAS_SKILL: {no_skill_students}")

        # 9. Career tanpa required skill
        logger.info("\n  [9. Career tanpa required skill]")
        no_skill_careers = self.run_query_count(
            "MATCH (c:Career) WHERE NOT (c)-[:REQUIRES]->() "
            "RETURN count(c) AS c")
        status = '✅' if no_skill_careers == 0 else '❌'
        logger.info(f"  {status} Career tanpa REQUIRES: {no_skill_careers}")

        # 10. Course tanpa taught skill
        logger.info("\n  [10. Course tanpa taught skill]")
        no_skill_courses = self.run_query_count(
            "MATCH (co:Course) WHERE NOT (co)-[:TEACHES]->() "
            "RETURN count(co) AS c")
        status = '✅' if no_skill_courses == 0 else '❌'
        logger.info(f"  {status} Course tanpa TEACHES: {no_skill_courses}")

        # 11. Skill yang tidak terhubung ke node lain (isolated)
        logger.info("\n  [11. Skill tanpa koneksi (isolated)]")
        isolated_skills = self.run_query_count(
            "MATCH (sk:Skill) "
            "WHERE NOT (sk)<-[:HAS_SKILL]-() "
            "AND NOT (sk)<-[:REQUIRES]-() "
            "AND NOT (sk)<-[:TEACHES]-() "
            "RETURN count(sk) AS c")
        logger.info(f"  Isolated skills: {isolated_skills}")

        # 12. Duplicate relationships
        logger.info("\n  [12. Duplicate relationships]")
        for rel_type in ['HAS_SKILL', 'REQUIRES', 'TEACHES']:
            dupe_query = f"""
            MATCH (a)-[r:{rel_type}]->(b)
            WITH a, b, count(r) AS cnt
            WHERE cnt > 1
            RETURN count(*) AS c
            """
            dupe_count = self.run_query_count(dupe_query)
            status = '✅' if dupe_count == 0 else '❌'
            logger.info(f"  {status} Duplicate {rel_type}: {dupe_count}")

        # 13. Null properties
        logger.info("\n  [13. Null properties]")
        null_checks = [
            ("Student", "student_id",
             "MATCH (s:Student) WHERE s.student_id IS NULL RETURN count(s) AS c"),
            ("Student", "name",
             "MATCH (s:Student) WHERE s.name IS NULL RETURN count(s) AS c"),
            ("Career", "name",
             "MATCH (c:Career) WHERE c.name IS NULL RETURN count(c) AS c"),
            ("Skill", "name",
             "MATCH (sk:Skill) WHERE sk.name IS NULL RETURN count(sk) AS c"),
            ("Course", "course_id",
             "MATCH (co:Course) WHERE co.course_id IS NULL RETURN count(co) AS c"),
            ("Course", "name",
             "MATCH (co:Course) WHERE co.name IS NULL RETURN count(co) AS c"),
        ]
        for label, prop, query in null_checks:
            null_count = self.run_query_count(query)
            status = '✅' if null_count == 0 else '❌'
            logger.info(f"  {status} {label}.{prop} IS NULL: {null_count}")

        # 14. Contoh graph Student → Skill → Career
        logger.info("\n  [14. Contoh: Student → Skill → Career]")
        sample_path = self.run_query("""
            MATCH (s:Student {student_id: 'J0001'})-[:HAS_SKILL]->(sk:Skill)
                  <-[:REQUIRES]-(c:Career)
            RETURN s.name AS student, sk.name AS skill, c.name AS career
            LIMIT 5
        """)
        if sample_path:
            for row in sample_path:
                logger.info(f"  ({row['student']}) "
                             f"--HAS_SKILL--> ({row['skill']}) "
                             f"<--REQUIRES-- ({row['career']})")
        else:
            logger.info("  ⚠️ Tidak ada path Student→Skill→Career ditemukan")

        # 15. Contoh graph Missing Skill → Course
        logger.info("\n  [15. Contoh: Career Required Skill → Course (TEACHES)]")
        sample_course = self.run_query("""
            MATCH (c:Career {name: 'data scientist'})-[:REQUIRES]->(sk:Skill)
                  <-[:TEACHES]-(co:Course)
            RETURN c.name AS career, sk.name AS skill,
                   co.name AS course, co.platform AS platform
            LIMIT 5
        """)
        if sample_course:
            for row in sample_course:
                logger.info(f"  ({row['career']}) "
                             f"--REQUIRES--> ({row['skill']}) "
                             f"<--TEACHES-- ({row['course']} [{row['platform']}])")
        else:
            logger.info("  ⚠️ Tidak ada path Career→Skill→Course ditemukan")

        # Summary
        logger.info("")
        logger.info("=" * 60)
        logger.info("GRAPH VALIDATION SUMMARY")
        logger.info("=" * 60)

        all_match = True
        for key, exp_val in expected.items():
            actual = results.get(key, -1)
            match = '✅' if actual == exp_val else '❌ MISMATCH'
            if actual != exp_val:
                all_match = False
            logger.info(f"  {match} {key}: expected={exp_val}, actual={actual}")

        logger.info(f"\n  Overall: {'✅ ALL MATCH' if all_match else '❌ MISMATCHES FOUND'}")

        logger.info("")
        logger.info("=" * 60)
        logger.info("STEP 6: STOP — Menunggu approval sebelum Gap Analysis")
        logger.info("=" * 60)

        return all_match


def main():
    logger.info("=" * 60)
    logger.info("TAHAP 10: KNOWLEDGE GRAPH IMPORT")
    logger.info("=" * 60)

    # Cek Neo4j availability
    try:
        importer = KnowledgeGraphImporter(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    except Exception as e:
        logger.error(f"  ❌ Gagal koneksi ke Neo4j: {e}")
        logger.error(f"  Pastikan Neo4j berjalan di {NEO4J_URI}")
        return

    try:
        # Clear existing data (fresh import)
        logger.info("\n  [CLEAN] Menghapus data graph sebelumnya...")
        importer.run_query("MATCH (n) DETACH DELETE n")
        logger.info("  ✅ Graph dibersihkan")

        # STEP 1: Constraints
        importer.create_constraints()

        # STEP 2: Import Students
        importer.import_students()

        # STEP 3: Import Careers
        importer.import_careers()

        # STEP 4: Import Courses
        importer.import_courses()

        # STEP 5-6: Validation & Stop
        importer.validate_graph()

    except Exception as e:
        logger.error(f"  ❌ Error: {e}")
        raise
    finally:
        importer.close()


if __name__ == "__main__":
    main()
