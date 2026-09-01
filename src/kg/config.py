"""
config.py — Konfigurasi Pipeline Knowledge Graph (Project KG 2)

Multi-Kampus: Jakarta + Surabaya
Semua threshold dan path disimpan di sini agar mudah diubah
tanpa menyentuh logika kode utama.
"""
import os
from pathlib import Path

# ============================================================
# PATH
# ============================================================
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_RAW_DIR = BASE_DIR / "data_raw"
DATA_CLEAN_DIR = BASE_DIR / "data_clean"
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_NORM_DIR = OUTPUT_DIR / "normalisasi_skill"
OUTPUT_KG_DIR = OUTPUT_DIR / "hasil_kg"

# Pastikan folder output ada
OUTPUT_NORM_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_KG_DIR.mkdir(parents=True, exist_ok=True)

# Dataset files — Multi-Kampus (Jakarta + Surabaya + ITS)
OBE_FILES = {
    "Jakarta": DATA_RAW_DIR / "obe" / "OBE_JAKARTA.xlsx",
    "Surabaya": DATA_RAW_DIR / "obe" / "OBE_SURABAYA.xlsx",
    "ITS": DATA_RAW_DIR / "obe" / "RPS_skill_extracted_20260809_185306.csv",
}

STUDENT_FILES = {
    "All_3Kampus": DATA_CLEAN_DIR / "obe" / "DATA_MAHASISWA_DUMMY_100.xlsx",
}

JOBS_FILE = DATA_RAW_DIR / "job" / "DATA_JOB_EKSTRAKSI_DAN_NORMALISASI.xlsx"
COURSE_FILE = DATA_RAW_DIR / "course" / "Online_Course_clean.xlsx"

# ============================================================
# THRESHOLD — OBE
# ============================================================
# Berdasarkan ketentuan yang diberikan untuk penelitian ini.
# Score >= 50.01 → CLO terpenuhi → Skill dianggap dimiliki mahasiswa.
OBE_SKILL_THRESHOLD = 50.01

# ============================================================
# THRESHOLD — SEMANTIC MATCHING
# ============================================================
# Cosine Similarity >= 0.85 → Accepted
# 0.70 – 0.84             → Review
# < 0.70                   → Rejected
SEMANTIC_THRESHOLD_ACCEPTED = 0.85
SEMANTIC_THRESHOLD_REVIEW = 0.70

# ============================================================
# MODEL — SENTENCE EMBEDDING
# ============================================================
SENTENCE_MODEL = "all-MiniLM-L6-v2"

# ============================================================
# NEO4J
# ============================================================
NEO4J_URI = "bolt://127.0.0.1:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "OBE12345"  # HARAP DIGANTI

# ============================================================
# SKILL SPLITTING (OBE) — termasuk kosakata OBE baru
# ============================================================
# Skill OBE yang menggunakan format gabungan dan harus dipecah
SKILL_SPLIT_MAP = {
    "java/python": ["java", "python"],
    "agile/scrum": ["agile", "scrum"],
    "sap/oracle": ["sap", "oracle"],
    "decision tree/knn/svm": ["decision tree", "knn", "svm"],
    "dashboard & reporting": ["dashboard", "reporting"],
    "wbs & scheduling": ["wbs", "scheduling"],
    # OBE Jakarta additions
    "algoritma & pemrograman dasar": ["algorithm design", "basic programming"],
    # OBE Surabaya additions
    "konsep dasar sistem informasi": ["information systems"],
}

# ============================================================
# FORBIDDEN MERGE PAIRS
# ============================================================
# Pasangan skill yang TIDAK BOLEH di-merge ke satu cluster,
# meskipun cosine similarity tinggi.
# Prinsip: false merge lebih berbahaya daripada unmatched.
FORBIDDEN_MERGE_GROUPS = [
    # Web technologies — harus terpisah
    {"html", "css", "javascript", "typescript"},
    # Programming languages — harus terpisah
    {"python", "java", "go", "c++", "c#", "ruby", "php", "r", "kotlin", "swift"},
    # Agile vs Scrum — metodologi terkait tapi kompetensi berbeda
    {"agile", "scrum"},
    # Operating Systems — harus terpisah
    {"linux", "windows", "macos"},
    # Framework vs language
    {"react", "angular", "vue"},
    # Analisis vs Measurement
    {"performance analysis", "performance measurement"},
    # Testing types
    {"usability testing", "software testing", "penetration testing"},
    # Governance & Control — domain berbeda
    {"internal control", "version control", "access control"},
    # Database types
    {"sql", "nosql", "mongodb", "postgresql"},
    # Cloud providers
    {"aws", "azure", "gcp", "google cloud"},
]

