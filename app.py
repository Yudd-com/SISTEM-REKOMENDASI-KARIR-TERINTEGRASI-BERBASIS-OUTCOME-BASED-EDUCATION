"""
app.py — Streamlit Prototype (Project KG 2)
Sistem Rekomendasi Karir & Kursus Terintegrasi Berbasis Outcome Based Education:
Rekomendasi Pembelajaran dari Knowledge Graph & Relative Skill Gap Analysis

Multi-Kampus: Telkom University Jakarta, Telkom University Surabaya, ITS Surabaya
Dataset: 100 Mahasiswa Terpadu | 492 Posisi Karir | 11.196 Kursus Online Master

Run:
    python -m streamlit run app.py
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path

# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title="OBE Career & Course Recommender",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# CUSTOM CSS & THEME
# ============================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

.section-title {
    font-size: 1.05rem;
    font-weight: 700;
    color: #888;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    border-bottom: 1px solid #333;
    padding-bottom: 8px;
    margin: 20px 0 14px 0;
}

/* Skill pills */
.pill-row { line-height: 2.2rem; }
.pill-green {
    display: inline-block;
    background: #064E3B;
    color: #6EE7B7;
    border-radius: 20px;
    padding: 2px 12px;
    font-size: 0.80rem;
    margin: 2px 3px;
    border: 1px solid #065F46;
}
.pill-red {
    display: inline-block;
    background: #450A0A;
    color: #FCA5A5;
    border-radius: 20px;
    padding: 2px 12px;
    font-size: 0.80rem;
    margin: 2px 3px;
    border: 1px solid #7F1D1D;
}
.pill-blue {
    display: inline-block;
    background: #1E3A5F;
    color: #93C5FD;
    border-radius: 20px;
    padding: 2px 12px;
    font-size: 0.80rem;
    margin: 2px 3px;
    border: 1px solid #1D4ED8;
}
.badge-gold {
    background: #78350F;
    color: #FDE68A;
    border-radius: 12px;
    padding: 2px 8px;
    font-size: 0.75rem;
    font-weight: 700;
    border: 1px solid #D97706;
}
</style>
""", unsafe_allow_html=True)

# ============================================================
# PATHS & CONFIGURATION
# ============================================================
BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_NORM_DIR = OUTPUT_DIR / "normalisasi_skill"
OUTPUT_KG_DIR = OUTPUT_DIR / "hasil_kg"

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

MAX_COURSES_PER_SKILL = 4
TOP_PLATFORMS = ['google', 'ibm', 'meta', 'microsoft', 'deeplearning.ai', 'coursera', 'edx', 'udemy', 'university']

# ============================================================
# HELPER FUNCTIONS
# ============================================================
def parse_skills(raw) -> list:
    if not raw or str(raw).strip() in ('', 'nan'):
        return []
    return [s.strip().lower() for s in str(raw).split('|') if s.strip()]


def level_sort_key(lvl: str) -> int:
    l = str(lvl).strip().lower()
    if 'beginner' in l: return 1
    if 'intermediate' in l or 'medium' in l: return 2
    if 'mixed' in l: return 3
    if 'advanced' in l: return 4
    return 5


def get_level_label(lvl: str) -> str:
    l = str(lvl).strip().lower()
    if 'beginner' in l: return 'Beginner'
    if 'intermediate' in l or 'medium' in l: return 'Intermediate'
    if 'mixed' in l: return 'Mixed'
    if 'advanced' in l: return 'Advanced'
    return str(lvl).strip() or 'Other'


def _course_priority(c: dict, target_skill: str, fallback_parent: str = None) -> tuple:
    """
    Hitung bobot relevansi judul kursus terhadap target skill.
    Skor lebih rendah = prioritas lebih tinggi (rank 1).
    """
    name = str(c.get('course_name', '')).lower()
    plat = str(c.get('platform', '')).lower()
    ts = target_skill.lower().strip()
    
    score = 0
    # 1. Exact skill string match in course title
    if ts in name:
        score -= 25
    
    # 2. Token match (kata per kata)
    tokens = [t for t in ts.split() if len(t) > 2]
    matched_tokens = sum(1 for t in tokens if t in name)
    score -= (matched_tokens * 6)
    
    # 3. Fallback parent token match
    if fallback_parent:
        fb_tokens = [t for t in fallback_parent.lower().split() if len(t) > 2]
        matched_fb = sum(1 for t in fb_tokens if t in name)
        score -= (matched_fb * 4)
    
    # 4. Top platform bonus
    if any(p in plat for p in ['google', 'ibm', 'meta', 'microsoft', 'deeplearning.ai']):
        score -= 4
    elif any(p in plat for p in TOP_PLATFORMS):
        score -= 2
        
    return (score, name)


