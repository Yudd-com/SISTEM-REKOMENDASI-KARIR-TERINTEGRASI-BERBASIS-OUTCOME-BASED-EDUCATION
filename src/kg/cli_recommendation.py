"""
cli_recommendation.py — CLI Sistem Rekomendasi Course

Input: Nama mahasiswa (langsung ketik, tanpa NIM/ID)
Output: Top Career + Missing Skills + Course Recommendation

Menggunakan data dari:
  - career_ranking_result_v2.csv
  - Neo4j Knowledge Graph (Course -[:TEACHES]-> Skill)
"""
import pandas as pd
import sys
from pathlib import Path
from neo4j import GraphDatabase

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, OUTPUT_DIR, OUTPUT_NORM_DIR, OUTPUT_KG_DIR

CSV_SEP = ';'
SKILL_SEP = ' | '
TOP_K = 5
MAX_COURSES_PER_SKILL = 4


def load_data():
    """Load career ranking v2 and student campus mapping."""
    ranking_path = OUTPUT_KG_DIR / "career_ranking_result_v2.csv"
    if not ranking_path.exists():
        ranking_path = OUTPUT_DIR / "career_ranking_result_v2.csv"
    df = pd.read_csv(ranking_path, sep=CSV_SEP)

    campus_path = OUTPUT_NORM_DIR / "student_skill_final.csv"
    if not campus_path.exists():
        campus_path = OUTPUT_DIR / "student_skill_final.csv"
    if not campus_path.exists():
        campus_path = OUTPUT_NORM_DIR / "student_skill_final_v2.csv"
    if campus_path.exists():
        df_campus = pd.read_csv(campus_path, sep=CSV_SEP)[['student_id', 'campus']].drop_duplicates()
        df = df.merge(df_campus, on='student_id', how='left')
    else:
        df['campus'] = df['student_id'].apply(
            lambda x: 'Jakarta' if str(x).startswith('J') else ('Surabaya' if str(x).startswith('S') else ('ITS' if str(x).startswith('I') else '-'))
        )
    return df


def level_sort_key(c):
    """Urutan prioritas level kursus: Beginner -> Intermediate/Medium -> Mixed -> Advanced -> Others."""
    lvl = str(c.get('level', '')).strip().lower()
    if 'beginner' in lvl:
        return 1
    elif 'intermediate' in lvl or 'medium' in lvl:
        return 2
    elif 'mixed' in lvl:
        return 3
    elif 'advanced' in lvl:
        return 4
    return 5


