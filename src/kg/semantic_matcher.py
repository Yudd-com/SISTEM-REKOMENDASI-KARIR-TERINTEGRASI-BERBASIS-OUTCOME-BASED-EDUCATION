"""
semantic_matcher.py — Tahap 5–8: Exact Matching, Semantic Matching,
                      Canonical Skill Master, Validasi Mapping

REVISI: Menambahkan validasi domain/context untuk mencegah false-positive merge.
- FORBIDDEN_MERGE_GROUPS: pasangan skill yang tidak boleh di-merge
- MANUAL_CANONICAL_OVERRIDES: mapping paksa untuk skill tertentu
- Union-Find dengan must-not-link constraint

Prinsip: false merge lebih berbahaya daripada skill yang belum ter-merge.

Output:
  - output/canonical_skill_master.csv
  - output/semantic_pairs.csv
"""
import pandas as pd
import numpy as np
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import (
    OUTPUT_DIR,
    SEMANTIC_THRESHOLD_ACCEPTED, SEMANTIC_THRESHOLD_REVIEW,
    SENTENCE_MODEL,
    FORBIDDEN_MERGE_GROUPS, MANUAL_CANONICAL_OVERRIDES
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)


# ============================================================
# FORBIDDEN MERGE LOOKUP
# ============================================================
def build_forbidden_lookup(forbidden_groups):
    """
    Bangun lookup set: jika skill A dan skill B ada di group yang sama,
    mereka tidak boleh di-merge.
    Returns: dict {skill: set of skills yang tidak boleh di-merge dengannya}
    """
    lookup = {}
    for group in forbidden_groups:
        for skill in group:
            if skill not in lookup:
                lookup[skill] = set()
            lookup[skill].update(group - {skill})
    return lookup


FORBIDDEN_LOOKUP = build_forbidden_lookup(FORBIDDEN_MERGE_GROUPS)


def is_merge_forbidden(skill_a, skill_b, cluster_members_a, cluster_members_b):
    """
    Cek apakah merger antara dua cluster dilarang.
    Merger dilarang jika SALAH SATU member cluster A
    memiliki forbidden pair dengan SALAH SATU member cluster B.
    """
    for member_a in cluster_members_a:
        forbidden_for_a = FORBIDDEN_LOOKUP.get(member_a, set())
        for member_b in cluster_members_b:
            if member_b in forbidden_for_a:
                return True
            # Juga cek apakah member_b ada substring match
            forbidden_for_b = FORBIDDEN_LOOKUP.get(member_b, set())
            if member_a in forbidden_for_b:
                return True
    return False


def skill_contains_forbidden_keyword(skill, forbidden_set):
    """
    Cek apakah skill mengandung keyword dari forbidden set.
    Contoh: 'linux administration' mengandung keyword 'linux'.
    """
    skill_lower = skill.lower()
    for keyword in forbidden_set:
        # Cek exact word boundary
        words = skill_lower.split()
        if keyword in words:
            return keyword
        # Cek jika skill dimulai dengan keyword
        if skill_lower.startswith(keyword + " ") or skill_lower.startswith(keyword + "/"):
            return keyword
    return None


# ============================================================
# DATA LOADING
# ============================================================
def load_raw_skills():
    """Membaca 3 file skill mentah hasil Tahap 1."""
    df_obe = pd.read_csv(OUTPUT_DIR / "obe_skills_raw.csv")
    df_jobs = pd.read_csv(OUTPUT_DIR / "job_skills_raw.csv")
    df_course = pd.read_csv(OUTPUT_DIR / "course_skills_raw.csv")

    obe_skills = set(df_obe['skill'].dropna().str.strip().str.lower().unique())
    job_skills = set(df_jobs['skill'].dropna().str.strip().str.lower().unique())
    course_skills = set(df_course['skill'].dropna().str.strip().str.lower().unique())

    return obe_skills, job_skills, course_skills


def build_skill_source_map(obe_skills, job_skills, course_skills):
    """Bangun mapping: skill -> list sumber (OBE, Jobs, Course)."""
    skill_sources = {}
    all_skills = obe_skills | job_skills | course_skills

    for skill in all_skills:
        sources = []
        if skill in obe_skills:
            sources.append('OBE')
        if skill in job_skills:
            sources.append('Jobs')
        if skill in course_skills:
            sources.append('Course')
        skill_sources[skill] = sources

    return skill_sources


