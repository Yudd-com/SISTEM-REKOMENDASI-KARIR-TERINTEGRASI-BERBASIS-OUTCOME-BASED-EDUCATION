@echo off
title Menjalankan App Utama (app.py) - Port 8502
cd /d "%~dp0"
echo ============================================================
echo   Menjalankan OBE Career & Course Recommender (app.py)
echo   Akses di browser: http://localhost:8502
echo ============================================================
python -m streamlit run app.py --server.port 8502
pause