SKILL_TAXONOMY_FALLBACK = {
    # Data Science, Statistics & Analytics
    'statistical analysis': 'statistics',
    'statistical modeling': 'statistics',
    'advanced statistical analysis': 'statistics',
    'business acumen': 'business intelligence',
    'data analytics': 'data analysis',
    'data analysis skills': 'data analysis',
    'predictive modeling': 'machine learning',
    'ai/ml algorithms': 'machine learning',
    'advanced ai/ml': 'machine learning',
    'intro nlp': 'deep learning',
    'text analysis': 'deep learning',
    'computer vision basics': 'deep learning',
    'deep learning basics': 'deep learning',
    'neural network architecture': 'neural networks',
    'reinforcement learning': 'machine learning',
    'big data analytics': 'data warehousing',
    'data pipeline': 'data warehousing',
    'data engineering': 'data warehousing',
    'power bi': 'business intelligence',
    'tableau': 'data visualization',
    'tableau / power bi': 'data visualization',
    'bi tools': 'business intelligence',

    # Cybersecurity & Infrastructure
    'security': 'cybersecurity',
    'threat detection': 'cybersecurity',
    'advanced threat detection': 'cybersecurity',
    'incident response': 'cybersecurity',
    'penetration testing': 'cybersecurity',
    'vulnerability assessment': 'cybersecurity',
    'antivirus tools': 'cybersecurity',
    'nist basics': 'cybersecurity',
    'snort': 'cybersecurity',
    'siem': 'cybersecurity',
    'ethical hacking': 'cybersecurity',
    'network security': 'cybersecurity',
    'firewall': 'networking',
    'firewalls': 'networking',
    'lan/wan': 'networking',
    'tcp/ip': 'networking',
    'routing': 'networking',
    'switching': 'networking',
    'system administration': 'linux',
    'windows server administration': 'operating systems',
    'windows server': 'operating systems',
    'linux administration': 'linux',
    'troubleshooting': 'linux',
    'system architecture': 'system design',
    'system engineering': 'system design',
    'soa': 'system design',
    'api design': 'system design',
    'microservices': 'system design',

    # Databases & Backend
    'performance tuning': 'databases',
    'database performance': 'databases',
    'database design': 'databases',
    'database': 'databases',
    'sqlite': 'sql',
    'sql server': 'sql',
    'postgresql': 'sql',
    'mysql': 'sql',
    'nosql': 'databases',
    'mongodb': 'databases',
    'redis': 'databases',
    'oracle': 'sql',
    'etl': 'data warehousing',

    # Mobile Development
    'android studio': 'mobile development',
    'kotlin': 'mobile development',
    'swift': 'mobile development',
    'objective-c': 'mobile development',
    'flutter': 'mobile development',
    'react native': 'react',

    # Web & Programming Languages
    'ruby': 'web development',
    'ruby on rails': 'web development',
    'laravel': 'web development',
    'frameworks (laravel': 'web development',
    'symfony': 'web development',
    'django': 'python',
    'flask': 'python',
    'vue.js': 'javascript',
    'angular': 'javascript',
    'typescript': 'javascript',
    'tailwind css': 'css',
    'bootstrap': 'css',
    'c#': 'software engineering',
    'vb.net': 'software engineering',
    'asp.net': 'web development',
    'asp.net basics': 'web development',
    'python basics': 'python',
    'python scripting': 'python',
    'core python': 'python',
    'c programming': 'c',
    'c++ basics': 'c++',
    'core java': 'java',
    'advanced java': 'java',
    'javascript basics': 'javascript',

    # Cloud & DevOps
    'hyper-v': 'cloud computing',
    'vmware': 'cloud computing',
    'virtualization': 'cloud computing',
    'docker': 'devops',
    'kubernetes': 'cloud computing',
    'ci/cd': 'devops',
    'terraform': 'cloud computing',
    'automation': 'devops',
    'aws basics': 'aws',
    'azure basics': 'azure',
    'gcp basics': 'google cloud',

    # UI/UX & Design
    'wireframing': 'user research',
    'sketch': 'user research',
    'adobe xd': 'user research',
    'adobe creative suite': 'user research',
    'figma': 'user research',
    'ui/ux design': 'user research',
    'usability testing': 'user research',

    # Agile & Methodologies
    'agility': 'agile',
    'scrum master': 'scrum',
    'design patterns': 'software engineering',
}


def _course_priority(c, target_skill_name, fallback_parent=None):
    """Hitung bobot relevansi judul kursus terhadap target skill."""
    name = str(c.get('course_name', '')).lower()
    plat = str(c.get('platform', '')).lower()
    ts = target_skill_name.lower().strip()
    
    score = 0
    if ts in name:
        score -= 25
    
    tokens = [t for t in ts.split() if len(t) > 2]
    matched_tokens = sum(1 for t in tokens if t in name)
    score -= (matched_tokens * 6)
    
    if fallback_parent:
        fb_tokens = [t for t in fallback_parent.lower().split() if len(t) > 2]
        matched_fb = sum(1 for t in fb_tokens if t in name)
        score -= (matched_fb * 4)
    
    if any(p in plat for p in ['google', 'ibm', 'meta', 'microsoft', 'deeplearning.ai']):
        score -= 4
    elif any(p in plat for p in ['coursera', 'edx', 'udemy', 'university']):
        score -= 2
        
    return (score, name)


def _select_progressive_courses(courses, target_skill_name, fallback_parent=None):
    """Pilih kursus terbaik berdasarkan relevansi judul & progresivitas level."""
    if not courses:
        return []
        
    sorted_candidates = sorted(courses, key=lambda c: _course_priority(c, target_skill_name, fallback_parent))
    
    buckets = {'beginner': [], 'intermediate': [], 'mixed': [], 'advanced': [], 'other': []}
    for c in sorted_candidates:
        lvl = str(c.get('level', '')).strip().lower()
        if 'beginner' in lvl:
            buckets['beginner'].append(c)
        elif 'intermediate' in lvl or 'medium' in lvl:
            buckets['intermediate'].append(c)
        elif 'mixed' in lvl:
            buckets['mixed'].append(c)
        elif 'advanced' in lvl:
            buckets['advanced'].append(c)
        else:
            buckets['other'].append(c)

    selected = []
    for b_key in ['beginner', 'intermediate', 'mixed', 'advanced', 'other']:
        if buckets[b_key]:
            best = buckets[b_key][0]
            p_score = _course_priority(best, target_skill_name, fallback_parent)[0]
            if p_score < 0 or best in sorted_candidates[:6]:
                selected.append(buckets[b_key].pop(0))

    for c in sorted_candidates:
        if len(selected) >= MAX_COURSES_PER_SKILL:
            break
        if c not in selected:
            selected.append(c)

    # Set label covers
    for c in selected:
        if fallback_parent:
            c['covers_label'] = f"{target_skill_name} (via Induk Skill: {fallback_parent})"
        else:
            c['covers_label'] = target_skill_name

    return selected[:MAX_COURSES_PER_SKILL]


