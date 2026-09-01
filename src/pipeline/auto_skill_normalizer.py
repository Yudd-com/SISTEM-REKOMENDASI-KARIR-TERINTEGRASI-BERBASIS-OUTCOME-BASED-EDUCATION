"""
auto_skill_normalizer.py
========================
Modul normalisasi & kanonikalisasi skill berbasis Semantic Clustering & Root Canonicalization.

Mengelompokkan ribuan variasi kata/frasa sinonim, imbuhan, dan variasi bahasa
menjadi satu bentuk Canonical Skill yang ringkas, baku, dan standar industri.

Contoh transformasi:
- 'agile methodology', 'agile methodologies', 'agile fundamentals', 'agile methods' -> 'agile'
- 'python programming', 'python language', 'pemrograman python'                    -> 'python'
- 'basis data', 'sistem basis data', 'database system', 'database management'      -> 'database'
- 'machine learning algorithms', 'pembelajaran mesin', 'ml techniques'             -> 'machine learning'
- 'jaringan komputer', 'computer networking', 'network fundamentals'               -> 'networking'
"""

import os
import re
import unicodedata
from pathlib import Path
import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

CURRENT_DIR = Path(__file__).resolve().parent
EKSTRAKSI_DIR = CURRENT_DIR / "Ekstraksi Skill"
NORMALISASI_DIR = CURRENT_DIR / "Normalisasi Skill"
NORMALISASI_DIR.mkdir(parents=True, exist_ok=True)

INPUT_EXTRACTION_XLSX = EKSTRAKSI_DIR / "skill_extraction_result.xlsx"
OUTPUT_CANONICAL_XLSX = NORMALISASI_DIR / "canonical_skill_master.xlsx"
OUTPUT_NORM_RESULT_XLSX = NORMALISASI_DIR / "skill_normalization_result.xlsx"
OUTPUT_REPORT_XLSX = NORMALISASI_DIR / "normalization_report.xlsx"
OUTPUT_REVIEW_XLSX = EKSTRAKSI_DIR / "skill_review_candidates.xlsx"
OUTPUT_UNMATCHED_XLSX = NORMALISASI_DIR / "unmatched_skills.xlsx"

MODEL_NAME = "all-MiniLM-L6-v2"

# Kata-kata pengisi / modifier umum yang sering menempel pada istilah skill
GENERIC_MODIFIERS = [
    r"\bmethodologies\b", r"\bmethodology\b", r"\bmethods\b", r"\bmethod\b",
    r"\bfundamentals\b", r"\bfundamental\b", r"\bbasics\b", r"\bbasic\b",
    r"\bknowledge\b", r"\bunderstanding\b", r"\bawareness\b", r"\boversight\b",
    r"\bskills\b", r"\bskill\b", r"\btechniques\b", r"\btechnique\b",
    r"\bconcepts\b", r"\bconcept\b", r"\bprinciples\b", r"\bprinciple\b",
    r"\bintroduction to\b", r"\bintro to\b", r"\bintroductory\b",
    r"\badvanced\b", r"\bintermediate\b", r"\bbeginner\b",
    r"\bprogramming language\b", r"\blanguage\b",
    r"\bkompetensi\b", r"\bkemampuan\b", r"\bkonsep dasar\b", r"\bdasar-dasar\b",
    r"\bdasar\b", r"\bprinsip\b", r"\bpengenalan\b", r"\bpenerapan\b", r"\bimplementasi\b",
    r"\bpemahaman\b", r"\bteori\b", r"\bpengantar\b", r"\bsistem\b"
]