# ============================================================
# TAHAP 6: SEMANTIC MATCHING
# ============================================================
def semantic_match_phase(all_skills):
    """
    Menggunakan all-MiniLM-L6-v2 untuk menemukan pasangan skill
    yang berbeda penulisan tapi bermakna sama.
    """
    from sentence_transformers import SentenceTransformer
    from sklearn.metrics.pairwise import cosine_similarity

    logger.info("  Memuat model SentenceTransformer...")
    model = SentenceTransformer(SENTENCE_MODEL)

    skills_list = sorted(all_skills)
    logger.info(f"  Menghitung embedding untuk {len(skills_list)} skill...")
    embeddings = model.encode(skills_list, show_progress_bar=True, batch_size=256)

    logger.info("  Menghitung cosine similarity matrix...")
    sim_matrix = cosine_similarity(embeddings)

    # Temukan pasangan dengan similarity >= REVIEW threshold
    pairs = []
    for i in range(len(skills_list)):
        for j in range(i + 1, len(skills_list)):
            score = sim_matrix[i][j]
            if score >= SEMANTIC_THRESHOLD_REVIEW:
                pairs.append({
                    'skill_a': skills_list[i],
                    'skill_b': skills_list[j],
                    'similarity': round(float(score), 4)
                })

    df_pairs = pd.DataFrame(pairs)
    df_pairs = df_pairs.sort_values('similarity', ascending=False).reset_index(drop=True)

    logger.info(f"  Ditemukan {len(df_pairs)} pasangan dengan similarity >= {SEMANTIC_THRESHOLD_REVIEW}")

    return df_pairs, skills_list, sim_matrix


# ============================================================
# TAHAP 7: BUILD CANONICAL MAPPING (WITH CONSTRAINTS)
# ============================================================
def build_canonical_mapping(all_skills, skill_sources, semantic_pairs):
    """
    Bangun canonical_skill_master dengan:
    1. Union-Find yang menghormati FORBIDDEN_MERGE_GROUPS
    2. MANUAL_CANONICAL_OVERRIDES diterapkan terakhir

    Prinsip: false merge lebih berbahaya daripada unmatched.
    """

    # --- Union-Find dengan constraint ---
    parent = {skill: skill for skill in all_skills}
    cluster_members = {skill: {skill} for skill in all_skills}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra == rb:
            return True  # already same cluster

        # CEK FORBIDDEN: apakah merger ini melanggar constraint?
        members_a = cluster_members.get(ra, {ra})
        members_b = cluster_members.get(rb, {rb})

        if is_merge_forbidden(a, b, members_a, members_b):
            return False  # merger ditolak

        # Merge cluster kecil ke besar
        if len(members_a) < len(members_b):
            ra, rb = rb, ra
            members_a, members_b = members_b, members_a

        parent[rb] = ra
        cluster_members[ra] = members_a | members_b
        if rb in cluster_members and rb != ra:
            del cluster_members[rb]

        return True

    # Hanya merge skill dengan similarity >= ACCEPTED threshold
    accepted_pairs = semantic_pairs[
        semantic_pairs['similarity'] >= SEMANTIC_THRESHOLD_ACCEPTED
    ].copy()

    merge_count = 0
    rejected_count = 0

    for _, row in accepted_pairs.iterrows():
        success = union(row['skill_a'], row['skill_b'])
        if success:
            merge_count += 1
        else:
            rejected_count += 1

    logger.info(f"  Merges accepted: {merge_count}")
    logger.info(f"  Merges rejected (forbidden): {rejected_count}")

    # Rebuild cluster_members setelah semua union selesai
    final_clusters = {}
    for skill in all_skills:
        root = find(skill)
        if root not in final_clusters:
            final_clusters[root] = set()
        final_clusters[root].add(skill)

    # --- Pilih canonical name per cluster ---
    # Prioritas: (1) ada di Jobs, (2) lebih pendek, (3) alphabetical
    canonical_map = {}
    for root, members in final_clusters.items():
        candidates = []
        for m in members:
            sources = skill_sources.get(m, [])
            in_jobs = 1 if 'Jobs' in sources else 0
            candidates.append((m, in_jobs, len(m)))

        candidates.sort(key=lambda x: (-x[1], x[2], x[0]))
        chosen = candidates[0][0]

        for m in members:
            canonical_map[m] = chosen

    # --- Terapkan MANUAL OVERRIDES (menimpa hasil otomatis) ---
    override_count = 0
    for original, forced_canonical in MANUAL_CANONICAL_OVERRIDES.items():
        if original in canonical_map:
            if canonical_map[original] != forced_canonical:
                override_count += 1
            canonical_map[original] = forced_canonical

    logger.info(f"  Manual overrides applied: {override_count}")

    return canonical_map, final_clusters