def get_courses_for_missing(driver, missing_skills):
    """
    Query Neo4j: untuk setiap missing skill, cari course yang TEACHES dengan variasi level berjenjang:
    1. Beginner
    2. Intermediate / Medium
    3. Mixed
    4. Advanced
    Jika exact match tidak tersedia di katalog, gunakan Skill Taxonomy Fallback ke induk skill.
    """
    if not missing_skills:
        return {}

    result = {}
    with driver.session() as session:
        for skill in missing_skills:
            # 1. Coba Exact Match terlebih dahulu
            records = session.run(
                "MATCH (co:Course)-[:TEACHES]->(sk:Skill {name: $skill}) "
                "RETURN co.course_id AS course_id, co.name AS course_name, "
                "       co.platform AS platform, co.level AS level ORDER BY co.name",
                {"skill": skill}
            )
            courses = [r.data() for r in records]

            if courses:
                result[skill] = _select_progressive_courses(courses, skill)
                continue

            # 2. Jika Exact Match kosong, coba Fallback ke Parent Skill di Taxonomy
            fallback_parent = SKILL_TAXONOMY_FALLBACK.get(skill)
            
            # Coba heuristik otomatis jika tidak ada di kamus statis
            if not fallback_parent:
                if ' ' in skill:
                    # Misal "python basics" -> "python"
                    for suffix in [' basics', ' scripting', ' programming', ' development', ' administration', ' architecture']:
                        if skill.endswith(suffix):
                            fallback_parent = skill[:-len(suffix)].strip()
                            break

            if fallback_parent:
                fb_records = session.run(
                    "MATCH (co:Course)-[:TEACHES]->(sk:Skill {name: $parent}) "
                    "RETURN co.course_id AS course_id, co.name AS course_name, "
                    "       co.platform AS platform, co.level AS level ORDER BY co.name",
                    {"parent": fallback_parent}
                )
                fb_courses = [r.data() for r in fb_records]
                if fb_courses:
                    result[skill] = _select_progressive_courses(fb_courses, skill, fallback_parent=fallback_parent)
                    continue

            # 3. Jika tetap tidak ada
            result[skill] = []

    return result


def find_student(df, query):
    """Cari student berdasarkan nama (case-insensitive, partial match)."""
    query_lower = query.strip().lower()

    # Exact match first
    exact = df[df['student_name'].str.lower() == query_lower]
    if len(exact) > 0:
        return exact.iloc[0]['student_id'], exact.iloc[0]['student_name']

    # Partial match
    partial = df[df['student_name'].str.lower().str.contains(query_lower, na=False)]
    if len(partial) > 0:
        unique = partial[['student_id', 'student_name']].drop_duplicates()
        if len(unique) == 1:
            return unique.iloc[0]['student_id'], unique.iloc[0]['student_name']
        else:
            return None, unique

    return None, None