def _select_progressive_courses(courses: list, target_skill: str, fallback_parent: str = None) -> list:
    """
    Pilih kursus terbaik berdasarkan relevansi judul & progresivitas level:
    Memprioritaskan 1 Beginner + 1 Intermediate + 1 Mixed + 1 Advanced,
    namun tetap mempertahankan relevansi judul domain tertinggi.
    """
    if not courses:
        return []
        
    # Sort all candidates by relevance score first
    sorted_candidates = sorted(courses, key=lambda c: _course_priority(c, target_skill, fallback_parent))
    
    # Split into level buckets
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
    # Ambil kursus terbaik per level progresif jika relevan
    for b_key in ['beginner', 'intermediate', 'mixed', 'advanced', 'other']:
        if buckets[b_key]:
            best = buckets[b_key][0]
            p_score = _course_priority(best, target_skill, fallback_parent)[0]
            # Prioritaskan jika relevan terhadap skill atau termasuk kandidat teratas
            if p_score < 0 or best in sorted_candidates[:6]:
                selected.append(buckets[b_key].pop(0))
                
    # Isi kekurangan slot dari kandidat terbaik secara keseluruhan
    for c in sorted_candidates:
        if len(selected) >= MAX_COURSES_PER_SKILL:
            break
        if c not in selected:
            selected.append(c)
            
    # Sort final selection berdasarkan urutan level: Beginner → Intermediate → Mixed → Advanced → Other
    selected_sorted = sorted(selected[:MAX_COURSES_PER_SKILL], key=lambda c: level_sort_key(c.get('level', '')))

    # Tambahkan label display
    final_selected = []
    for c in selected_sorted:
        c_copy = dict(c)
        if fallback_parent:
            c_copy['covers_label'] = f"{target_skill} (via: {fallback_parent})"
        else:
            c_copy['covers_label'] = target_skill
        c_copy['level_label'] = get_level_label(c.get('level', ''))
        final_selected.append(c_copy)
        
    return final_selected


@st.cache_data
def _build_skill_index(df_course: pd.DataFrame) -> dict:
    """Build inverted index: skill -> list of course dicts."""
    idx = {}
    grp = df_course.groupby(
        ['course_id', 'course_name', 'platform', 'level'], as_index=False
    )['canonical_skill'].apply(list)
    for _, row in grp.iterrows():
        course_dict = {
            'course_id': row['course_id'],
            'course_name': row['course_name'],
            'platform': row['platform'],
            'level': row['level'],
        }
        for sk in row['canonical_skill']:
            sk = str(sk).strip().lower()
            if sk:
                idx.setdefault(sk, []).append(dict(course_dict))
    return idx


def get_courses_for_missing(skill_index: dict, missing_skills: list) -> dict:
    """
    Mencari kursus rekomendasi untuk setiap missing skill:
    1. Exact match di katalog kursus.
    2. Fallback taxonomy domain (SKILL_TAXONOMY_FALLBACK).
    3. Heuristik pembersihan prefix / suffix kata kunci.
    """
    result = {}
    for skill in missing_skills:
        # 1. Exact match
        courses = [dict(c) for c in skill_index.get(skill, [])]
        if courses:
            result[skill] = _select_progressive_courses(courses, skill)
            continue
            
        # 2. Taxonomy fallback
        fallback_parent = SKILL_TAXONOMY_FALLBACK.get(skill)
        
        # 3. Heuristik Suffix / Prefix
        if not fallback_parent:
            # Check suffixes
            for suffix in [' basics', ' scripting', ' programming',
                           ' development', ' administration', ' architecture',
                           ' techniques', ' analysis', ' fundamentals', ' engineering',
                           ' tools', ' modeling', ' management', ' design', ' skills']:
                if skill.endswith(suffix):
                    cand = skill[:-len(suffix)].strip()
                    if cand in skill_index or cand in SKILL_TAXONOMY_FALLBACK:
                        fallback_parent = cand if cand in skill_index else SKILL_TAXONOMY_FALLBACK[cand]
                        break
                        
        if not fallback_parent:
            # Check prefixes
            for prefix in ['advanced ', 'basic ', 'intro ', 'core ', 'applied ', 'practical ']:
                if skill.startswith(prefix):
                    cand = skill[len(prefix):].strip()
                    if cand in skill_index or cand in SKILL_TAXONOMY_FALLBACK:
                        fallback_parent = cand if cand in skill_index else SKILL_TAXONOMY_FALLBACK[cand]
                        break
                        
        if fallback_parent:
            fb_courses = [dict(c) for c in skill_index.get(fallback_parent, [])]
            if fb_courses:
                result[skill] = _select_progressive_courses(fb_courses, skill, fallback_parent)
                continue
                
        result[skill] = []
    return result