# ============================================================
# GENERATE MASTER CSV
# ============================================================
def generate_master_csv(all_skills, skill_sources, canonical_map, semantic_pairs):
    """
    Menghasilkan canonical_skill_master.csv
    """
    rows = []

    # Buat lookup similarity ke canonical
    pair_scores = {}
    for _, p in semantic_pairs.iterrows():
        pair_scores[(p['skill_a'], p['skill_b'])] = p['similarity']
        pair_scores[(p['skill_b'], p['skill_a'])] = p['similarity']

    for skill in sorted(all_skills):
        sources = skill_sources.get(skill, ['Unknown'])
        canonical = canonical_map.get(skill, skill)

        # Tentukan method dan score
        if canonical == skill:
            method = 'exact'
            score = 1.0
            status = 'accepted'
        else:
            score = pair_scores.get((skill, canonical), 0.0)
            if score == 0.0:
                # Cek skor transitif
                for other_skill, other_canonical in canonical_map.items():
                    if other_canonical == canonical and other_skill != skill:
                        s = pair_scores.get((skill, other_skill), 0.0)
                        if s > score:
                            score = s

            # Cek apakah ini manual override
            if skill in MANUAL_CANONICAL_OVERRIDES:
                method = 'manual'
                status = 'accepted'
            elif score >= SEMANTIC_THRESHOLD_ACCEPTED:
                method = 'semantic'
                status = 'accepted'
            elif score >= SEMANTIC_THRESHOLD_REVIEW:
                method = 'semantic'
                status = 'review'
            else:
                method = 'unmatched'
                status = 'unmatched'

        for src in sources:
            rows.append({
                'source': src,
                'original_skill': skill,
                'canonical_skill': canonical,
                'similarity_score': round(score, 4),
                'mapping_method': method,
                'status': status
            })

    df_master = pd.DataFrame(rows)
    out_path = OUTPUT_DIR / "canonical_skill_master.csv"
    df_master.to_csv(out_path, index=False)
    logger.info(f"  Disimpan: {out_path}")

    return df_master


