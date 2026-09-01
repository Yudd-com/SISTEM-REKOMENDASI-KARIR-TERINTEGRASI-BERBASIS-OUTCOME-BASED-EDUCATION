"""
reorganize_output_folders.py
=============================
Memisahkan folder di final_project/output/:
1. output/normalisasi_skill/  <- CSV hasil ekstraksi & normalisasi skill (input KG)
2. output/hasil_kg/           <- CSV hasil analisis & komputasi KG (Gap, Ranking, Rekomendasi)
3. Tambahkan .gitkeep di setiap folder
"""
import shutil
from pathlib import Path

BASE = Path(r"D:\Magang Brin\gap analisis\final_project")
OUT_DIR = BASE / "output"

DIR_NORM = OUT_DIR / "normalisasi_skill"
DIR_KG   = OUT_DIR / "hasil_kg"

def main():
    DIR_NORM.mkdir(parents=True, exist_ok=True)
    DIR_KG.mkdir(parents=True, exist_ok=True)

    # 1. Normalisasi Skill Files
    norm_files = [
        "student_skill_final.csv",
        "career_skill_final.csv",
        "course_skill_final.csv",
        "canonical_skill_master.csv",
        "obe_skills_raw.csv",
    ]
    print("=== MEMINDAHKAN FILE NORMALISASI SKILL ===")
    for fname in norm_files:
        src = OUT_DIR / fname
        dst = DIR_NORM / fname
        if src.exists():
            shutil.move(str(src), str(dst))
            print(f"  [MOVED] {fname} -> output/normalisasi_skill/")
        elif (BASE / "data_clean" / "normalized" / fname).exists():
            shutil.copy2(str(BASE / "data_clean" / "normalized" / fname), str(dst))
            print(f"  [COPIED from data_clean] {fname} -> output/normalisasi_skill/")

    # 2. Hasil KG Files
    kg_files = [
        "career_gap_raw.csv",
        "career_ranking_result_v2.csv",
        "course_recommendation_result.csv",
    ]
    print("\n=== MEMINDAHKAN FILE HASIL KG ===")
    for fname in kg_files:
        src = OUT_DIR / fname
        dst = DIR_KG / fname
        if src.exists():
            shutil.move(str(src), str(dst))
            print(f"  [MOVED] {fname} -> output/hasil_kg/")

    # 3. Buat .gitkeep di semua folder penting
    print("\n=== MEMBUAT .gitkeep FILES ===")
    gitkeeps = [
        OUT_DIR / ".gitkeep",
        DIR_NORM / ".gitkeep",
        DIR_KG / ".gitkeep",
        BASE / "data_clean" / "normalized" / ".gitkeep",
        BASE / "data_clean" / "obe" / ".gitkeep",
        BASE / "data_clean" / "job" / ".gitkeep",
        BASE / "data_clean" / "course" / ".gitkeep",
        BASE / "data_raw" / "obe" / ".gitkeep",
        BASE / "data_raw" / "job" / ".gitkeep",
        BASE / "data_raw" / "course" / ".gitkeep",
    ]
    for gk in gitkeeps:
        gk.parent.mkdir(parents=True, exist_ok=True)
        gk.write_text("# Placeholder\n", encoding="utf-8")
        print(f"  [GITKEEP] {gk.relative_to(BASE)}")

    print("\n=== SELESAI ===")

if __name__ == "__main__":
    main()