def build_roadmap(courses_map: dict) -> dict:
    roadmap = {}
    for skill, courses in courses_map.items():
        for c in courses:
            lbl = c.get('level_label', get_level_label(c.get('level', '')))
            srt = level_sort_key(c.get('level', ''))
            if lbl not in roadmap:
                roadmap[lbl] = {'sort': srt, 'courses': []}
            roadmap[lbl]['courses'].append(c)
    return dict(sorted(roadmap.items(), key=lambda x: x[1]['sort']))


# ============================================================
# DATA LOADER
# ============================================================
@st.cache_data
def load_data():
    ranking_path = OUTPUT_KG_DIR / "career_ranking_result_v2.csv"
    if not ranking_path.exists():
        ranking_path = OUTPUT_DIR / "career_ranking_result_v2.csv"
        
    course_path = OUTPUT_NORM_DIR / "course_skill_final.csv"
    if not course_path.exists():
        course_path = OUTPUT_DIR / "course_skill_final.csv"

    if not ranking_path.exists() or not course_path.exists():
        return None, None, f"File data tidak ditemukan di {OUTPUT_DIR}"

    df_rank = pd.read_csv(ranking_path, sep=';')
    df_course = pd.read_csv(course_path, sep=';')

    # Normalize campus column
    if 'campus' not in df_rank.columns:
        df_rank['campus'] = df_rank['student_id'].apply(
            lambda x: 'Jakarta' if str(x).startswith('J') else ('Surabaya' if str(x).startswith('S') else 'ITS')
        )
    else:
        df_rank['campus'] = df_rank['campus'].apply(
            lambda x: 'Jakarta' if 'jakarta' in str(x).lower() else ('Surabaya' if 'surabaya' in str(x).lower() and not 'its' in str(x).lower() else 'ITS')
        )

    df_course['level'] = df_course['level'].fillna('').astype(str).str.strip()
    df_course['canonical_skill'] = df_course['canonical_skill'].fillna('').str.strip().str.lower()
    for col in ['required_skills', 'matched_skills', 'missing_skills']:
        if col in df_rank.columns:
            df_rank[col] = df_rank[col].fillna('')

    return df_rank, df_course, None


df_rank, df_course, load_error = load_data()

# ============================================================
# SIDEBAR
# ============================================================
with st.sidebar:
    st.markdown("## 🎓 OBE Recommender")
    st.divider()
    page = st.radio(
        "Navigation",
        ["🏠 Recommendation"],  # 🕸️ Knowledge Graph di-hide dari sidebar (fungsi tetap ada)
        label_visibility="collapsed"
    )
    # Override page ke KG jika diakses via query param ?page=kg
    if st.query_params.get("page") == "kg":
        page = "🕸️ Knowledge Graph"
    st.divider()
    st.caption("Sistem Rekomendasi Karir Berbasis\nKnowledge Graph & Gap Analysis")
    st.caption("📁 Dataset:\n- 300 Mahasiswa (ITS, Jakarta, Surabaya)\n- 496 Karir\n- 8.207 Kursus Online")

# ============================================================
# ERROR CHECK
# ============================================================
if load_error:
    st.error(f"❌ Gagal memuat data: {load_error}")
    st.stop()