# Kamus Sinonim & Istilah Lintas Bahasa Baku (Indonesian <-> English <-> Standar Industri)
CORE_SYNONYM_MAP = {
    # Agile & Project Management
    "agile methodologies": "agile",
    "agile methodology": "agile",
    "agile methods": "agile",
    "agile fundamentals": "agile",
    "agile knowledge": "agile",
    "agile understanding": "agile",
    "agile awareness": "agile",
    "agile facilitation": "agile",
    "agile oversight": "agile",
    "agile leadership": "agile",
    "agile documentation": "agile",
    "agile workflow management": "agile",
    "scrum master": "scrum",
    "scrum framework": "scrum",
    "scrum methodology": "scrum",
    
    # Programming & Languages
    "python programming": "python",
    "python language": "python",
    "python 3": "python",
    "pemrograman python": "python",
    "java programming": "java",
    "pemrograman java": "java",
    "c# .net": "c#",
    "c#.net": "c#",
    "c++ programming": "c++",
    "javascript programming": "javascript",
    "js": "javascript",
    "golang": "go",
    "go programming": "go",
    "php programming": "php",
    "r programming": "r",
    "pemrograman web": "web development",
    "web programming": "web development",
    "algoritma dan pemrograman": "algorithm & programming",
    "algoritma & pemrograman": "algorithm & programming",
    "algoritma & pemrograman dasar": "algorithm & programming",
    "algoritma pemrograman": "algorithm & programming",
    "algorithm design": "algorithm & programming",
    "struktur data": "data structures",
    "struktur data dan algoritma": "data structures & algorithms",
    "oop": "object-oriented programming",
    "oop (object oriented programming)": "object-oriented programming",
    "object oriented programming": "object-oriented programming",
    "pemrograman berorientasi objek": "object-oriented programming",
    
    # Data & AI
    "basis data": "database",
    "basis data / database": "database",
    "sistem basis data": "database",
    "database system": "database",
    "database management": "database",
    "relational database": "relational database",
    "rdbms": "relational database",
    "sql programming": "sql",
    "sql query": "sql",
    "sql queries": "sql",
    "analisis data": "data analysis",
    "data analytics": "data analysis",
    "data mining": "data mining",
    "penambangan data": "data mining",
    "data warehouse": "data warehousing",
    "data warehousing": "data warehousing",
    "gudang data": "data warehousing",
    "business intelligence": "business intelligence",
    "bi": "business intelligence",
    "machine learning": "machine learning",
    "pembelajaran mesin": "machine learning",
    "machine learning algorithms": "machine learning",
    "deep learning": "deep learning",
    "pembelajaran mendalam": "deep learning",
    "neural network": "neural networks",
    "artificial intelligence": "artificial intelligence",
    "kecerdasan buatan": "artificial intelligence",
    "ai": "artificial intelligence",
    "natural language processing": "natural language processing",
    "nlp": "natural language processing",
    "computer vision": "computer vision",
    
    # Networking, Security & Cloud
    "jaringan komputer": "networking",
    "computer networking": "networking",
    "computer networks": "networking",
    "network security": "network security",
    "keamanan jaringan": "network security",
    "keamanan siber": "cybersecurity",
    "cyber security": "cybersecurity",
    "kriptografi": "cryptography",
    "cloud computing": "cloud computing",
    "komputasi awan": "cloud computing",
    "aws": "amazon web services",
    "amazon web services": "amazon web services",
    "google cloud platform": "google cloud platform",
    "gcp": "google cloud platform",
    "microsoft azure": "azure",
    "docker container": "docker",
    "kubernetes orchestration": "kubernetes",
    "ci/cd pipeline": "ci/cd",
    
    # Systems & UI/UX
    "sistem informasi": "information systems",
    "konsep dasar sistem informasi": "information systems",
    "enterprise resource planning": "erp",
    "erp (enterprise resource planning)": "erp",
    "ui/ux": "ui/ux",
    "ui/ux design": "ui/ux",
    "user interface / user experience": "ui/ux",
    "desain antarmuka": "ui/ux",
    "uml": "uml",
    "uml (unified modeling language)": "uml",
    "erd": "erd",
    "erd (entity relationship diagram)": "erd",

    # Academic Curriculum & Software Engineering
    "administrasi basis data": "database administration",
    "arsitektur jaringan": "network architecture",
    "arsitektur sistem basis data": "database architecture",
    "basis data logikal": "database design",
    "desain basis data": "database design",
    "mendesain basis data konseptual": "database design",
    "pengembangan sistem basis data": "database development",
    "sistem database": "database",
    "manipulasi data relasional": "sql",
    "query": "sql",
    "stored procedure": "stored procedures",
    "algoritma & pemrograman dasar": "algorithm & programming",
    "algoritma": "algorithms",
    "algoritma graph": "graph algorithms",
    "algoritma heuristik": "heuristic algorithms",
    "struktur data": "data structures",
    "pemrograman": "programming",
    "program": "programming",
    "pemrograman integer": "integer programming",
    "pemrograman open source": "open source software",
    "rekayasa kebutuhan perangkat lunak": "software requirements engineering",
    "perangkat lunak": "software engineering",
    "prototyping": "prototyping",
    "pseudocode": "pseudocode",
    "flowchart": "flowchart",
    "usability testing": "usability testing",
    "use case diagram": "use case diagram",
    
    # IT Governance, Audit, Security & Management
    "audit ti": "it audit",
    "tatakelola ti": "it governance",
    "strategi ti": "it strategy",
    "manajemen layanan ti": "it service management",
    "keamanan informasi": "information security",
    "tatakelola keamanan informasi": "information security",
    "manajemen keamanan siber": "cybersecurity",
    "pengembangan keamanan data": "data security",
    "proteksi fisik": "physical security",
    "vulnerability assessment": "vulnerability assessment",
    "manajemen resiko": "risk management",
    "sistem pengendalian internal": "internal control systems",
    "cobit": "cobit",
    "togaf": "togaf",
    "enterprise architecture": "enterprise architecture",
    "transformasi digital": "digital transformation",
    "teknologi informasi": "information technology",
    "infrastruktur": "it infrastructure",
    "infrastruktur sistem": "it infrastructure",
    "perangkat keras komputer": "computer hardware",
    "sistem komputer": "computer systems",
    "perangkat": "hardware",
    
    # Data Science, AI & Statistics
    "analisis data": "data analysis",
    "menganalisa data": "data analysis",
    "pengumpulan data": "data collection",
    "pemodelan data": "data modeling",
    "data lake": "data lake",
    "data science": "data science",
    "data scientist": "data science",
    "analisis kecerdasan mesin": "machine learning",
    "ml": "machine learning",
    "ai": "artificial intelligence",
    "iot": "internet of things",
    "cognitive computing": "cognitive computing",
    "cognitive problem solver": "problem solving",
    "expert systems": "expert systems",
    "komputasi lunak": "soft computing",
    "soft computing": "soft computing",
    "komputasional": "computational thinking",
    "visualisasi": "data visualization",
    "konsep statistik": "statistics",
    "statistika/probabilitas": "statistics",
    "regresi": "regression analysis",
    "klasifikasi (data)": "data classification",
    "decision tree": "decision tree",
    "clustering": "clustering",
    "knowledge graph": "knowledge graph",
    
    # Business, Operations & Systems
    "proses bisnis": "business process",
    "integrasi proses bisnis": "business process integration",
    "strategi bisnis": "business strategy",
    "manajemen rantai pasok": "supply chain management",
    "scm (supply chain management)": "supply chain management",
    "crm": "crm",
    "crm (customer relationship management)": "crm",
    "integrasi erp": "erp",
    "kpi (key performance indicator)": "kpi",
    "kpi": "kpi",
    "manajemen permintaan": "demand management",
    "perencanaan agregat": "aggregate planning",
    "peramalan": "forecasting",
    "sistem enterprise": "enterprise systems",
    "sistem fluss": "flow systems",
    "sistem keputusan berbasis model": "decision support systems",
    "validasi model simulasi sistem dinamika": "system dynamics simulation",
    "simulasi": "simulation modeling",
    "mensimulasikan": "simulation modeling",
    "analisis sensitivitas": "sensitivity analysis",
    "optimasi": "optimization",
    "optimasi kombinatorik": "combinatorial optimization",
    "simpleks": "simplex algorithm",
    "matematika": "mathematics",
    "logika": "logic",
    "struktur diskrit": "discrete mathematics",
    "desain organisasi": "organization design",
    "contingencies factors": "contingency planning",
    "structural configurations": "organizational structure",
    
    # Networking & Web
    "komunikasi jaringan": "networking",
    "perangkat jaringan": "networking",
    "protokol internet": "networking",
    "routing": "routing",
    "switching": "network switching",
    "osi layer": "osi model",
    "tcp/ip": "tcp/ip",
    "ipv4": "ipv4",
    "ipv6": "ipv6",
    "ipv6)": "ipv6",
    "firewall": "firewall",
    "cisco": "cisco networking",
    "rest api": "rest api",
    "api": "api",
    "graphql": "graphql",
    "http": "http",
    "json": "json",
    "xml": "xml",
    "sprint (agile)": "scrum",
    "kanban": "kanban",
    "figma": "figma",
    "memvalidasi": "data validation",
    "perbaikan masalah": "troubleshooting",
    "technical": "technical skills",
    "deteksi": "anomaly detection",
    "encoding": "data encoding"
}



