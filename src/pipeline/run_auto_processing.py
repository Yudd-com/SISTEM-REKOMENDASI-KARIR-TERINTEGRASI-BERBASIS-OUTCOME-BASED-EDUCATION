"""
run_auto_processing.py
======================
Script orchestrator untuk menjalankan pipeline pemrosesan data otomatis secara end-to-end:
1. Ekstraksi Otomatis (auto_skill_extractor.py)
2. Normalisasi & Kanonikalisasi Otomatis (auto_skill_normalizer.py)
"""

import sys
from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(CURRENT_DIR))

import auto_skill_extractor
import auto_skill_normalizer

def main():
    print("*" * 70)
    print("STARTING END-TO-END AUTOMATED SKILL PROCESSING PIPELINE")
    print("*" * 70)
    
    # 1. Ekstraksi Skill Otomatis
    auto_skill_extractor.run_extraction()
    
    # 2. Normalisasi & Kanonikalisasi Otomatis
    auto_skill_normalizer.run_normalization()
    
    print("\n" + "*" * 70)
    print("END-TO-END AUTOMATED PIPELINE COMPLETED SUCCESSFULLY!")
    print("*" * 70)

if __name__ == "__main__":
    main()