# ==============================================================
# PAGE: RECOMMENDATION
# ==============================================================
if page == "🏠 Recommendation":
    st.markdown("## 🎓 OBE Career & Online Learning Recommender")
    st.caption("Rekomendasi karir dan online course berbasis Outcome Based Education & Knowledge Graph Gap Analysis")
    st.divider()

    # ── Student Selector & Campus Filter ───────────────────────
    st.markdown('<div class="section-title">👤 Pilih Mahasiswa</div>', unsafe_allow_html=True)
    
    col_filter, col_select = st.columns([1, 3])
    with col_filter:
        campus_filter = st.selectbox(
            "Filter Kampus",
            ["Semua (300 Mahasiswa)", "ITS (100 Mahasiswa)", "Jakarta (100 Mahasiswa)", "Surabaya (100 Mahasiswa)"],
            index=0
        )
    
    students_all = df_rank[['student_id', 'student_name', 'campus']].drop_duplicates().sort_values('student_id')
    
    if "ITS" in campus_filter:
        students = students_all[students_all['campus'] == 'ITS'].copy()
    elif "Jakarta" in campus_filter:
        students = students_all[students_all['campus'] == 'Jakarta'].copy()
    elif "Surabaya" in campus_filter:
        students = students_all[students_all['campus'] == 'Surabaya'].copy()
    else:
        students = students_all.copy()

    students['display'] = students['student_id'] + " — " + students['student_name'] + " (" + students['campus'] + ")"
    
    with col_select:
        selected_display = st.selectbox("Pilih Mahasiswa", students['display'].tolist(), label_visibility="visible")

    selected_sid    = selected_display.split(" — ")[0].strip()
    student_df      = df_rank[df_rank['student_id'] == selected_sid].copy()
    selected_name   = student_df['student_name'].iloc[0]
    selected_campus = student_df['campus'].iloc[0]
    top5            = student_df[student_df['career_rank'] <= 5].sort_values('career_rank')

    # ── Student Summary Metrics ───────────────────────────────
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("👤 Nama Mahasiswa", selected_name)
    col2.metric("🆔 Student ID", selected_sid)
    col3.metric("🎯 Top Karir Tersedia", len(top5))
    col4.metric("🏫 Asal Mahasiswa", selected_campus)
    st.divider()

    # ── Top 5 Recommended Careers ─────────────────────────────
    st.markdown('<div class="section-title">🏆 Rekomendasi Karir (Top 5)</div>', unsafe_allow_html=True)

    career_options = []
    for _, row in top5.iterrows():
        rank      = int(row['career_rank'])
        career_nm = row['career_name'].title()
        rsg       = float(row['relative_skill_gap']) * 100
        matched   = int(row['matched_skill_count'])
        required  = int(row['required_skill_count'])
        missing_c = int(row['missing_skill_count'])
        is_top    = rank == 1

        with st.container(border=True):
            left, right = st.columns([1, 9])
            with left:
                if is_top:
                    st.markdown("## ⭐")
                else:
                    st.markdown(f"### #{rank}")
            with right:
                if is_top:
                    st.markdown(f"🏆 **#{rank} — {career_nm}** &nbsp;&nbsp; `[Top Recommended]`")
                else:
                    st.markdown(f"**#{rank} — {career_nm}**")
                
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("📊 Skill Gap",   f"{rsg:.1f}%")
                m2.metric("✅ Matched",     matched)
                m3.metric("📋 Required",    required)
                m4.metric("⚠ Missing",     missing_c)
                
                # Bar biru tepat di bawah 4 metrik
                match_pct = (100.0 - rsg) if required > 0 else 0.0
                st.progress(max(0.0, min(1.0, match_pct / 100.0)))

        career_options.append(f"#{rank} — {career_nm}")

    st.divider()

    # ── Career Detail Selector ────────────────────────────────
    st.markdown('<div class="section-title">📋 Detail Karir & Rekomendasi Kursus</div>', unsafe_allow_html=True)
    
    col_scope, _ = st.columns([2, 1])
    with col_scope:
        career_scope = st.radio(
            "Pilih Mode Tampilan Karir:",
            ["🏆 Top 5 Rekomendasi Karir", "🌐 Eksplorasi Semua 496 Karir Industri"],
            horizontal=True,
            label_visibility="collapsed"
        )

    if career_scope == "🏆 Top 5 Rekomendasi Karir":
        available_careers = top5.sort_values('career_rank')
    else:
        available_careers = student_df.sort_values('career_rank')

    career_options_list = [f"#{int(r['career_rank'])} — {r['career_name'].title()}" for _, r in available_careers.iterrows()]
    sel_career_disp     = st.selectbox("Pilih Career untuk Detail", career_options_list, label_visibility="visible")
    sel_career_rank     = int(sel_career_disp.split(" — ")[0].replace("#", "").strip())
    career_row          = student_df[student_df['career_rank'] == sel_career_rank].iloc[0]
    career_name_full    = career_row['career_name'].title()
    rsg_val             = float(career_row['relative_skill_gap']) * 100

    required_skills = parse_skills(career_row['required_skills'])
    matched_skills  = parse_skills(career_row['matched_skills'])
    missing_skills  = parse_skills(career_row['missing_skills'])

    # ── Career Metrics ────────────────────────────────────────
    st.markdown(f"### 💼 {career_name_full}")
    mc1, mc2, mc3, mc4 = st.columns(4)
    mc1.metric("📋 Required Skills", int(career_row['required_skill_count']))
    mc2.metric("✅ Matched Skills",  int(career_row['matched_skill_count']))
    mc3.metric("⚠ Missing Skills",  int(career_row['missing_skill_count']))
    mc4.metric("📊 Skill Gap",       f"{rsg_val:.2f}%")

    # ── Skill Tabs ────────────────────────────────────────────
    tab1, tab2, tab3 = st.tabs(["📋 Career Requirements", "✅ Matched Skills", "⚠ Missing Skills"])

    with tab1:
        if required_skills:
            pills = "".join([f'<span class="pill-blue">{s}</span>' for s in sorted(required_skills)])
            st.markdown(f'<div class="pill-row">{pills}</div>', unsafe_allow_html=True)
        else:
            st.info("Data required skills tidak tersedia.")

    with tab2:
        if matched_skills:
            pills = "".join([f'<span class="pill-green">✓ {s}</span>' for s in sorted(matched_skills)])
            st.markdown(f'<div class="pill-row">{pills}</div>', unsafe_allow_html=True)
        else:
            st.warning("Tidak ada matched skills untuk karir ini.")

    with tab3:
        if missing_skills:
            pills = "".join([f'<span class="pill-red">✗ {s}</span>' for s in sorted(missing_skills)])
            st.markdown(f'<div class="pill-row">{pills}</div>', unsafe_allow_html=True)
        else:
            st.success("🎉 Tidak ada missing skills — mahasiswa sudah memenuhi semua kebutuhan karir ini!")

    st.divider()

    # ── Course Recommendation ─────────────────────────────────
    if not missing_skills:
        st.success("✅ Tidak ada missing skills — tidak diperlukan rekomendasi kursus.")
    else:
        st.markdown('<div class="section-title">📚 Rekomendasi Kursus</div>', unsafe_allow_html=True)
        st.caption(f"Rekomendasi per missing skill: 1 Beginner → 1 Intermediate → 1 Mixed → 1 Advanced (maks 4/skill) + Taxonomy Fallback")

        # Build skill index (cached) dan get recommendations
        skill_index   = _build_skill_index(df_course)
        courses_map   = get_courses_for_missing(skill_index, missing_skills)

        # Hitung uncovered
        uncovered = [sk for sk in missing_skills if not courses_map.get(sk)]
        has_any   = any(courses_map.get(sk) for sk in missing_skills)

        if not has_any:
            st.warning("⚠️ Tidak ditemukan kursus untuk semua missing skills pada dataset.")
        else:
            course_number = 1
            for sk in sorted(missing_skills):
                courses = courses_map.get(sk, [])
                if not courses:
                    continue
                st.markdown(f"**Missing Skill: `{sk}`**")
                for c in courses:
                    lvl_icon = {'Beginner': '🟢', 'Intermediate': '🔵',
                                'Mixed': '🟣', 'Advanced': '🔴'}.get(c.get('level_label', ''), '⚪')
                    with st.container(border=True):
                        h_col, d_col = st.columns([7, 3])
                        with h_col:
                            st.markdown(f"**#{course_number} — 📚 {c['course_name']}**")
                            st.caption(f"🏛️ {c['platform']}  |  {lvl_icon} Level: {c.get('level_label', '-')}")
                        with d_col:
                            covers_lbl = c.get('covers_label', sk)
                            st.caption(f"Covers: `{covers_lbl}`")
                    course_number += 1

        if uncovered:
            with st.expander(f"⚠️ {len(uncovered)} missing skill belum ada course-nya"):
                for sk in sorted(uncovered):
                    st.markdown(f"- ❌ **{sk}**")

        # ── Learning Roadmap ──────────────────────────────────
        st.divider()
        st.markdown('<div class="section-title">🗺️ Peta Jalur Pembelajaran</div>', unsafe_allow_html=True)
        st.caption("Jalur pembelajaran bertahap berdasarkan tingkat kesulitan kursus (dikelompokkan dari semua skill)")

        roadmap = build_roadmap(courses_map)
        if not roadmap:
            st.info("Roadmap tidak tersedia karena tidak ada rekomendasi kursus.")
        else:
            level_icons = {'Beginner': '🟢', 'Intermediate': '🔵', 'Mixed': '🟣', 'Advanced': '🔴'}
            for step_num, (lvl_name, lvl_data) in enumerate(roadmap.items(), 1):
                icon = level_icons.get(lvl_name, '⚪')
                with st.container(border=True):
                    st.markdown(f"**{icon} Step {step_num} — {lvl_name}**")
                    for c in lvl_data['courses']:
                        covers_str = c.get('covers_label', '')
                        st.markdown(f"- 📚 **{c['course_name']}** *(by {c['platform']})* — covers: `{covers_str}`")


