@echo off
chcp 65001 >nul
title SecureVoice - Install
cd /d "%~dp0"
echo ============================================================
echo   SecureVoice - Secure Voice Communication System
echo   Step 1/2: Installing requirements
echo ============================================================
where python >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Python is not installed or not in PATH.
  echo Download Python 3.10+ from https://www.python.org/downloads/
  echo and CHECK "Add python.exe to PATH" during installation.
  pause
  exit /b 1
)
python --version
if not exist .venv (
  echo Creating virtual environment .venv ...
  python -m venv .venv
)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if errorlevel 1 (
  echo [ERROR] Installing packages failed. Check your internet connection.
  pause
  exit /b 1
)
echo.
echo [OK] Installation finished. Now run:  run.bat
echo      (Optional, as Administrator) firewall.bat
pause
