@echo off
title Menjalankan App Eksperimen (app1.py) - Port 8503
cd /d "%~dp0"
echo ============================================================
echo   Menjalankan OBE Recommender + Nilai Mahasiswa (app1.py)
echo   Akses di browser: http://localhost:8503
echo ============================================================
python -m streamlit run app1.py --server.port 8503
pause