# ==============================================================
# PAGE: KNOWLEDGE GRAPH
# ==============================================================
elif page == "🕸️ Knowledge Graph":
    st.markdown("## 🕸️ Knowledge Graph — Visualisasi Konseptual")
    st.caption("Representasi relasi antara Student, Career, Skill, dan Course dalam Knowledge Graph")
    st.divider()

    # Ontology description
    st.markdown("### 🧠 Struktur Ontologi Knowledge Graph")

    col_desc, col_rel = st.columns(2)
    with col_desc:
        with st.container(border=True):
            st.markdown("**Node Types**")
            st.dataframe(pd.DataFrame({
                'Node': ['👤 Student', '💼 Career', '🔧 Skill', '📚 Course'],
                'Properti': ['student_id, name, campus', 'career_id, name', 'name (canonical)', 'course_id, name, platform, level'],
                'Jumlah': ['300', '496', '11.362', '8.207']
            }), use_container_width=True, hide_index=True)

    with col_rel:
        with st.container(border=True):
            st.markdown("**Relasi Graph**")
            st.code(
                "(Student)  --[HAS_SKILL]--> (Skill)\n"
                "(Career)   --[REQUIRES]---> (Skill)\n"
                "(Course)   --[TEACHES]----> (Skill)",
                language="text"
            )
            st.markdown("""
- **HAS_SKILL**: Skill yang dikuasai mahasiswa
- **REQUIRES**: Skill yang dibutuhkan oleh karir
- **TEACHES**: Skill yang diajarkan oleh kursus
""")

    st.divider()
    st.markdown("### 🔍 Subgraph — Mahasiswa & Karir Rank #1")

    students = df_rank[['student_id', 'student_name', 'campus']].drop_duplicates().sort_values('student_id')
    students['display'] = students['student_id'] + " — " + students['student_name'] + " (" + students['campus'] + ")"
    sel = st.selectbox("Pilih Mahasiswa", students['display'].tolist(), key="kg_student")
    sel_sid = sel.split(" — ")[0].strip()

    career_row_kg = df_rank[(df_rank['student_id'] == sel_sid) & (df_rank['career_rank'] == 1)]
    if career_row_kg.empty:
        st.warning("Data karir tidak ditemukan untuk mahasiswa ini.")
    else:
        row_kg          = career_row_kg.iloc[0]
        matched_kg      = parse_skills(row_kg['matched_skills'])
        missing_kg      = parse_skills(row_kg['missing_skills'])
        career_name_kg  = row_kg['career_name'].title()
        rsg_kg          = float(row_kg['relative_skill_gap']) * 100

        # Gunakan logika rekomendasi kursus yang sama
        skill_index_kg  = _build_skill_index(df_course)
        courses_map_kg  = get_courses_for_missing(skill_index_kg, missing_kg)
        
        # Flatten untuk graph visualization (max 3 kursus unik)
        recs_kg = []
        seen_kg = set()
        for courses in courses_map_kg.values():
            for c in courses:
                if c['course_id'] not in seen_kg and len(recs_kg) < 3:
                    seen_kg.add(c['course_id'])
                    recs_kg.append(c)

        inf1, inf2, inf3, inf4 = st.columns(4)
        inf1.metric("👤 Mahasiswa", row_kg['student_name'][:15])
        inf2.metric("💼 Target Karir", career_name_kg[:20])
        inf3.metric("📊 Skill Gap", f"{rsg_kg:.1f}%")
        inf4.metric("📚 Course Tersedia", len(recs_kg))

        # Build graph
        node_x, node_y, node_text, node_color, node_size = [], [], [], [], []
        edge_x, edge_y = [], []
        positions = {}

        def add_node(key, x, y, label, color, size):
            positions[key] = (x, y)
            node_x.append(x); node_y.append(y)
            node_text.append(label)
            node_color.append(color); node_size.append(size)

        def add_edge(k1, k2):
            if k1 in positions and k2 in positions:
                x1, y1 = positions[k1]
                x2, y2 = positions[k2]
                edge_x.extend([x1, x2, None])
                edge_y.extend([y1, y2, None])

        # Student
        add_node('student', 0, 0, f"👤 {row_kg['student_name']}", '#60A5FA', 28)
        # Career
        add_node('career', 4, 0, f"💼 {career_name_kg[:20]}", '#A78BFA', 24)

        all_skills = matched_kg[:5] + missing_kg[:5]
        n = len(all_skills)
        for i, sk in enumerate(all_skills):
            y = (i - n/2 + 0.5) * 1.0
            key = f'sk_{sk}'
            color = '#22C55E' if sk in matched_kg else '#EF4444'
            add_node(key, 2, y, f"🔧 {sk}", color, 14)
            if sk in matched_kg:
                add_edge('student', key)
            add_edge('career', key)

        for i, rec in enumerate(recs_kg):
            y = (i - len(recs_kg)/2 + 0.5) * 1.5
            key = f'co_{rec["course_id"]}'
            add_node(key, 6, y, f"📚 {rec['course_name'][:25]}", '#FCD34D', 18)
            covers_label = rec.get('covers_label', '')
            skill_from_label = covers_label.split(' (via:')[0].strip() if covers_label else ''
            add_edge(key, f'sk_{skill_from_label}')

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=edge_x, y=edge_y, mode='lines',
            line=dict(width=1, color='rgba(100,116,139,0.5)'),
            hoverinfo='none'
        ))
        fig.add_trace(go.Scatter(
            x=node_x, y=node_y, mode='markers+text',
            marker=dict(size=node_size, color=node_color, line=dict(width=1, color='#1E293B')),
            text=node_text,
            textposition='top center',
            textfont=dict(size=9),
            hoverinfo='text'
        ))
        fig.update_layout(
            showlegend=False, height=520,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            margin=dict(l=10, r=10, t=20, b=10)
        )
        st.plotly_chart(fig, use_container_width=True)
        st.caption("🟢 Matched Skill  🔴 Missing Skill  🔵 Student  🟣 Career  🟡 Course (Top 3 Recommendation)")

    # Cypher reference
    with st.expander("🔧 Cypher Query Reference (Neo4j Browser)"):
        st.code("""
-- Skema Lengkap
CALL db.schema.visualization()

-- Subgraph: Student matched skills + career requirements
MATCH (s:Student {name: "Laila Kusuma"})-[r1:HAS_SKILL]->(sk:Skill)
      <-[r2:REQUIRES]-(c:Career {name: "data warehouse programming specialist"})
RETURN s, r1, sk, r2, c

-- Missing skills + available courses
MATCH (c:Career {name: "data warehouse programming specialist"})-[:REQUIRES]->(sk:Skill)
WHERE NOT EXISTS {
  MATCH (s:Student {name: "Laila Kusuma"})-[:HAS_SKILL]->(sk)
}
MATCH (co:Course)-[:TEACHES]->(sk)
RETURN co, sk, c LIMIT 30

-- Node statistics
MATCH (n) RETURN labels(n)[0] AS Tipe, count(n) AS Total ORDER BY Total DESC
""", language="cypher")