# ============================================================
# MANUAL CANONICAL OVERRIDES
# ============================================================
# Mapping manual yang memaksa skill tertentu ke canonical tertentu.
# Format: original_skill -> canonical_skill
# Override ini diterapkan SETELAH semantic matching, menimpa hasil otomatis.
MANUAL_CANONICAL_OVERRIDES = {
    # ETL variants → etl
    "etl process": "etl",
    "etl processes": "etl",
    "etl basics": "etl",
    "etl concepts": "etl",
    "etl fundamentals": "etl",
    "etl awareness": "etl",
    "etl process awareness": "etl",
    "etl process knowledge": "etl",
    "etl process understanding": "etl",
    "etl understanding": "etl",
    "etl tools introduction": "etl",

    # OOP variants → object-oriented programming
    "oop principles": "object-oriented programming",
    "oop basics": "object-oriented programming",
    "oop": "object-oriented programming",
    "object-oriented programming": "object-oriented programming",
    "object oriented programming": "object-oriented programming",

    # Usability — pertahankan sebagai usability testing
    "usability testing": "usability testing",
    "usability basics": "usability testing",

    # Linux — jangan campur dengan Windows
    "linux administration": "linux",
    "linux administration basics": "linux",
    "linux administration expert": "linux",
    "linux administration fundamentals": "linux",
    "linux expert": "linux",
    "linux basics": "linux",
    "linux fundamentals": "linux",

    # Windows — terpisah dari Linux
    "windows fundamentals": "windows",
    "windows os basics": "windows",
    "windows os fundamentals": "windows",

    # Linux+Windows gabungan → pisahkan tidak bisa lewat override,
    # akan ditangani di split phase

    # Data structures
    "data structure": "data structures",
    "data structures": "data structures",

    # Neural networks
    "neural network": "neural networks",
    "neural networks": "neural networks",

    # Design patterns
    "design pattern": "design patterns",
    "design patterns": "design patterns",

    # Dashboard
    "dashboard": "dashboard",
    "dashboards": "dashboard",

    # Security audit
    "security audit": "security audits",
    "security audits": "security audits",

    # TCP/IP
    "tcp/ip protocol": "tcp/ip",
    "tcp/ip": "tcp/ip",
}

# ============================================================
# COMPOUND SKILL SPLITS (All Datasets)
# ============================================================
# Skill gabungan yang muncul di dataset Jobs/Course dan harus dipecah.
# Diterapkan pada SEMUA sumber, bukan hanya OBE.
COMPOUND_SKILL_SPLITS = {
    # Programming language combos
    "python, go, java": ["python", "go", "java"],
    "python, java": ["python", "java"],
    "c/c++": ["c", "c++"],

    # Web combos
    "html, css, javascript basics": ["html", "css", "javascript"],
    "html & css": ["html", "css"],
    "html/css": ["html", "css"],
    "html/css basics": ["html", "css"],
    "basic html/css": ["html", "css"],
    "html/css/xml": ["html", "css", "xml"],
    "xml/html/css": ["xml", "html", "css"],

    # OS combos
    "linux/windows": ["linux", "windows"],
    "linux/windows basics": ["linux", "windows"],
    "linux/windows administration": ["linux", "windows"],
    "linux/windows administration expert": ["linux", "windows"],
    "linux/windows expert": ["linux", "windows"],
    "linux/windows os expert": ["linux", "windows"],
    "linux/windows os fundamentals": ["linux", "windows"],
    "windows/linux basics": ["linux", "windows"],
    "linux and windows expert": ["linux", "windows"],
    "linux and windows os basics": ["linux", "windows"],
    "linux and windows os expert": ["linux", "windows"],

    # VCS combos
    "git/github/gitlab": ["git", "github", "gitlab"],
    "github/gitlab": ["github", "gitlab"],

    # Agile combos (di Jobs/Course)
    "agile/scrum": ["agile", "scrum"],
    "agile/scrum understanding": ["agile", "scrum"],
}