def clean_skill_str(s: str) -> str:
    """Membersihkan string secara menyeluruh dari tanda baca, token aneh, dan sisa kurung."""
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
    
    # 3. Hapus kurung buka/tutup dan isi di dalamnya
    s = re.sub(r'\s*\([^)]*\)?', '', s)
    s = re.sub(r'\s*\[[^\]]*\]?', '', s)
    s = re.sub(r'[\(\)\[\]\{\}\<\>\"\'`]', ' ', s)
    
    # 4. Hapus tanda baca di awal dan akhir kecuali .net, c#, c++
    s = re.sub(r'^[^a-zA-Z0-9\.\#\+]+', '', s)
    s = re.sub(r'[^a-zA-Z0-9\.\#\+]+$', '', s)
    if s.endswith('.') and not s.lower().endswith('.net'):
        s = s.rstrip('.').strip()
    s = re.sub(r'[\)\}\]\:\;\,\.]+$', '', s)
    
    # 5. Hapus tanda baca di tengah yang aneh
    s = re.sub(r'[:;|_~!?*]+', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip().lower()
    return s




def get_lemmatized_root(skill: str) -> str:
    """Mengekstrak bentuk akar (root concept) dari frasa skill."""
    s = skill
    # 1. Cek kamus sinonim inti
    if s in CORE_SYNONYM_MAP:
        return CORE_SYNONYM_MAP[s]
        
    # 2. Hapus modifier umum jika bukan istilah tunggal
    words = s.split()
    if len(words) > 1:
        s_clean = s
        for mod in GENERIC_MODIFIERS:
            s_clean = re.sub(mod, "", s_clean, flags=re.IGNORECASE).strip()
        s_clean = re.sub(r"\s+", " ", s_clean).strip(" -.,:/")
        if len(s_clean) >= 3 and s_clean in CORE_SYNONYM_MAP:
            return CORE_SYNONYM_MAP[s_clean]
        elif len(s_clean) >= 3:
            return s_clean

    return s


def run_normalization():
    print("=" * 65)
    print("MEMULAI NORMALISASI & SEMANTIC CLUSTERING SKILL")
    print("=" * 65)

    if not INPUT_EXTRACTION_XLSX.exists():
        print(f"Error: File ekstraksi {INPUT_EXTRACTION_XLSX} tidak ditemukan.")
        return

    print("\n[1/5] Memuat skill mentah dari seluruh sumber...")
    df_raw_combined = pd.read_excel(INPUT_EXTRACTION_XLSX, sheet_name="All_Raw_Combined")
    df_job = pd.read_excel(INPUT_EXTRACTION_XLSX, sheet_name="Job_Skills")
    df_course = pd.read_excel(INPUT_EXTRACTION_XLSX, sheet_name="Course_Skills")

    raw_skills = sorted(list(set([clean_skill_str(s) for s in df_raw_combined["skill"] if clean_skill_str(s)])))
    print(f"  -> Total Skill Mentah Dievaluasi: {len(raw_skills):,} skill")

    # 2. Pembentukan Klaster Root & Canonical Representation
    print("\n[2/5] Menerapkan Rule-based Lemmatization & Core Synonym Reduction...")
    pre_canonical_map = {}
    for s in raw_skills:
        root = get_lemmatized_root(s)
        pre_canonical_map[s] = root

    unique_roots = sorted(list(set(pre_canonical_map.values())))
    print(f"  -> Reduksi Tahap 1: Dari {len(raw_skills):,} variasi menjadi {len(unique_roots):,} akar konsep unik.")

    # 3. Semantic Embedding & Cross-Matching
    print(f"\n[3/5] Meng-encode Sentence Embeddings AI ({MODEL_NAME}) untuk Cross-Lingual & Synonym Clustering...")
    model = SentenceTransformer(MODEL_NAME)
    root_embeddings = model.encode(unique_roots, batch_size=64, show_progress_bar=True, normalize_embeddings=True)

    sim_matrix = cosine_similarity(root_embeddings)
    
    # Pengelompokan Klaster Semantik (Kemiripan >= 0.85)
    root_to_cluster_canonical = {}
    visited = set()

    for i, root in enumerate(unique_roots):
        if i in visited:
            continue
        # Cari semua anggota klaster dengan cosine similarity >= 0.85
        cluster_indices = np.where(sim_matrix[i] >= 0.85)[0]
        cluster_members = [unique_roots[idx] for idx in cluster_indices]
        
        # Pilih representasi kanonikal terbaik:
        # Prioritaskan istilah yang ada di CORE_SYNONYM_MAP atau istilah paling ringkas dan baku
        best_rep = min(cluster_members, key=lambda x: (0 if x in CORE_SYNONYM_MAP.values() else 1, len(x), x))
        
        for idx in cluster_indices:
            visited.add(idx)
            root_to_cluster_canonical[unique_roots[idx]] = best_rep

    # 4. Bangun Hasil Pemetaan Akhir dengan Batch Encoding
    print("\n[4/5] Mengompilasi Tabel Canonical Skill Master...")
    canonical_master_rows = []
    review_candidate_rows = []
    unmatched_rows = []

    # Pre-map all final canonicals
    mapped_canonicals = [root_to_cluster_canonical.get(pre_canonical_map[orig], pre_canonical_map[orig]) for orig in raw_skills]
    
    # Batch encode all raw skills and their targets
    print("  -> Batch encoding seluruh pasangan skill untuk penilaian skor semantik...")
    all_orig_embs = model.encode(raw_skills, batch_size=128, show_progress_bar=False, normalize_embeddings=True)
    all_canon_embs = model.encode(mapped_canonicals, batch_size=128, show_progress_bar=False, normalize_embeddings=True)
    
    # Calculate cosine similarity for all rows simultaneously (dot product of normalized vectors)
    pair_sims = np.sum(all_orig_embs * all_canon_embs, axis=1)

    for i, orig in enumerate(raw_skills):
        final_canonical = mapped_canonicals[i]
        sim_score = float(pair_sims[i])
        
        if orig == final_canonical:
            sim_score = 1.0000
            method = "exact"
            status = "accepted"
        elif sim_score >= 0.70 or orig in CORE_SYNONYM_MAP:
            method = "semantic_clustered"
            status = "accepted"
        elif 0.55 <= sim_score < 0.70:
            method = "semantic_review"
            status = "review_candidate"
            review_candidate_rows.append({
                "original_skill": orig,
                "candidate_canonical_skill": final_canonical,
                "similarity_score": round(sim_score, 4),
                "status": "review_needed"
            })
        else:
            method = "unmatched_retained"
            status = "unmatched_retained"
            final_canonical = orig
            unmatched_rows.append({
                "original_skill": orig,
                "best_candidate": final_canonical,
                "similarity_score": round(sim_score, 4),
                "reason": "Similarity < 0.55"
            })

        canonical_master_rows.append({
            "original_skill": orig,
            "canonical_skill": final_canonical,
            "similarity_score": round(sim_score, 4),
            "mapping_method": method,
            "status": status
        })


    df_canonical_master = pd.DataFrame(canonical_master_rows)
    df_review = pd.DataFrame(review_candidate_rows)
    df_unmatched = pd.DataFrame(unmatched_rows)

    num_transformed = (df_canonical_master["original_skill"] != df_canonical_master["canonical_skill"]).sum()
    print(f"  -> Total Skill Berhasil Dikelompokkan/Dinormalisasi: {num_transformed:,} dari {len(df_canonical_master):,} skill!")
    print(f"  -> Total Canonical Unique Skills Akhir: {df_canonical_master['canonical_skill'].nunique():,} skill baku.")

    # 5. Simpan Seluruh Output Excel
    print("\n[5/5] Menyimpan output Excel Canonical Master & Normalisasi...")
    
    with pd.ExcelWriter(OUTPUT_CANONICAL_XLSX, engine="openpyxl") as writer:
        df_canonical_master.to_excel(writer, sheet_name="Canonical_Master", index=False)
    print(f"  -> {OUTPUT_CANONICAL_XLSX.name} tersimpan.")

    with pd.ExcelWriter(OUTPUT_REVIEW_XLSX, engine="openpyxl") as writer:
        df_review.to_excel(writer, sheet_name="Review_Candidates", index=False)
    print(f"  -> {OUTPUT_REVIEW_XLSX.name} tersimpan.")

    with pd.ExcelWriter(OUTPUT_UNMATCHED_XLSX, engine="openpyxl") as writer:
        df_unmatched.to_excel(writer, sheet_name="Unmatched_Skills", index=False)
    print(f"  -> {OUTPUT_UNMATCHED_XLSX.name} tersimpan.")

    # Simpan laporan
    summary_metrics = [
        {"Metrik": "Total Raw Skills Mentah", "Nilai": len(raw_skills)},
        {"Metrik": "Total Canonical Unique Skills (Baku)", "Nilai": df_canonical_master["canonical_skill"].nunique()},
        {"Metrik": "Skill Berhasil Dinormalisasi / Dikelompokkan", "Nilai": num_transformed},
        {"Metrik": "Persentase Konsolidasi", "Nilai": f"{(num_transformed/len(raw_skills))*100:.2f}%"},
        {"Metrik": "AI Model yang Digunakan", "Nilai": MODEL_NAME}
    ]
    df_metrics = pd.DataFrame(summary_metrics)
    with pd.ExcelWriter(OUTPUT_REPORT_XLSX, engine="openpyxl") as writer:
        df_metrics.to_excel(writer, sheet_name="Summary_Metrics", index=False)
        df_canonical_master[df_canonical_master["original_skill"] != df_canonical_master["canonical_skill"]].head(2000).to_excel(writer, sheet_name="Normalized_Samples", index=False)
    print(f"  -> {OUTPUT_REPORT_XLSX.name} tersimpan.")

    print("\n" + "=" * 65)
    print("NORMALISASI SKILL DENGAN SEMANTIC CLUSTERING SELESAI DENGAN SUKSES!")
    print("=" * 65)


if __name__ == "__main__":
    run_normalization()