# ==============================================================
# PAGE: ANALYSIS (LOGIC PRESERVED, HIDDEN FROM SIDEBAR RADIO)
# ==============================================================
elif page == "📊 Analysis":
    st.markdown("## 📊 Dataset & Gap Analysis")
    st.caption("Statistik ringkasan dataset Knowledge Graph dan hasil Gap Analysis")
    st.divider()

    # Summary stats
    n_students = df_rank['student_id'].nunique()
    n_careers  = df_rank['career_name'].nunique()
    n_courses  = df_course['course_id'].nunique()
    n_skills   = df_course['canonical_skill'].nunique()
    avg_rsg    = df_rank[df_rank['career_rank'] == 1]['relative_skill_gap'].mean() * 100
    n_mappings = len(df_course)

    s1, s2, s3 = st.columns(3)
    with s1:
        st.metric("👤 Total Mahasiswa", n_students)
        st.metric("📚 Total Kursus Online", n_courses)
    with s2:
        st.metric("💼 Total Posisi Karir", n_careers)
        st.metric("🔧 Unique Skills (Courses)", n_skills)
    with s3:
        st.metric("📊 Avg Skill Gap (Top-1)", f"{avg_rsg:.1f}%")
        st.metric("🔗 Course-Skill Mappings", f"{n_mappings:,}")
    st.divider()

    # RSG distribution
    st.subheader("📊 Distribusi Relative Skill Gap — Top-1 Career")
    df_rsg = df_rank[df_rank['career_rank'] == 1][['student_id', 'student_name', 'relative_skill_gap']].copy()
    df_rsg['rsg_pct'] = df_rsg['relative_skill_gap'] * 100
    fig_rsg = px.histogram(df_rsg, x='rsg_pct', nbins=20,
        labels={'rsg_pct': 'Relative Skill Gap (%)'},
        title='Distribusi RSG untuk Karir Rank #1',
        color_discrete_sequence=['#3B82F6'],
        template='plotly_dark')
    fig_rsg.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0.1)')
    st.plotly_chart(fig_rsg, use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("🏆 Top 15 Karir Paling Sering Direkomendasikan")
        top_c = df_rank[df_rank['career_rank'] == 1]['career_name'].value_counts().head(15).reset_index()
        top_c.columns = ['Career', 'Jumlah']
        fig_tc = px.bar(top_c, x='Jumlah', y='Career', orientation='h',
            color='Jumlah', color_continuous_scale='Blues',
            template='plotly_dark', title='Frekuensi Karir sebagai Rank #1')
        fig_tc.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0.1)',
            yaxis={'categoryorder': 'total ascending'})
        st.plotly_chart(fig_tc, use_container_width=True)

    with c2:
        st.subheader("🏛 Top 15 Platform Kursus Online")
        top_p = df_course[['course_id', 'platform']].drop_duplicates()['platform'].value_counts().head(15).reset_index()
        top_p.columns = ['Platform', 'Jumlah Kursus']
        fig_p = px.bar(top_p, x='Jumlah Kursus', y='Platform', orientation='h',
            color='Jumlah Kursus', color_continuous_scale='Greens',
            template='plotly_dark', title='Platform Kursus Terbanyak')
        fig_p.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0.1)',
            yaxis={'categoryorder': 'total ascending'})
        st.plotly_chart(fig_p, use_container_width=True)

    # Level distribution + campus boxplot
    d1, d2 = st.columns(2)
    with d1:
        st.subheader("📊 Distribusi Level Kursus")
        df_lv = df_course[['course_id', 'level']].drop_duplicates().copy()
        df_lv['level_clean'] = df_lv['level'].apply(get_level_label)
        lv_cnt = df_lv['level_clean'].value_counts().reset_index()
        lv_cnt.columns = ['Level', 'Jumlah']
        fig_lv = px.pie(lv_cnt, values='Jumlah', names='Level',
            template='plotly_dark',
            color='Level',
            color_discrete_map={'Beginner': '#22C55E', 'Intermediate': '#3B82F6', 'Mixed': '#A855F7', 'Advanced': '#EF4444'},
            title='Komposisi Level Kursus Online')
        fig_lv.update_layout(paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_lv, use_container_width=True)

    with d2:
        st.subheader("📊 Skill Gap per Campus")
        df_c = df_rank[df_rank['career_rank'] == 1].copy()
        df_c['rsg_pct'] = df_c['relative_skill_gap'] * 100
        fig_box = px.box(
            df_c, x='campus', y='rsg_pct', color='campus',
            labels={'rsg_pct': 'Relative Skill Gap (%)', 'campus': 'Kampus'},
            template='plotly_dark'
        )
        fig_box.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(15,23,42,0.5)')
        st.plotly_chart(fig_box, use_container_width=True)