def display_recommendation(df, driver, student_id, student_name):
    """Tampilkan rekomendasi untuk satu mahasiswa."""
    student_df = df[df['student_id'] == student_id]
    top_careers = student_df[student_df['career_rank'] <= TOP_K]
    campus = student_df['campus'].iloc[0] if ('campus' in student_df.columns and not student_df.empty and pd.notna(student_df['campus'].iloc[0])) else 'Unknown'

    print()
    print("=" * 50)
    print("   SISTEM REKOMENDASI COURSE")
    print("=" * 50)
    print(f"Student        : {student_name}")
    print(f"Asal Mahasiswa : {campus}")
    print()

    print("-" * 50)
    print("TOP CAREER")
    print("-" * 50)

    for _, row in top_careers.iterrows():
        rank = row['career_rank']
        career = row['career_name']
        rsg = row['relative_skill_gap']
        matched = row['matched_skill_count']
        required = row['required_skill_count']
        missing_count = row['missing_skill_count']

        # Parse missing skills
        missing_str = row['missing_skills']
        if pd.notna(missing_str) and missing_str:
            missing_skills = [s.strip() for s in missing_str.split(SKILL_SEP)]
        else:
            missing_skills = []

        # Parse matched skills
        matched_str = row['matched_skills']
        if pd.notna(matched_str) and matched_str:
            matched_skills = [s.strip() for s in matched_str.split(SKILL_SEP)]
        else:
            matched_skills = []

        # Parse all required skills
        required_skills = sorted(list(set(matched_skills + missing_skills)))

        print()
        print(f"[{rank}] {career.title()}")
        print(f"    Relative Skill Gap : {rsg*100:.2f}%")
        print(f"    Matched Skills     : {matched} / {required}")
        print(f"    Missing Skills     : {missing_count}")
        print(f"    Requirements       : {required}")

        if required_skills:
            print()
            print(f"    Requirements:")
            for sk in required_skills:
                print(f"      * {sk}")

        if matched_skills:
            print()
            print(f"    Matched:")
            for sk in sorted(matched_skills):
                print(f"      + {sk}")

        if missing_skills:
            print()
            print(f"    Missing:")
            for sk in sorted(missing_skills):
                print(f"      - {sk}")

            # Get course recommendations per missing skill
            courses_map = get_courses_for_missing(driver, missing_skills)

            print()
            print(f"    Course Recommendation:")

            has_any_course = False
            no_course_skills = []
            course_number = 1

            for sk in sorted(missing_skills):
                courses = courses_map.get(sk, [])
                if courses:
                    has_any_course = True
                    for c in courses:
                        raw_level = c.get('level')
                        level = str(raw_level).strip() if isinstance(raw_level, str) and raw_level.strip() else '-'
                        raw_platform = c.get('platform')
                        platform = str(raw_platform).strip() if isinstance(raw_platform, str) and raw_platform.strip() else '-'
                        print(f"      {course_number}. {c['course_name']}")
                        print(f"         Platform : {platform}")
                        print(f"         Level    : {level}")
                        print(f"         Covers   : {c.get('covers_label', sk)}")
                        course_number += 1
                else:
                    no_course_skills.append(sk)

            if no_course_skills:
                print(f"      Tidak tersedia course untuk skill:")
                for sk in no_course_skills:
                    print(f"      - {sk}")

            if not has_any_course and not no_course_skills:
                print(f"      (Tidak ada missing skill)")

        print()
        print("-" * 50)


def interactive_mode(df, driver):
    """Mode interaktif — terus menerima input nama."""
    print()
    print("=" * 50)
    print("   SISTEM REKOMENDASI COURSE")
    print("   Berbasis Knowledge Graph & Gap Analysis")
    print("=" * 50)
    print()
    print("Ketik nama mahasiswa untuk melihat rekomendasi.")
    print("Ketik 'exit' atau 'quit' untuk keluar.")
    print("Ketik 'list' untuk melihat daftar mahasiswa.")
    print()

    while True:
        try:
            query = input("Nama mahasiswa: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nSampai jumpa!")
            break

        if not query:
            continue

        if query.lower() in ('exit', 'quit', 'q'):
            print("Sampai jumpa!")
            break

        if query.lower() == 'list':
            students = df[['student_id', 'student_name']].drop_duplicates()
            students = students.sort_values('student_id')
            print(f"\nDaftar Mahasiswa ({len(students)}):")
            for _, s in students.iterrows():
                print(f"  {s['student_name']}")
            print()
            continue

        sid, result = find_student(df, query)

        if sid is None and result is None:
            print(f"\n  ⚠ Mahasiswa '{query}' tidak ditemukan.")
            print(f"  Ketik 'list' untuk melihat daftar mahasiswa.\n")
            continue

        if sid is None and isinstance(result, pd.DataFrame):
            print(f"\n  Ditemukan {len(result)} mahasiswa:")
            for _, s in result.iterrows():
                print(f"    - {s['student_name']}")
            print(f"  Masukkan nama lengkap.\n")
            continue

        display_recommendation(df, driver, sid, result)


def single_mode(df, driver, name):
    """Mode single — langsung tampilkan untuk satu nama."""
    sid, result = find_student(df, name)

    if sid is None and result is None:
        print(f"\n  ⚠ Mahasiswa '{name}' tidak ditemukan.")
        return

    if sid is None and isinstance(result, pd.DataFrame):
        print(f"\n  Ditemukan {len(result)} mahasiswa:")
        for _, s in result.iterrows():
            print(f"    - {s['student_name']}")
        print(f"  Masukkan nama lengkap.")
        return

    display_recommendation(df, driver, sid, result)


def main():
    df = load_data()
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    try:
        if len(sys.argv) > 1:
            # Single mode: python cli_recommendation.py "Citra Permata"
            name = " ".join(sys.argv[1:])
            single_mode(df, driver, name)
        else:
            # Interactive mode
            interactive_mode(df, driver)
    finally:
        driver.close()


if __name__ == "__main__":
    main()