# ============================================================
# REVIEW REPORT
# ============================================================
def print_review_report(df_master, canonical_map, clusters, semantic_pairs):
    """Tahap 8: Tampilkan hasil untuk direview oleh user."""

    logger.info("")
    logger.info("=" * 60)
    logger.info("TAHAP 8: VALIDASI MAPPING — REVIEW REPORT")
    logger.info("=" * 60)

    # Statistik umum
    unique_original = df_master['original_skill'].nunique()
    unique_canonical = df_master['canonical_skill'].nunique()

    method_counts = df_master.drop_duplicates('original_skill').groupby('mapping_method').size()
    status_counts = df_master.drop_duplicates('original_skill').groupby('status').size()

    logger.info(f"\n  [Statistik Normalisasi]")
    logger.info(f"  Unique original skills : {unique_original}")
    logger.info(f"  Unique canonical skills: {unique_canonical}")
    logger.info(f"  Reduksi: {unique_original} -> {unique_canonical} "
                f"({unique_original - unique_canonical} skill di-merge)")

    logger.info(f"\n  [Mapping Method]")
    for method, count in sorted(method_counts.items()):
        logger.info(f"    {method}: {count}")

    logger.info(f"\n  [Status]")
    for status, count in sorted(status_counts.items()):
        logger.info(f"    {status}: {count}")

    # Per sumber
    for src in ['OBE', 'Jobs', 'Course']:
        df_src = df_master[df_master['source'] == src]
        logger.info(f"\n  [{src}]")
        logger.info(f"    Original skills : {df_src['original_skill'].nunique()}")
        logger.info(f"    -> Canonical     : {df_src['canonical_skill'].nunique()}")

    # Tampilkan cluster yang memiliki > 1 anggota (skill yang di-merge)
    merged_clusters = {k: v for k, v in clusters.items() if len(v) > 1}
    logger.info(f"\n  [Skill yang Di-merge (Clusters > 1 member): "
                f"{len(merged_clusters)} cluster]")

    # Hanya tampilkan top 30 berdasarkan ukuran cluster
    sorted_clusters = sorted(merged_clusters.items(), key=lambda x: -len(x[1]))
    for canonical_root, members in sorted_clusters[:30]:
        canonical = canonical_map[list(members)[0]]
        member_list = ", ".join(sorted(members))
        logger.info(f"    canonical: '{canonical}' <- [{member_list}]")

    if len(sorted_clusters) > 30:
        logger.info(f"    ... dan {len(sorted_clusters) - 30} cluster lainnya")

    # Tampilkan OBE mapping lengkap
    logger.info(f"\n  [MAPPING LENGKAP OBE → CANONICAL]")
    df_obe = df_master[df_master['source'] == 'OBE'].sort_values('original_skill')
    for _, row in df_obe.iterrows():
        status_icon = '✅' if row['status'] == 'accepted' else '⚠️'
        method_label = row['mapping_method']
        logger.info(f"    {status_icon} {row['original_skill']:35s} -> "
                     f"{row['canonical_skill']:30s} "
                     f"(sim: {row['similarity_score']:.4f}, {method_label})")

    # Validasi: cek apakah ada forbidden merge yang lolos
    logger.info(f"\n  [VALIDASI FORBIDDEN MERGES]")
    violations = 0
    for group in FORBIDDEN_MERGE_GROUPS:
        # Cek apakah ada dua skill di group ini yang punya canonical sama
        canonicals_in_group = {}
        for skill in group:
            if skill in canonical_map:
                canon = canonical_map[skill]
                if canon not in canonicals_in_group:
                    canonicals_in_group[canon] = []
                canonicals_in_group[canon].append(skill)

        for canon, skills in canonicals_in_group.items():
            if len(skills) > 1:
                logger.info(f"    ❌ VIOLATION: {skills} di-merge ke '{canon}'")
                violations += 1

    if violations == 0:
        logger.info(f"    ✅ Tidak ada pelanggaran forbidden merge.")

    # Review pairs (0.70-0.84)
    review_pairs = semantic_pairs[
        (semantic_pairs['similarity'] >= SEMANTIC_THRESHOLD_REVIEW) &
        (semantic_pairs['similarity'] < SEMANTIC_THRESHOLD_ACCEPTED)
    ].head(20)

    if len(review_pairs) > 0:
        logger.info(f"\n  [Pasangan REVIEW (similarity 0.70-0.84) — Top 20]")
        for _, p in review_pairs.iterrows():
            logger.info(f"    '{p['skill_a']}' <-> '{p['skill_b']}' "
                         f"(sim: {p['similarity']:.4f})")


# ============================================================
# MAIN
# ============================================================
def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    logger.info("=" * 60)
    logger.info("TAHAP 5-8: SEMANTIC MATCHING & CANONICAL SKILL (REVISI)")
    logger.info("=" * 60)

    # Load raw skills
    obe_skills, job_skills, course_skills = load_raw_skills()
    all_skills = obe_skills | job_skills | course_skills
    skill_sources = build_skill_source_map(obe_skills, job_skills, course_skills)

    logger.info(f"\n  Total unique skills (gabungan 3 sumber): {len(all_skills)}")

    # Tahap 5: Exact Match (implicit — same string = same canonical)
    logger.info("\n  [Tahap 5] Exact Match (implicit via lowercase)...")

    # Tahap 6: Semantic Match
    logger.info("\n  [Tahap 6] Semantic Match...")
    semantic_pairs, skills_list, sim_matrix = semantic_match_phase(all_skills)

    # Tahap 7: Build Canonical Mapping (with constraints)
    logger.info("\n  [Tahap 7] Building Canonical Skill Master (with constraints)...")
    canonical_map, clusters = build_canonical_mapping(
        all_skills, skill_sources, semantic_pairs
    )

    # Generate master CSV
    df_master = generate_master_csv(all_skills, skill_sources, canonical_map, semantic_pairs)

    # Tahap 8: Review Report
    print_review_report(df_master, canonical_map, clusters, semantic_pairs)

    # Simpan semantic pairs untuk referensi
    semantic_pairs.to_csv(OUTPUT_DIR / "semantic_pairs.csv", index=False)
    logger.info(f"\n  Semantic pairs disimpan: {OUTPUT_DIR / 'semantic_pairs.csv'}")

    logger.info("\n" + "=" * 60)
    logger.info("BERHENTI DI TAHAP 8.")
    logger.info("Silakan review canonical_skill_master.csv")
    logger.info("sebelum lanjut ke Neo4j.")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
