"""
obe_canonicalizer.py — OBE Skill Canonicalization v2

Pipeline khusus untuk memetakan skill OBE Jakarta + Surabaya
ke canonical vocabulary Jobs/Course.

Method (berurutan):
  1. Manual Override   — prioritas tertinggi
  2. Exact Match       — skill OBE == vocabulary Jobs/Course
  3. Semantic Match    — all-MiniLM-L6-v2, threshold >= 0.85
  4. Review Candidate  — explicit review list (jangan auto-merge)
  5. Unmatched         — tidak ada padanan cukup kuat

Output:
  - output/obe_skill_canonical_mapping_v2.csv
  - output/obe_skill_review_candidates.csv
  - output/obe_unmatched_skills_v2.csv
  - output/student_skill_final_v2.csv

STOP sebelum Neo4j import.
"""

import sys
import pandas as pd
import numpy as np
import logging
from pathlib import Path
from sentence_transformers import SentenceTransformer

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import (
    OBE_FILES, STUDENT_FILES, OUTPUT_DIR,
    OBE_SKILL_THRESHOLD, SENTENCE_MODEL,
    SEMANTIC_THRESHOLD_ACCEPTED, FORBIDDEN_MERGE_GROUPS
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

CSV_SEP = ';'

# ==============================================================
# MANUAL CANONICAL OVERRIDES (approved, immediate merge)
# ==============================================================
MANUAL_OVERRIDES = {
    "jaringan komputer":             "networking",
    "kriptografi":                   "cryptography",
    "basis data / database":         "database",
    "klasifikasi (data)":            "classification",
    "otorisasi":                     "authorization",
    "oop (object oriented programming)": "object-oriented programming",
    "erp (enterprise resource planning)": "erp",
    "etl (extract transform load)":  "etl",
    "crm (customer relationship management)": "crm",
    # Approved in review session
    "data warehouse":                "data warehousing",
    "regresi":                       "regression",
    # Existing normalization overrides
    "microsoft excel":               "excel",
    "neural network":                "neural networks",
    "ui/ux design":                  "ui/ux",
    "uml (unified modeling language)": "uml",
    "erd (entity relationship diagram)": "erd",
}

# ==============================================================
# REVIEW CANDIDATES (jangan auto-merge — perlu validasi manual)
# Approved: regresi dan data warehouse sudah dipindah ke MANUAL_OVERRIDES
# ==============================================================
REVIEW_CANDIDATES = {
    "statistika/probabilitas":      "statistics",
    "kpi (key performance indicator)": "key performance indicator",
    "scm (supply chain management)": "supply chain management",
    "osi layer":                    "networking",
    "algoritma & pemrograman dasar": "programming",
    "konsep dasar sistem informasi": "information systems",
    "sprint (agile)":               "agile",
    "use case diagram":             "use case design",
}

# ==============================================================
# FORBIDDEN MERGE PAIRS (dari config + tambahan khusus OBE)
# ==============================================================
FORBIDDEN_PAIRS = [
    {"agile", "scrum"},
    {"agile", "kanban"},
    {"scrum", "kanban"},
    {"linux", "windows"},
    {"python", "java"},
    {"python", "php"},
    {"java", "php"},
    {"html", "css"},
    {"html", "javascript"},
    {"css", "javascript"},
    {"networking", "osi layer"},
    {"sprint (agile)", "scrum"},
]


def load_obe_skills_raw():
    """Load obe_skills_raw.csv hasil skill_extractor.py."""
    df = pd.read_csv(OUTPUT_DIR / "obe_skills_raw.csv")
    logger.info(f"  Loaded obe_skills_raw.csv: {len(df)} rows, "
                f"{df['student_id'].nunique()} students, "
                f"{df['skill'].nunique()} unique skills")
    return df


def load_reference_vocabulary():
    """Load canonical vocabulary dari Jobs dan Course (bukan dari OBE)."""
    df_job = pd.read_csv(OUTPUT_DIR / "job_skills_raw.csv")
    df_course = pd.read_csv(OUTPUT_DIR / "course_skills_raw.csv")
    # Also load canonical_skill_master untuk vocabulary yang sudah ternormalisasi
    job_vocab = set(df_job['skill'].str.strip().str.lower().unique())
    course_vocab = set(df_course['skill'].str.strip().str.lower().unique())
    all_vocab = job_vocab | course_vocab
    logger.info(f"  Reference vocabulary: {len(job_vocab)} Job skills + "
                f"{len(course_vocab)} Course skills = {len(all_vocab)} unique")
    return job_vocab, course_vocab, all_vocab


def check_forbidden_merge(skill_a, skill_b):
    """Cek apakah merge dua skill melanggar forbidden merge pairs."""
    for pair in FORBIDDEN_PAIRS:
        if skill_a in pair and skill_b in pair:
            return True
    return False


def get_skill_sources(df_obe, skill):
    """Dapatkan list kampus yang memiliki skill ini."""
    sources = sorted(df_obe[df_obe['skill'] == skill]['kampus'].unique().tolist())
    return ', '.join(sources)


def run_canonicalization(df_obe, job_vocab, course_vocab, all_vocab):
    """
    Jalankan canonicalization dengan urutan priority:
    1. Manual Override
    2. Exact Match (ke Jobs vocab atau Course vocab)
    3. Semantic Match (>= 0.85)
    4. Review Candidate (dari REVIEW_CANDIDATES dict)
    5. Unmatched
    """
    logger.info("")
    logger.info("=" * 65)
    logger.info("CANONICALIZATION — OBE SKILLS v2")
    logger.info("=" * 65)

    unique_skills = sorted(df_obe['skill'].unique())
    logger.info(f"  Total unique OBE skills: {len(unique_skills)}")

    # Load embedding model
    logger.info(f"  Loading sentence embedding model: {SENTENCE_MODEL}")
    model = SentenceTransformer(SENTENCE_MODEL)

    # Encode reference vocabulary
    vocab_list = sorted(all_vocab)
    logger.info(f"  Encoding {len(vocab_list)} reference skills...")
    vocab_embeddings = model.encode(vocab_list, batch_size=256,
                                     show_progress_bar=False,
                                     convert_to_numpy=True)

    # Encode OBE skills
    logger.info(f"  Encoding {len(unique_skills)} OBE skills...")
    obe_embeddings = model.encode(unique_skills, batch_size=64,
                                   show_progress_bar=False,
                                   convert_to_numpy=True)

    # Cosine similarity
    from numpy.linalg import norm
    def cosine_sim(a, b):
        return float(np.dot(a, b) / (norm(a) * norm(b) + 1e-10))

    mapping_rows = []
    review_rows = []
    unmatched_rows = []

    stats = {
        'manual_override': 0,
        'exact_match': 0,
        'semantic_match': 0,
        'review': 0,
        'unmatched': 0,
    }

    for i, skill in enumerate(unique_skills):
        sources = get_skill_sources(df_obe, skill)
        skill_lower = skill.strip().lower()

        # --- PRIORITY 1: Manual Override ---
        if skill_lower in MANUAL_OVERRIDES:
            canonical = MANUAL_OVERRIDES[skill_lower]
            mapping_rows.append({
                'original_skill': skill,
                'canonical_skill': canonical,
                'similarity_score': 1.0,
                'mapping_method': 'manual_override',
                'status': 'accepted',
                'source': sources,
                'reason': f'Manual override: "{skill}" -> "{canonical}"'
            })
            stats['manual_override'] += 1
            continue

        # --- PRIORITY 2: Review Candidate (sebelum semantic!) ---
        if skill_lower in REVIEW_CANDIDATES:
            candidate = REVIEW_CANDIDATES[skill_lower]
            # Hitung similarity untuk informasi
            obe_emb = obe_embeddings[i]
            if candidate in vocab_list:
                cand_idx = vocab_list.index(candidate)
                sim = cosine_sim(obe_emb, vocab_embeddings[cand_idx])
            else:
                sim = 0.0

            in_jobs = candidate in job_vocab
            in_course = candidate in course_vocab
            review_rows.append({
                'original_skill': skill,
                'candidate_canonical_skill': candidate,
                'similarity_score': round(sim, 4),
                'status': 'REVIEW',
                'source': sources,
                'in_job_vocab': in_jobs,
                'in_course_vocab': in_course,
                'reason': (
                    f'Review candidate: "{skill}" -> "{candidate}". '
                    f'In Jobs: {in_jobs}, In Course: {in_course}. '
                    f'Sim: {sim:.4f}. Perlu validasi manual sebelum merge.'
                )
            })
            # Tetap masuk mapping sebagai REVIEW (bukan accepted)
            mapping_rows.append({
                'original_skill': skill,
                'canonical_skill': skill,  # tetap diri sendiri dulu
                'similarity_score': round(sim, 4),
                'mapping_method': 'review',
                'status': 'REVIEW',
                'source': sources,
                'reason': (
                    f'Review candidate untuk "{candidate}" (sim={sim:.4f}). '
                    f'Belum di-merge. Lihat obe_skill_review_candidates.csv.'
                )
            })
            stats['review'] += 1
            continue

        # --- PRIORITY 3: Exact Match ---
        if skill_lower in all_vocab:
            in_jobs = skill_lower in job_vocab
            in_course = skill_lower in course_vocab
            mapping_rows.append({
                'original_skill': skill,
                'canonical_skill': skill_lower,
                'similarity_score': 1.0,
                'mapping_method': 'exact_match',
                'status': 'accepted',
                'source': sources,
                'reason': (
                    f'Exact match ke vocabulary '
                    f"{'Jobs' if in_jobs else ''}{'/' if in_jobs and in_course else ''}"
                    f"{'Course' if in_course else ''}"
                )
            })
            stats['exact_match'] += 1
            continue

        # --- PRIORITY 4: Semantic Match ---
        obe_emb = obe_embeddings[i]
        sims = np.array([cosine_sim(obe_emb, vocab_embeddings[j])
                         for j in range(len(vocab_list))])
        best_idx = int(np.argmax(sims))
        best_sim = float(sims[best_idx])
        best_match = vocab_list[best_idx]

        if best_sim >= SEMANTIC_THRESHOLD_ACCEPTED:
            # Check forbidden merge
            if check_forbidden_merge(skill_lower, best_match):
                # Forbidden — tetap unmatched
                unmatched_rows.append({
                    'original_skill': skill,
                    'source': sources,
                    'reason': (
                        f'Semantic match ke "{best_match}" (sim={best_sim:.4f}) '
                        f'ditolak: FORBIDDEN MERGE'
                    )
                })
                mapping_rows.append({
                    'original_skill': skill,
                    'canonical_skill': skill_lower,
                    'similarity_score': round(best_sim, 4),
                    'mapping_method': 'unmatched',
                    'status': 'unmatched',
                    'source': sources,
                    'reason': (
                        f'Best match "{best_match}" ({best_sim:.4f}) '
                        f'DITOLAK karena forbidden merge rule.'
                    )
                })
                stats['unmatched'] += 1
            else:
                # Accepted semantic match
                mapping_rows.append({
                    'original_skill': skill,
                    'canonical_skill': best_match,
                    'similarity_score': round(best_sim, 4),
                    'mapping_method': 'semantic_match',
                    'status': 'accepted',
                    'source': sources,
                    'reason': (
                        f'Semantic match: "{skill}" -> "{best_match}" '
                        f'(sim={best_sim:.4f})'
                    )
                })
                stats['semantic_match'] += 1
        else:
            # Unmatched — similarity terlalu rendah
            unmatched_rows.append({
                'original_skill': skill,
                'source': sources,
                'reason': (
                    f'Best semantic match: "{best_match}" ({best_sim:.4f}) '
                    f'< threshold {SEMANTIC_THRESHOLD_ACCEPTED}. '
                    f'Dipertahankan sebagai canonical skill sendiri.'
                )
            })
            mapping_rows.append({
                'original_skill': skill,
                'canonical_skill': skill_lower,
                'similarity_score': round(best_sim, 4),
                'mapping_method': 'unmatched',
                'status': 'unmatched',
                'source': sources,
                'reason': (
                    f'Tidak ada padanan cukup kuat. Best: "{best_match}" '
                    f'({best_sim:.4f}). Dipertahankan sebagai skill sendiri.'
                )
            })
            stats['unmatched'] += 1

    return pd.DataFrame(mapping_rows), pd.DataFrame(review_rows), \
           pd.DataFrame(unmatched_rows), stats


def build_student_skill_final_v2(df_obe, df_mapping):
    """
    Build student_skill_final_v2.csv dengan canonical skill dari mapping v2.
    Threshold: score >= 50.01
    Satu mahasiswa tidak boleh duplicate canonical skill (ambil score max).
    """
    logger.info("")
    logger.info("=" * 65)
    logger.info("BUILD student_skill_final_v2.csv")
    logger.info("=" * 65)

    # Load raw OBE data dengan CLO info
    all_rows = []
    for kampus, obe_path in OBE_FILES.items():
        student_path = STUDENT_FILES[kampus]

        df_obe_ref = pd.read_excel(obe_path, sheet_name='Referensi_CLO')
        df_mhs = pd.read_excel(student_path, sheet_name='Daftar_Mahasiswa')
        df_scores = pd.read_excel(student_path,
                                   sheet_name='Nilai_Mahasiswa_per_CLO')

        # Filter threshold
        df_pass = df_scores[df_scores['score'] >= OBE_SKILL_THRESHOLD].copy()

        # Join OBE reference
        df_joined = df_pass.merge(
            df_obe_ref[['id_CLO', 'skill_technical']],
            on='id_CLO', how='left'
        )
        df_joined = df_joined.merge(
            df_mhs[['id_student', 'nama_mahasiswa']],
            on='id_student', how='left'
        )
        df_joined['kampus'] = kampus

        all_rows.append(df_joined)
        logger.info(f"  {kampus}: {df_pass['id_student'].nunique()} mhs, "
                     f"{len(df_pass)} records lolos threshold")

    df_all = pd.concat(all_rows, ignore_index=True)
    df_all['skill_original'] = df_all['skill_technical'].str.strip().str.lower()

    # Build mapping lookup: original_skill -> canonical_skill
    mapping_lookup = {}
    for _, row in df_mapping.iterrows():
        orig = str(row['original_skill']).strip().lower()
        canon = str(row['canonical_skill']).strip().lower()
        mapping_lookup[orig] = canon

    # Apply canonical mapping
    df_all['canonical_skill'] = df_all['skill_original'].map(
        lambda s: mapping_lookup.get(s, s)
    )

    # Deduplikasi: per student per canonical_skill, ambil score max
    df_final = (
        df_all.groupby(
            ['id_student', 'nama_mahasiswa', 'kampus', 'canonical_skill']
        ).agg(
            skill_original=('skill_original', 'first'),
            id_CLO=('id_CLO', 'first'),
            score=('score', 'max')
        ).reset_index()
    )

    # Rename columns
    df_final = df_final.rename(columns={
        'id_student': 'student_id',
        'nama_mahasiswa': 'student_name',
        'kampus': 'campus',
    })

    # Reorder
    cols = ['student_id', 'student_name', 'campus', 'id_CLO',
            'skill_original', 'canonical_skill', 'score']
    df_final = df_final[cols]

    # Stats
    logger.info(f"  Total records         : {len(df_final)}")
    logger.info(f"  Total students        : {df_final['student_id'].nunique()}")
    logger.info(f"  Unique canonical skills: {df_final['canonical_skill'].nunique()}")
    for k in ['Jakarta', 'Surabaya']:
        n = df_final[df_final['campus'] == k]['student_id'].nunique()
        r = len(df_final[df_final['campus'] == k])
        logger.info(f"  {k}: {n} mhs, {r} skill records")

    per_student = df_final.groupby('student_id').size()
    logger.info(f"  Skills per student: "
                f"min={per_student.min()}, max={per_student.max()}, "
                f"mean={per_student.mean():.1f}")

    # Check duplicates
    dupes = df_final.duplicated(
        subset=['student_id', 'canonical_skill']
    ).sum()
    logger.info(f"  Duplicate (student, canonical_skill): {dupes} "
                f"{'[OK]' if dupes == 0 else '[WARNING!]'}")

    out = OUTPUT_DIR / "student_skill_final_v2.csv"
    df_final.to_csv(out, index=False, sep=CSV_SEP)
    logger.info(f"  Saved: {out}")

    return df_final


def print_full_report(df_mapping, df_review, df_unmatched, stats,
                      job_vocab, course_vocab):
    """Laporan akhir komprehensif."""
    logger.info("")
    logger.info("=" * 65)
    logger.info("LAPORAN CANONICALIZATION OBE v2")
    logger.info("=" * 65)

    total = len(df_mapping)

    logger.info(f"\n[A] STATISTIK SEBELUM CANONICALIZATION")
    logger.info(f"  Total unique OBE skills  : {total}")
    jakarta = sorted(df_mapping[df_mapping['source'].str.contains(
        'Jakarta', na=False)]['original_skill'].unique())
    surabaya = sorted(df_mapping[df_mapping['source'].str.contains(
        'Surabaya', na=False)]['original_skill'].unique())
    both = sorted(df_mapping[df_mapping['source'].str.contains(
        ',', na=False)]['original_skill'].unique())
    logger.info(f"  Jakarta only             : "
                f"{len([s for s in jakarta if s not in surabaya])}")
    logger.info(f"  Surabaya only            : "
                f"{len([s for s in surabaya if s not in jakarta])}")
    logger.info(f"  Both campuses            : {len(both)}")

    logger.info(f"\n[B] STATISTIK SETELAH CANONICALIZATION")
    logger.info(f"  Manual override          : {stats['manual_override']}")
    logger.info(f"  Exact match              : {stats['exact_match']}")
    logger.info(f"  Semantic match           : {stats['semantic_match']}")
    logger.info(f"  Review candidates        : {stats['review']}")
    logger.info(f"  Unmatched (self-retain)  : {stats['unmatched']}")
    logger.info(f"  TOTAL                    : {total}")

    accepted = stats['manual_override'] + stats['exact_match'] + stats['semantic_match']
    logger.info(f"\n  Accepted (auto)          : {accepted} "
                f"({accepted/total*100:.1f}%)")
    logger.info(f"  Review (pending)         : {stats['review']} "
                f"({stats['review']/total*100:.1f}%)")
    logger.info(f"  Unmatched                : {stats['unmatched']} "
                f"({stats['unmatched']/total*100:.1f}%)")

    # Match ke Jobs/Course vocabulary
    accepted_canonical = set(
        df_mapping[df_mapping['status'] == 'accepted']['canonical_skill']
    )
    match_job = len(accepted_canonical & job_vocab)
    match_course = len(accepted_canonical & course_vocab)
    logger.info(f"\n[C] OVERLAP DENGAN VOCABULARY REFERENSI")
    logger.info(f"  Canonical skills match ke Jobs  : {match_job}")
    logger.info(f"  Canonical skills match ke Course : {match_course}")

    logger.info(f"\n[D] TABEL MAPPING LENGKAP")
    logger.info(f"  {'Original Skill':<45} {'Canonical Skill':<40} "
                f"{'Method':<18} {'Status':<10} {'Sim':>6}")
    logger.info(f"  {'-'*45} {'-'*40} {'-'*18} {'-'*10} {'-'*6}")
    for _, row in df_mapping.sort_values('mapping_method').iterrows():
        logger.info(f"  {row['original_skill']:<45} {row['canonical_skill']:<40} "
                    f"{row['mapping_method']:<18} {row['status']:<10} "
                    f"{row['similarity_score']:>6.4f}")

    logger.info(f"\n[E] MANUAL OVERRIDES ({stats['manual_override']})")
    manual = df_mapping[df_mapping['mapping_method'] == 'manual_override']
    for _, row in manual.iterrows():
        logger.info(f"  {row['original_skill']:<40} -> {row['canonical_skill']}")

    logger.info(f"\n[F] EXACT MATCHES ({stats['exact_match']})")
    exact = df_mapping[df_mapping['mapping_method'] == 'exact_match']
    for _, row in exact.iterrows():
        in_job = row['canonical_skill'] in job_vocab
        in_course = row['canonical_skill'] in course_vocab
        logger.info(f"  {row['original_skill']:<40}  "
                    f"[Jobs={'Y' if in_job else 'N'} Course={'Y' if in_course else 'N'}]")

    logger.info(f"\n[G] SEMANTIC MATCHES ({stats['semantic_match']})")
    sem = df_mapping[df_mapping['mapping_method'] == 'semantic_match']
    for _, row in sem.iterrows():
        logger.info(f"  {row['original_skill']:<40} -> {row['canonical_skill']:<35} "
                    f"(sim={row['similarity_score']:.4f})")

    logger.info(f"\n[H] REVIEW CANDIDATES ({stats['review']})")
    logger.info(f"  {'Original':<40} {'Candidate':<35} {'Sim':>6} "
                f"{'In Jobs':>8} {'In Course':>10}")
    logger.info(f"  {'-'*40} {'-'*35} {'-'*6} {'-'*8} {'-'*10}")
    for _, row in df_review.iterrows():
        logger.info(f"  {row['original_skill']:<40} {row['candidate_canonical_skill']:<35} "
                    f"{row['similarity_score']:>6.4f} "
                    f"{'YES' if row['in_job_vocab'] else 'NO':>8} "
                    f"{'YES' if row['in_course_vocab'] else 'NO':>10}")

    logger.info(f"\n[I] UNMATCHED SKILLS ({stats['unmatched']})")
    for _, row in df_unmatched.iterrows():
        logger.info(f"  {row['original_skill']:<40} [{row['source']}]")
        logger.info(f"    Reason: {row['reason']}")

    logger.info(f"\n[J] FORBIDDEN MERGE VALIDATION")
    violations = []
    for _, row in df_mapping.iterrows():
        if row['mapping_method'] in ('manual_override', 'semantic_match'):
            orig = row['original_skill'].lower()
            canon = row['canonical_skill'].lower()
            if check_forbidden_merge(orig, canon):
                violations.append(f"  VIOLATION: {orig} -> {canon}")
    if violations:
        for v in violations:
            logger.info(v)
    else:
        logger.info("  [OK] Tidak ada forbidden merge violation.")


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    logger.info("=" * 65)
    logger.info("OBE SKILL CANONICALIZATION v2")
    logger.info("Jakarta + Surabaya | Threshold >= 50.01")
    logger.info("=" * 65)

    # Load data
    df_obe = load_obe_skills_raw()
    job_vocab, course_vocab, all_vocab = load_reference_vocabulary()

    # Run canonicalization
    df_mapping, df_review, df_unmatched, stats = run_canonicalization(
        df_obe, job_vocab, course_vocab, all_vocab
    )

    # Save output files
    mapping_path = OUTPUT_DIR / "obe_skill_canonical_mapping_v2.csv"
    review_path = OUTPUT_DIR / "obe_skill_review_candidates.csv"
    unmatched_path = OUTPUT_DIR / "obe_unmatched_skills_v2.csv"

    df_mapping.to_csv(mapping_path, index=False, sep=CSV_SEP)
    df_review.to_csv(review_path, index=False, sep=CSV_SEP)
    df_unmatched.to_csv(unmatched_path, index=False, sep=CSV_SEP)

    logger.info(f"\n  Saved: {mapping_path}")
    logger.info(f"  Saved: {review_path}")
    logger.info(f"  Saved: {unmatched_path}")

    # Build student_skill_final_v2
    df_student_v2 = build_student_skill_final_v2(df_obe, df_mapping)

    # Full report
    print_full_report(df_mapping, df_review, df_unmatched, stats,
                      job_vocab, course_vocab)

    logger.info("")
    logger.info("=" * 65)
    logger.info("CANONICALIZATION v2 SELESAI")
    logger.info("STOP — Jangan lanjut ke Neo4j sebelum review.")
    logger.info("=" * 65)
    logger.info(f"\n  Output files:")
    logger.info(f"  1. {mapping_path}")
    logger.info(f"  2. {review_path}")
    logger.info(f"  3. {unmatched_path}")
    logger.info(f"  4. {OUTPUT_DIR / 'student_skill_final_v2.csv'}")


if __name__ == "__main__":
    main()
