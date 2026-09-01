@echo off
title Menjalankan Kedua Aplikasi (app.py & app1.py)
cd /d "%~dp0"
echo ============================================================
echo   Menjalankan app.py (Port 8502) dan app1.py (Port 8503)
echo ============================================================
start "Streamlit app.py (Port 8502)" cmd /k "python -m streamlit run app.py --server.port 8502"
start "Streamlit app1.py (Port 8503)" cmd /k "python -m streamlit run app1.py --server.port 8503"
echo.
echo Kedua aplikasi berhasil dijalankan!
echo - App Utama:      http://localhost:8502
echo - App Eksperimen: http://localhost:8503
echo.
pause
